"""Request bodies. Responses are plain dicts built in serializers.py."""
import re

from pydantic import BaseModel, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginIn(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=128)


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name is too short.")
        return v

    @field_validator("password")
    @classmethod
    def password_rules(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password is too long.")
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
            raise ValueError("Use at least one letter and one number.")
        return v


class TeamCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)

    @field_validator("name")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Team name is too short.")
        return v


class TeamJoinIn(BaseModel):
    invite_code: str = Field(min_length=4, max_length=16)


class SubmissionIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    summary: str = Field(min_length=1, max_length=4000)
    repo_url: str = Field(min_length=1, max_length=500)
    demo_url: str = Field(default="", max_length=500)
    tech_stack: str = Field(default="", max_length=255)

    @field_validator("title", "summary", "repo_url", "demo_url", "tech_stack")
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()


class CriterionIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=255)
    max_score: int = Field(ge=1, le=100)
    position: int | None = Field(default=None, ge=0, le=1000)


class AssignmentIn(BaseModel):
    submission_id: int
    judge_id: int


class ScoreIn(BaseModel):
    criterion_id: int
    score: int = Field(ge=0)


class EvaluationIn(BaseModel):
    scores: list[ScoreIn] = Field(min_length=1, max_length=50)
    feedback: str = Field(default="", max_length=1000)


class PublishIn(BaseModel):
    allow_pending: bool = False
