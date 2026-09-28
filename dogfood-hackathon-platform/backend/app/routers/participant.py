import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db, utcnow
from ..deps import get_hackathon, require_role
from ..models import Hackathon, Submission, Team, TeamMember, User
from ..schemas import SubmissionIn, TeamCreateIn, TeamJoinIn
from ..serializers import hackathon_out, is_locked, submission_out, team_out
from ..services import eligibility

router = APIRouter(prefix="/api", tags=["participant"])
participant_only = require_role("participant")


@router.get("/hackathon")
def current_hackathon(hackathon: Hackathon = Depends(get_hackathon)):
    """Public: the login page shows the event name and dates."""
    return hackathon_out(hackathon)


def _my_team(db: Session, user: User, hackathon: Hackathon) -> Team | None:
    member = db.scalars(
        select(TeamMember).where(
            TeamMember.user_id == user.id, TeamMember.hackathon_id == hackathon.id
        )
    ).first()
    return member.team if member else None


def _ensure_not_published(hackathon: Hackathon) -> None:
    if hackathon.results_published:
        raise HTTPException(status_code=409, detail="Results are published. The event is closed.")


def _new_invite_code(db: Session) -> str:
    while True:
        code = secrets.token_hex(3).upper()  # e.g. "7F3A0C"
        if not db.scalars(select(Team).where(Team.invite_code == code)).first():
            return code


@router.get("/teams/me")
def get_my_team(
    user: User = Depends(participant_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    team = _my_team(db, user, hackathon)
    return {"team": team_out(team, include_invite=True) if team else None}


@router.post("/teams", status_code=201)
def create_team(
    body: TeamCreateIn,
    user: User = Depends(participant_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    _ensure_not_published(hackathon)
    if _my_team(db, user, hackathon):
        raise HTTPException(status_code=409, detail="You're already on a team.")
    taken = db.scalars(
        select(Team).where(
            Team.hackathon_id == hackathon.id, func.lower(Team.name) == body.name.lower()
        )
    ).first()
    if taken:
        raise HTTPException(status_code=409, detail="That team name is taken. Try another.")

    team = Team(
        hackathon_id=hackathon.id,
        name=body.name,
        invite_code=_new_invite_code(db),
        created_by_id=user.id,
    )
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=user.id, hackathon_id=hackathon.id, is_lead=True))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You're already on a team.")
    db.refresh(team)
    return {"team": team_out(team, include_invite=True)}


@router.post("/teams/join")
def join_team(
    body: TeamJoinIn,
    user: User = Depends(participant_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    _ensure_not_published(hackathon)
    if _my_team(db, user, hackathon):
        raise HTTPException(status_code=409, detail="You're already on a team.")
    team = db.scalars(
        select(Team).where(
            Team.hackathon_id == hackathon.id,
            Team.invite_code == body.invite_code.strip().upper(),
        )
    ).first()
    if team is None:
        raise HTTPException(status_code=404, detail="No team uses that invite code.")
    if len(team.members) >= hackathon.max_team_size:
        raise HTTPException(
            status_code=409, detail=f"This team is full ({hackathon.max_team_size} members max)."
        )
    if team.submission and is_locked(team.submission):
        raise HTTPException(
            status_code=409, detail="This team's project is already being judged, so it can't take new members."
        )

    db.add(TeamMember(team_id=team.id, user_id=user.id, hackathon_id=hackathon.id))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You're already on a team.")
    db.refresh(team)
    if team.submission:
        eligibility.apply(team.submission, hackathon, team)  # team size changed
    db.commit()
    return {"team": team_out(team, include_invite=True)}


@router.get("/submissions/me")
def get_my_submission(
    user: User = Depends(participant_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    team = _my_team(db, user, hackathon)
    if team is None or team.submission is None:
        return {"submission": None, "has_team": team is not None}
    return {"submission": submission_out(team.submission), "has_team": True}


@router.put("/submissions/me")
def save_my_submission(
    body: SubmissionIn,
    user: User = Depends(participant_only),
    hackathon: Hackathon = Depends(get_hackathon),
    db: Session = Depends(get_db),
):
    """Create or update the team's single submission, then run eligibility."""
    _ensure_not_published(hackathon)
    team = _my_team(db, user, hackathon)
    if team is None:
        raise HTTPException(status_code=409, detail="Create or join a team before submitting.")

    sub = team.submission
    now = utcnow()
    if sub is None:
        sub = Submission(hackathon_id=hackathon.id, team_id=team.id, submitted_by_id=user.id)
        db.add(sub)
    elif is_locked(sub):
        raise HTTPException(
            status_code=409, detail="Judging has started, so this submission can't be changed."
        )

    sub.title = body.title
    sub.summary = body.summary
    sub.repo_url = body.repo_url
    sub.demo_url = body.demo_url
    sub.tech_stack = body.tech_stack
    sub.submitted_by_id = user.id
    sub.submitted_at = now
    sub.updated_at = now
    eligibility.apply(sub, hackathon, team)
    db.commit()
    db.refresh(sub)
    return {"submission": submission_out(sub)}
