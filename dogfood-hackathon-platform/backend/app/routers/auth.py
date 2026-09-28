from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import LoginIn, RegisterIn
from ..security import create_access_token, hash_password, verify_password
from ..serializers import user_out

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_response(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id, user.role),
        "token_type": "bearer",
        "user": user_out(user),
    }


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalars(
        select(User).where(func.lower(User.email) == body.email.strip().lower())
    ).first()
    if not verify_password(body.password, user.password_hash if user else None):
        # Same message whether the email or the password was wrong.
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return _token_response(user)


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    """Self-service sign-up. Always creates a participant — never an admin or judge."""
    exists = db.scalars(select(User).where(func.lower(User.email) == body.email)).first()
    if exists:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role="participant",
    )
    db.add(user)
    db.commit()
    return _token_response(user)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)
