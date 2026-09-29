"""Admin data export: the "out" half of the import/export paths in DATA-MODEL.md.

- results.csv  : the current ranking (draft or published), one row per submission
- event.json   : a full snapshot of the event, minus password hashes

The "in" half is the seed CLI (python -m app.seed). See DATA-MODEL.md.
"""
import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db, utcnow
from ..deps import get_hackathon, require_role
from ..models import Certificate, Hackathon, Result, Submission, Team, User
from ..serializers import (
    assignment_out,
    certificate_out,
    hackathon_out,
    iso,
    result_out,
    submission_out,
    team_out,
    user_out,
)

router = APIRouter(prefix="/api/admin/export", tags=["export"])
admin_only = require_role("admin")

EXPORT_FORMAT_VERSION = 1
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value) -> str:
    """Stop spreadsheet apps from executing user-supplied text as a formula
    (CSV/formula injection). Numbers are left alone."""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def _ordered_results(db: Session, hackathon: Hackathon) -> list[Result]:
    results = db.scalars(select(Result).where(Result.hackathon_id == hackathon.id)).all()
    return sorted(results, key=lambda r: (r.rank is None, r.rank or 0, r.team.name))


@router.get("/results.csv")
def export_results_csv(
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "rank", "team", "project", "status", "final_score", "judge_count",
            "pending_evaluations", "normalized_scores", "note", "published",
        ]
    )
    for r in _ordered_results(db, hackathon):
        writer.writerow(
            [
                r.rank if r.rank is not None else "",
                _safe_cell(r.team.name),
                _safe_cell(r.submission.title),
                r.status,
                f"{r.final_score:.2f}" if r.final_score is not None else "",
                r.judge_count,
                r.pending_count,
                ";".join(f"{b['normalized_score']:.2f}" for b in (r.breakdown or [])),
                _safe_cell(r.note),
                "yes" if hackathon.results_published else "no",
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dogfood-results.csv"'},
    )


@router.get("/event.json")
def export_event_json(
    _: User = Depends(admin_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    users = db.scalars(select(User).order_by(User.id)).all()
    teams = db.scalars(select(Team).where(Team.hackathon_id == hackathon.id).order_by(Team.id)).all()
    submissions = db.scalars(
        select(Submission).where(Submission.hackathon_id == hackathon.id).order_by(Submission.id)
    ).all()
    certificates = db.scalars(
        select(Certificate).where(Certificate.hackathon_id == hackathon.id).order_by(Certificate.id)
    ).all()

    payload = {
        "format_version": EXPORT_FORMAT_VERSION,
        "exported_at": iso(utcnow()),
        "hackathon": hackathon_out(hackathon),
        # Never export password hashes.
        "users": [{**user_out(u), "created_at": iso(u.created_at)} for u in users],
        "teams": [team_out(t, include_invite=True) for t in teams],
        "submissions": [submission_out(s) for s in submissions],
        "assignments": [assignment_out(a) for s in submissions for a in s.assignments],
        "results": [result_out(r) for r in _ordered_results(db, hackathon)],
        "certificates": [certificate_out(c) for c in certificates],
    }
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": 'attachment; filename="dogfood-event-export.json"'},
    )
