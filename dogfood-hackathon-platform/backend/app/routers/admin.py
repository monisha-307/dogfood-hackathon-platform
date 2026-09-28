from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_hackathon, require_role
from ..models import (
    Criterion,
    Evaluation,
    Hackathon,
    JudgeAssignment,
    Result,
    Submission,
    Team,
    TeamMember,
    User,
)
from ..schemas import AssignmentIn, CriterionIn, PublishIn
from ..serializers import (
    assignment_out,
    criterion_out,
    evaluation_out,
    hackathon_out,
    iso,
    result_out,
    submission_out,
    team_out,
    user_out,
)
from ..services import scoring

router = APIRouter(prefix="/api/admin", tags=["admin"])
admin_only = require_role("admin")


def _ensure_not_published(hackathon: Hackathon) -> None:
    if hackathon.results_published:
        raise HTTPException(
            status_code=409, detail="Results are published. Unpublish them to make changes."
        )


def _submissions(db: Session, hackathon: Hackathon) -> list[Submission]:
    return list(
        db.scalars(
            select(Submission)
            .where(Submission.hackathon_id == hackathon.id)
            .order_by(Submission.submitted_at)
        )
    )


def _evaluation_count(db: Session, hackathon: Hackathon) -> int:
    return db.scalar(
        select(func.count(Evaluation.id))
        .join(Submission, Evaluation.submission_id == Submission.id)
        .where(Submission.hackathon_id == hackathon.id)
    ) or 0


# ---------------------------------------------------------------- overview

@router.get("/overview")
def overview(
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    subs = _submissions(db, hackathon)
    assignments = [a for s in subs for a in s.assignments]
    participants = db.scalar(select(func.count(User.id)).where(User.role == "participant")) or 0
    in_teams = db.scalar(
        select(func.count(TeamMember.id)).where(TeamMember.hackathon_id == hackathon.id)
    ) or 0
    eligible = [s for s in subs if s.eligibility_status == "eligible"]
    unassigned = [s for s in eligible if not s.assignments]
    return {
        "hackathon": hackathon_out(hackathon),
        "counts": {
            "participants": participants,
            "participants_without_team": max(participants - in_teams, 0),
            "teams": db.scalar(select(func.count(Team.id)).where(Team.hackathon_id == hackathon.id)) or 0,
            "submissions": len(subs),
            "eligible": len(eligible),
            "ineligible": len(subs) - len(eligible),
            "unassigned": len(unassigned),
            "evaluations_total": len(assignments),
            "evaluations_completed": sum(1 for a in assignments if a.status == "completed"),
            "evaluations_pending": sum(1 for a in assignments if a.status == "pending"),
            "judges": db.scalar(select(func.count(User.id)).where(User.role == "judge")) or 0,
        },
        "next_steps": _next_steps(hackathon, subs, unassigned, assignments),
    }


def _next_steps(hackathon, subs, unassigned, assignments) -> list[str]:
    if hackathon.results_published:
        return ["Results are live. Participants can see their rank and download certificates."]
    steps = []
    if unassigned:
        steps.append(f"Assign a judge to {len(unassigned)} eligible submission(s).")
    pending = sum(1 for a in assignments if a.status == "pending")
    if pending:
        steps.append(f"Wait for {pending} pending evaluation(s), or publish without them.")
    if any(a.status == "completed" for a in assignments):
        steps.append("Calculate results to preview the ranking, then publish.")
    if not subs:
        steps.append("No submissions yet.")
    return steps


# ---------------------------------------------------------------- people

@router.get("/participants")
def participants(
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    users = db.scalars(select(User).where(User.role == "participant").order_by(User.full_name)).all()
    out = []
    for u in users:
        membership = next((m for m in u.memberships if m.hackathon_id == hackathon.id), None)
        out.append(
            {
                **user_out(u),
                "joined_at": iso(u.created_at),
                "team": {"id": membership.team.id, "name": membership.team.name} if membership else None,
                "is_lead": membership.is_lead if membership else False,
            }
        )
    return {"participants": out}


@router.get("/judges")
def judges(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    users = db.scalars(select(User).where(User.role == "judge").order_by(User.full_name)).all()
    return {"judges": [user_out(u) for u in users]}


@router.get("/teams")
def teams(
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Team).where(Team.hackathon_id == hackathon.id).order_by(Team.name)).all()
    out = []
    for t in rows:
        data = team_out(t, include_invite=True)
        data["submission"] = (
            {
                "id": t.submission.id,
                "title": t.submission.title,
                "eligibility_status": t.submission.eligibility_status,
            }
            if t.submission
            else None
        )
        out.append(data)
    return {"teams": out}


# ---------------------------------------------------------------- submissions & assignments

@router.get("/submissions")
def submissions(
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    return {"submissions": [submission_out(s, with_judging=True) for s in _submissions(db, hackathon)]}


@router.post("/assignments", status_code=201)
def assign_judge(
    body: AssignmentIn,
    admin: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    _ensure_not_published(hackathon)
    sub = db.get(Submission, body.submission_id)
    if sub is None or sub.hackathon_id != hackathon.id:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if sub.eligibility_status != "eligible":
        raise HTTPException(status_code=409, detail="Only eligible submissions can be sent to judges.")
    judge = db.get(User, body.judge_id)
    if judge is None or judge.role != "judge":
        raise HTTPException(status_code=404, detail="Judge not found.")
    if any(a.judge_id == judge.id for a in sub.assignments):
        raise HTTPException(status_code=409, detail=f"{judge.full_name} is already assigned to this submission.")

    assignment = JudgeAssignment(submission_id=sub.id, judge_id=judge.id, assigned_by_id=admin.id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {"assignment": assignment_out(assignment)}


@router.delete("/assignments/{assignment_id}")
def unassign_judge(
    assignment_id: int,
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    _ensure_not_published(hackathon)
    assignment = db.get(JudgeAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    if assignment.status == "completed":
        raise HTTPException(status_code=409, detail="This evaluation is already submitted and can't be removed.")
    db.delete(assignment)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- criteria

@router.get("/criteria")
def list_criteria(
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    return {
        "criteria": [criterion_out(c) for c in hackathon.criteria],
        "max_total": sum(c.max_score for c in hackathon.criteria),
        "evaluations_submitted": _evaluation_count(db, hackathon),
    }


@router.post("/criteria", status_code=201)
def create_criterion(
    body: CriterionIn,
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    _ensure_not_published(hackathon)
    position = body.position
    if position is None:
        position = max((c.position for c in hackathon.criteria), default=0) + 1
    criterion = Criterion(
        hackathon_id=hackathon.id,
        name=body.name.strip(),
        description=body.description.strip(),
        max_score=body.max_score,
        position=position,
    )
    db.add(criterion)
    db.commit()
    return {"criterion": criterion_out(criterion)}


def _get_criterion(db: Session, hackathon: Hackathon, criterion_id: int) -> Criterion:
    criterion = db.get(Criterion, criterion_id)
    if criterion is None or criterion.hackathon_id != hackathon.id:
        raise HTTPException(status_code=404, detail="Criterion not found.")
    return criterion


@router.put("/criteria/{criterion_id}")
def update_criterion(
    criterion_id: int,
    body: CriterionIn,
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    _ensure_not_published(hackathon)
    criterion = _get_criterion(db, hackathon, criterion_id)
    criterion.name = body.name.strip()
    criterion.description = body.description.strip()
    criterion.max_score = body.max_score
    if body.position is not None:
        criterion.position = body.position
    db.commit()
    return {"criterion": criterion_out(criterion)}


@router.delete("/criteria/{criterion_id}")
def delete_criterion(
    criterion_id: int,
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    _ensure_not_published(hackathon)
    criterion = _get_criterion(db, hackathon, criterion_id)
    if len(hackathon.criteria) <= 1:
        raise HTTPException(status_code=409, detail="Keep at least one criterion.")
    db.delete(criterion)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- scores & results

@router.get("/evaluations")
def evaluations(
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    rows = []
    for sub in _submissions(db, hackathon):
        for a in sub.assignments:
            rows.append(
                {
                    "submission": {"id": sub.id, "title": sub.title, "team": sub.team.name},
                    "assignment_id": a.id,
                    "judge": {"id": a.judge.id, "full_name": a.judge.full_name},
                    "status": a.status,
                    "evaluation": evaluation_out(a.evaluation) if a.evaluation else None,
                }
            )
    return {"evaluations": rows}


def _results_payload(db: Session, hackathon: Hackathon) -> dict:
    results = db.scalars(select(Result).where(Result.hackathon_id == hackathon.id)).all()
    ordered = sorted(results, key=lambda r: (r.rank is None, r.rank or 0, r.team.name))
    pending = scoring.pending_assignments(db, hackathon)
    return {
        "published": hackathon.results_published,
        "published_at": iso(hackathon.results_published_at),
        "calculated_at": iso(hackathon.results_calculated_at),
        "results": [result_out(r) for r in ordered],
        "pending_evaluations": [
            {"assignment_id": a.id, "judge": a.judge.full_name, "submission": a.submission.title}
            for a in pending
        ],
    }


@router.get("/results")
def get_results(
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    return _results_payload(db, hackathon)


@router.post("/results/calculate")
def calculate(
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    _ensure_not_published(hackathon)
    scoring.calculate_results(db, hackathon)
    db.commit()
    return _results_payload(db, hackathon)


@router.post("/results/publish")
def publish(
    body: PublishIn,
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    _ensure_not_published(hackathon)
    pending = scoring.pending_assignments(db, hackathon)
    if pending and not body.allow_pending:
        raise HTTPException(
            status_code=409,
            detail=f"{len(pending)} evaluation(s) are still pending. Publish anyway to rank on completed scores only.",
        )
    scoring.publish(db, hackathon)
    db.commit()
    return _results_payload(db, hackathon)


@router.post("/results/unpublish")
def unpublish(
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    if not hackathon.results_published:
        raise HTTPException(status_code=409, detail="Results aren't published.")
    scoring.unpublish(db, hackathon)
    db.commit()
    return _results_payload(db, hackathon)
