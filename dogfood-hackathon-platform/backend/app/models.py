"""The ten MVP tables. Nothing else."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base, utcnow

ROLES = ("admin", "participant", "judge")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    memberships: Mapped[list["TeamMember"]] = relationship(back_populates="user")


class Hackathon(Base):
    __tablename__ = "hackathons"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    tagline: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    submission_deadline: Mapped[datetime] = mapped_column(DateTime)
    min_team_size: Mapped[int] = mapped_column(Integer, default=1)
    max_team_size: Mapped[int] = mapped_column(Integer, default=4)
    results_published: Mapped[bool] = mapped_column(Boolean, default=False)
    results_published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    results_calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    criteria: Mapped[list["Criterion"]] = relationship(
        back_populates="hackathon", order_by="Criterion.position"
    )
    teams: Mapped[list["Team"]] = relationship(back_populates="hackathon")


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("hackathon_id", "name", name="uq_team_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    hackathon_id: Mapped[int] = mapped_column(ForeignKey("hackathons.id"))
    name: Mapped[str] = mapped_column(String(80))
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    hackathon: Mapped[Hackathon] = relationship(back_populates="teams")
    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team", order_by="TeamMember.joined_at", cascade="all, delete-orphan"
    )
    submission: Mapped[Optional["Submission"]] = relationship(
        back_populates="team", uselist=False
    )


class TeamMember(Base):
    __tablename__ = "team_members"
    # One team per participant per hackathon, enforced by the database.
    __table_args__ = (
        UniqueConstraint("hackathon_id", "user_id", name="uq_one_team_per_hackathon"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    hackathon_id: Mapped[int] = mapped_column(ForeignKey("hackathons.id"))
    is_lead: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    team: Mapped[Team] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    hackathon_id: Mapped[int] = mapped_column(ForeignKey("hackathons.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), unique=True)
    submitted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    repo_url: Mapped[str] = mapped_column(String(500))
    demo_url: Mapped[str] = mapped_column(String(500), default="")
    tech_stack: Mapped[str] = mapped_column(String(255), default="")
    eligibility_status: Mapped[str] = mapped_column(String(20), default="pending")
    eligibility_checks: Mapped[list] = mapped_column(JSON, default=list)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    team: Mapped[Team] = relationship(back_populates="submission")
    assignments: Mapped[list["JudgeAssignment"]] = relationship(
        back_populates="submission", order_by="JudgeAssignment.assigned_at"
    )


class Criterion(Base):
    __tablename__ = "criteria"

    id: Mapped[int] = mapped_column(primary_key=True)
    hackathon_id: Mapped[int] = mapped_column(ForeignKey("hackathons.id"))
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(255), default="")
    max_score: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, default=0)

    hackathon: Mapped[Hackathon] = relationship(back_populates="criteria")


class JudgeAssignment(Base):
    __tablename__ = "judge_assignments"
    __table_args__ = (
        UniqueConstraint("submission_id", "judge_id", name="uq_judge_once_per_submission"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    judge_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | completed
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    submission: Mapped[Submission] = relationship(back_populates="assignments")
    judge: Mapped[User] = relationship(foreign_keys=[judge_id])
    evaluation: Mapped[Optional["Evaluation"]] = relationship(
        back_populates="assignment", uselist=False
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("judge_assignments.id"), unique=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    judge_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Snapshot of the rubric at scoring time:
    # [{criterion_id, name, max_score, score}, ...]
    scores: Mapped[list] = mapped_column(JSON)
    raw_total: Mapped[float] = mapped_column(Float)
    max_total: Mapped[float] = mapped_column(Float)
    normalized_score: Mapped[float] = mapped_column(Float)
    feedback: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    assignment: Mapped[JudgeAssignment] = relationship(back_populates="evaluation")
    judge: Mapped[User] = relationship(foreign_keys=[judge_id])


class Result(Base):
    __tablename__ = "results"
    __table_args__ = (UniqueConstraint("hackathon_id", "submission_id", name="uq_result"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    hackathon_id: Mapped[int] = mapped_column(ForeignKey("hackathons.id"))
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    status: Mapped[str] = mapped_column(String(20))  # ranked | not_ranked
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    final_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    judge_count: Mapped[int] = mapped_column(Integer, default=0)
    pending_count: Mapped[int] = mapped_column(Integer, default=0)
    # [{judge, raw_total, max_total, normalized_score}, ...]
    breakdown: Mapped[list] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(String(255), default="")
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    submission: Mapped[Submission] = relationship()
    team: Mapped[Team] = relationship()


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (UniqueConstraint("hackathon_id", "user_id", name="uq_certificate"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    hackathon_id: Mapped[int] = mapped_column(ForeignKey("hackathons.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    result_id: Mapped[Optional[int]] = mapped_column(ForeignKey("results.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(30))  # winner | runner_up | second_runner_up | participation
    title: Mapped[str] = mapped_column(String(80))
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    final_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    verification_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship()
    team: Mapped[Team] = relationship()
    hackathon: Mapped[Hackathon] = relationship()
