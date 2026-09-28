"""Scoring rules, in one place.

    normalized_score = (raw_score / maximum_possible_score) * 100
    final_score      = average(normalized_scores of every completed evaluation)

Ranking uses standard competition ranking: equal final scores share a rank
(1, 1, 3). Only eligible submissions with at least one completed evaluation
are ranked.
"""
import secrets

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..models import Certificate, Hackathon, JudgeAssignment, Result, Submission

CERTIFICATE_TITLES = {
    1: ("winner", "Winner"),
    2: ("runner_up", "First Runner-up"),
    3: ("second_runner_up", "Second Runner-up"),
}


def normalize(raw_total: float, max_total: float) -> float:
    if max_total <= 0:
        return 0.0
    return round(raw_total / max_total * 100, 2)


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def pending_assignments(db: Session, hackathon: Hackathon) -> list[JudgeAssignment]:
    return list(
        db.scalars(
            select(JudgeAssignment)
            .join(Submission, JudgeAssignment.submission_id == Submission.id)
            .where(
                Submission.hackathon_id == hackathon.id,
                Submission.eligibility_status == "eligible",
                JudgeAssignment.status == "pending",
            )
        )
    )


def calculate_results(db: Session, hackathon: Hackathon) -> list[Result]:
    """Recompute the full ranking from scratch. Idempotent."""
    # Certificates point at results, so stale ones go first.
    db.execute(delete(Certificate).where(Certificate.hackathon_id == hackathon.id))
    db.execute(delete(Result).where(Result.hackathon_id == hackathon.id))
    now = utcnow()
    submissions = db.scalars(
        select(Submission).where(Submission.hackathon_id == hackathon.id)
    ).all()

    rows: list[Result] = []
    for sub in submissions:
        completed = [a.evaluation for a in sub.assignments if a.evaluation is not None]
        pending = sum(1 for a in sub.assignments if a.status == "pending")
        breakdown = [
            {
                "judge": e.judge.full_name,
                "raw_total": e.raw_total,
                "max_total": e.max_total,
                "normalized_score": e.normalized_score,
            }
            for e in completed
        ]
        result = Result(
            hackathon_id=hackathon.id,
            submission_id=sub.id,
            team_id=sub.team_id,
            judge_count=len(completed),
            pending_count=pending,
            breakdown=breakdown,
            computed_at=now,
        )
        if sub.eligibility_status != "eligible":
            result.status, result.note = "not_ranked", "Not eligible"
        elif not completed:
            result.status, result.note = "not_ranked", "No completed evaluations yet"
        else:
            result.status = "ranked"
            result.final_score = average([e.normalized_score for e in completed])
            if pending:
                result.note = f"{pending} evaluation(s) still pending"
        rows.append(result)

    ranked = sorted(
        (r for r in rows if r.status == "ranked"), key=lambda r: r.final_score, reverse=True
    )
    previous_score, previous_rank = None, 0
    for position, result in enumerate(ranked, start=1):
        if result.final_score != previous_score:
            previous_rank, previous_score = position, result.final_score
        result.rank = previous_rank

    db.add_all(rows)
    hackathon.results_calculated_at = now
    db.flush()
    return rows


def issue_certificates(db: Session, hackathon: Hackathon) -> int:
    """One certificate per participant whose team submitted a project."""
    db.execute(delete(Certificate).where(Certificate.hackathon_id == hackathon.id))
    results = db.scalars(select(Result).where(Result.hackathon_id == hackathon.id)).all()
    issued = 0
    for result in results:
        kind, title = CERTIFICATE_TITLES.get(result.rank or 0, ("participation", "Participant"))
        for member in result.team.members:
            db.add(
                Certificate(
                    hackathon_id=hackathon.id,
                    user_id=member.user_id,
                    team_id=result.team_id,
                    result_id=result.id,
                    kind=kind,
                    title=title,
                    rank=result.rank,
                    final_score=result.final_score,
                    verification_code=secrets.token_hex(6).upper(),
                    issued_at=utcnow(),
                )
            )
            issued += 1
    db.flush()
    return issued


def publish(db: Session, hackathon: Hackathon) -> None:
    calculate_results(db, hackathon)
    issue_certificates(db, hackathon)
    hackathon.results_published = True
    hackathon.results_published_at = utcnow()


def unpublish(db: Session, hackathon: Hackathon) -> None:
    db.execute(delete(Certificate).where(Certificate.hackathon_id == hackathon.id))
    hackathon.results_published = False
    hackathon.results_published_at = None
