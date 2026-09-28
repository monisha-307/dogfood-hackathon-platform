"""Turn ORM objects into plain JSON-able dicts."""
from datetime import datetime

from .database import utcnow
from .models import (
    Certificate,
    Criterion,
    Evaluation,
    Hackathon,
    JudgeAssignment,
    Result,
    Submission,
    Team,
    User,
)


def iso(dt: datetime | None) -> str | None:
    # Stored as naive UTC; mark it as UTC so browsers convert correctly.
    return dt.isoformat(timespec="seconds") + "Z" if dt else None


def user_out(user: User) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}


def hackathon_phase(h: Hackathon) -> str:
    if h.results_published:
        return "results_published"
    now = utcnow()
    if now < h.starts_at:
        return "upcoming"
    if now <= h.submission_deadline:
        return "submissions_open"
    return "judging"


def criterion_out(c: Criterion) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "max_score": c.max_score,
        "position": c.position,
    }


def hackathon_out(h: Hackathon) -> dict:
    return {
        "id": h.id,
        "name": h.name,
        "tagline": h.tagline,
        "description": h.description,
        "starts_at": iso(h.starts_at),
        "ends_at": iso(h.ends_at),
        "submission_deadline": iso(h.submission_deadline),
        "min_team_size": h.min_team_size,
        "max_team_size": h.max_team_size,
        "phase": hackathon_phase(h),
        "results_published": h.results_published,
        "results_published_at": iso(h.results_published_at),
        "results_calculated_at": iso(h.results_calculated_at),
        "criteria": [criterion_out(c) for c in h.criteria],
        "max_total": sum(c.max_score for c in h.criteria),
    }


def team_out(team: Team, include_invite: bool = False) -> dict:
    data = {
        "id": team.id,
        "name": team.name,
        "created_at": iso(team.created_at),
        "members": [
            {
                "id": m.user.id,
                "full_name": m.user.full_name,
                "email": m.user.email,
                "is_lead": m.is_lead,
                "joined_at": iso(m.joined_at),
            }
            for m in team.members
        ],
        "has_submission": team.submission is not None,
        "submission_locked": is_locked(team.submission) if team.submission else False,
    }
    if include_invite:
        data["invite_code"] = team.invite_code
    return data


def is_locked(sub: Submission) -> bool:
    """Once a judge is assigned, the submission is frozen."""
    return len(sub.assignments) > 0


def submission_stage(sub: Submission) -> str:
    if sub.eligibility_status != "eligible":
        return "ineligible"
    if not sub.assignments:
        return "awaiting_judges"
    if any(a.status == "pending" for a in sub.assignments):
        return "in_review"
    return "evaluated"


def submission_out(sub: Submission, with_judging: bool = False) -> dict:
    data = {
        "id": sub.id,
        "team": {"id": sub.team.id, "name": sub.team.name},
        "title": sub.title,
        "summary": sub.summary,
        "repo_url": sub.repo_url,
        "demo_url": sub.demo_url,
        "tech_stack": sub.tech_stack,
        "eligibility_status": sub.eligibility_status,
        "eligibility_checks": sub.eligibility_checks or [],
        "stage": submission_stage(sub),
        "locked": is_locked(sub),
        "submitted_at": iso(sub.submitted_at),
        "updated_at": iso(sub.updated_at),
        "judges_assigned": len(sub.assignments),
        "evaluations_completed": sum(1 for a in sub.assignments if a.status == "completed"),
    }
    if with_judging:
        data["assignments"] = [assignment_out(a) for a in sub.assignments]
    return data


def evaluation_out(e: Evaluation) -> dict:
    return {
        "id": e.id,
        "assignment_id": e.assignment_id,
        "submission_id": e.submission_id,
        "judge": {"id": e.judge.id, "full_name": e.judge.full_name},
        "scores": e.scores,
        "raw_total": e.raw_total,
        "max_total": e.max_total,
        "normalized_score": e.normalized_score,
        "feedback": e.feedback,
        "submitted_at": iso(e.submitted_at),
    }


def assignment_out(a: JudgeAssignment) -> dict:
    return {
        "id": a.id,
        "submission_id": a.submission_id,
        "judge": {"id": a.judge.id, "full_name": a.judge.full_name},
        "status": a.status,
        "assigned_at": iso(a.assigned_at),
        "completed_at": iso(a.completed_at),
        "evaluation": evaluation_out(a.evaluation) if a.evaluation else None,
    }


def result_out(r: Result) -> dict:
    return {
        "id": r.id,
        "rank": r.rank,
        "status": r.status,
        "final_score": r.final_score,
        "judge_count": r.judge_count,
        "pending_count": r.pending_count,
        "breakdown": r.breakdown or [],
        "note": r.note,
        "team": {"id": r.team.id, "name": r.team.name},
        "submission": {"id": r.submission.id, "title": r.submission.title},
        "computed_at": iso(r.computed_at),
    }


def certificate_out(c: Certificate) -> dict:
    return {
        "id": c.id,
        "kind": c.kind,
        "title": c.title,
        "rank": c.rank,
        "final_score": c.final_score,
        "verification_code": c.verification_code,
        "issued_at": iso(c.issued_at),
        "recipient": c.user.full_name,
        "team": c.team.name,
        "project": c.team.submission.title if c.team.submission else None,
        "hackathon": c.hackathon.name,
        "hackathon_ends_at": iso(c.hackathon.ends_at),
    }
