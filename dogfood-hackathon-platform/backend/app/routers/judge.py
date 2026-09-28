from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db, utcnow
from ..deps import get_hackathon, require_role
from ..models import Evaluation, Hackathon, JudgeAssignment, User
from ..schemas import EvaluationIn
from ..serializers import criterion_out, evaluation_out, iso, submission_out
from ..services.scoring import normalize

router = APIRouter(prefix="/api/judge", tags=["judge"])
judge_only = require_role("judge")


def _assignment_out(a: JudgeAssignment) -> dict:
    return {
        "id": a.id,
        "status": a.status,
        "assigned_at": iso(a.assigned_at),
        "completed_at": iso(a.completed_at),
        "submission": submission_out(a.submission),
        "evaluation": evaluation_out(a.evaluation) if a.evaluation else None,
    }


def _own_assignment(db: Session, judge: User, assignment_id: int) -> JudgeAssignment:
    assignment = db.get(JudgeAssignment, assignment_id)
    # 404 (not 403) so judges can't probe which assignment ids exist.
    if assignment is None or assignment.judge_id != judge.id:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return assignment


@router.get("/assignments")
def my_assignments(
    judge: User = Depends(judge_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    assignments = db.scalars(
        select(JudgeAssignment)
        .where(JudgeAssignment.judge_id == judge.id)
        .order_by(JudgeAssignment.status.desc(), JudgeAssignment.assigned_at)
    ).all()
    items = [_assignment_out(a) for a in assignments if a.submission.hackathon_id == hackathon.id]
    completed = sum(1 for a in items if a["status"] == "completed")
    return {
        "assignments": items,
        "total": len(items),
        "completed": completed,
        "pending": len(items) - completed,
        "results_published": hackathon.results_published,
    }


@router.get("/assignments/{assignment_id}")
def get_assignment(
    assignment_id: int,
    judge: User = Depends(judge_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    assignment = _own_assignment(db, judge, assignment_id)
    return {
        "assignment": _assignment_out(assignment),
        "criteria": [criterion_out(c) for c in hackathon.criteria],
        "max_total": sum(c.max_score for c in hackathon.criteria),
        "results_published": hackathon.results_published,
    }


@router.post("/assignments/{assignment_id}/evaluation", status_code=201)
def submit_evaluation(
    assignment_id: int,
    body: EvaluationIn,
    judge: User = Depends(judge_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    assignment = _own_assignment(db, judge, assignment_id)
    if hackathon.results_published:
        raise HTTPException(status_code=409, detail="Results are published. Scoring is closed.")
    if assignment.status == "completed":
        raise HTTPException(status_code=409, detail="You've already submitted this evaluation.")

    criteria = {c.id: c for c in hackathon.criteria}
    given = {s.criterion_id: s.score for s in body.scores}
    if len(given) != len(body.scores):
        raise HTTPException(status_code=422, detail="Each criterion can only be scored once.")
    missing = [criteria[cid].name for cid in criteria if cid not in given]
    if missing:
        raise HTTPException(status_code=422, detail=f"Score every criterion. Missing: {', '.join(missing)}.")
    unknown = [cid for cid in given if cid not in criteria]
    if unknown:
        raise HTTPException(status_code=422, detail="One of the scores is for an unknown criterion.")
    for cid, score in given.items():
        if not 0 <= score <= criteria[cid].max_score:
            raise HTTPException(
                status_code=422,
                detail=f"{criteria[cid].name} must be between 0 and {criteria[cid].max_score}.",
            )

    snapshot = [
        {"criterion_id": c.id, "name": c.name, "max_score": c.max_score, "score": given[c.id]}
        for c in hackathon.criteria
    ]
    raw_total = float(sum(given.values()))
    max_total = float(sum(c.max_score for c in hackathon.criteria))
    now = utcnow()
    evaluation = Evaluation(
        assignment_id=assignment.id,
        submission_id=assignment.submission_id,
        judge_id=judge.id,
        scores=snapshot,
        raw_total=raw_total,
        max_total=max_total,
        normalized_score=normalize(raw_total, max_total),
        feedback=body.feedback.strip(),
        submitted_at=now,
    )
    assignment.status = "completed"
    assignment.completed_at = now
    db.add(evaluation)
    db.commit()
    db.refresh(assignment)
    return {"assignment": _assignment_out(assignment)}
