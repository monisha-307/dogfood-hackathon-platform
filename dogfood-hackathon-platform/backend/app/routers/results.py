from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_hackathon, require_role
from ..models import Certificate, Hackathon, Result, TeamMember, User
from ..serializers import certificate_out, iso, result_out

router = APIRouter(prefix="/api", tags=["results"])


@router.get("/results")
def published_results(
    _: User = Depends(get_current_user),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    """The public leaderboard. Empty until an admin publishes."""
    if not hackathon.results_published:
        return {"published": False, "results": []}
    results = db.scalars(select(Result).where(Result.hackathon_id == hackathon.id)).all()
    ordered = sorted(results, key=lambda r: (r.rank is None, r.rank or 0, r.team.name))
    rows = []
    for r in ordered:
        row = result_out(r)
        # Judges stay anonymous on the public board.
        row["breakdown"] = [
            {**b, "judge": f"Judge {i}"} for i, b in enumerate(row["breakdown"], start=1)
        ]
        rows.append(row)
    return {"published": True, "published_at": iso(hackathon.results_published_at), "results": rows}


@router.get("/results/me")
def my_result(
    user: User = Depends(require_role("participant")),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    membership = db.scalars(
        select(TeamMember).where(
            TeamMember.user_id == user.id, TeamMember.hackathon_id == hackathon.id
        )
    ).first()
    if not hackathon.results_published:
        return {"published": False, "result": None, "feedback": []}
    if membership is None or membership.team.submission is None:
        return {"published": True, "result": None, "feedback": []}

    team = membership.team
    result = db.scalars(
        select(Result).where(Result.hackathon_id == hackathon.id, Result.team_id == team.id)
    ).first()
    feedback = [
        {
            "judge": f"Judge {i}",
            "scores": a.evaluation.scores,
            "normalized_score": a.evaluation.normalized_score,
            "feedback": a.evaluation.feedback,
        }
        for i, a in enumerate(
            (a for a in team.submission.assignments if a.evaluation is not None), start=1
        )
    ]
    total_ranked = len(
        db.scalars(
            select(Result).where(Result.hackathon_id == hackathon.id, Result.status == "ranked")
        ).all()
    )
    data = result_out(result) if result else None
    if data:
        data["breakdown"] = [
            {**b, "judge": f"Judge {i}"} for i, b in enumerate(data["breakdown"], start=1)
        ]
    return {"published": True, "result": data, "total_ranked": total_ranked, "feedback": feedback}


@router.get("/certificates/me")
def my_certificate(
    user: User = Depends(require_role("participant")),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    cert = db.scalars(
        select(Certificate).where(
            Certificate.user_id == user.id, Certificate.hackathon_id == hackathon.id
        )
    ).first()
    return {"certificate": certificate_out(cert) if cert else None, "published": hackathon.results_published}


@router.get("/certificates/verify/{code}")
def verify_certificate(code: str, db: Session = Depends(get_db)):
    """Public check that a certificate is genuine. Returns only what's printed on it."""
    cert = db.scalars(
        select(Certificate).where(Certificate.verification_code == code.strip().upper()[:32])
    ).first()
    if cert is None:
        raise HTTPException(status_code=404, detail="No certificate matches this code.")
    data = certificate_out(cert)
    return {"valid": True, "certificate": data}
