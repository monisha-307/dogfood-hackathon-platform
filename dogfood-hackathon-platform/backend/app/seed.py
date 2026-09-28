"""Fictional demo data.

Runs automatically on first start (when the database has no users).
Reset any time with:   python -m app.seed --reset
"""
import argparse
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, utcnow
from .models import (
    Criterion,
    Evaluation,
    Hackathon,
    JudgeAssignment,
    Submission,
    Team,
    TeamMember,
    User,
)
from .security import hash_password
from .services import eligibility, scoring

DEMO_ACCOUNTS = [
    # email, password, full name, role
    ("admin@dogfood.dev", "Admin@123", "Ria Kapoor", "admin"),
    ("judge@dogfood.dev", "Judge@123", "Dr. Vikram Iyer", "judge"),
    ("participant@dogfood.dev", "Participant@123", "Alex Morgan", "participant"),
    ("priya@dogfood.dev", "Demo@2026", "Priya Nair", "participant"),
    ("arjun@dogfood.dev", "Demo@2026", "Arjun Mehta", "participant"),
    ("meera@dogfood.dev", "Demo@2026", "Meera Das", "participant"),
    ("kabir@dogfood.dev", "Demo@2026", "Kabir Shah", "participant"),
]

DEFAULT_CRITERIA = [
    ("Innovation", "How new or surprising is the idea?", 20),
    ("Technical Implementation", "Does it work, and is it built well?", 25),
    ("User Experience", "Is it easy and pleasant to use?", 20),
    ("Impact", "Would it matter to real people?", 20),
    ("Presentation", "Is the demo and write-up clear?", 15),
]


def seed(db: Session) -> bool:
    """Insert demo data if the database is empty. Returns True if it seeded."""
    if db.scalars(select(User)).first() is not None:
        return False

    now = utcnow()
    users = {}
    for email, password, name, role in DEMO_ACCOUNTS:
        user = User(email=email, full_name=name, password_hash=hash_password(password), role=role)
        db.add(user)
        users[email] = user
    db.flush()

    hackathon = Hackathon(
        name="Dogfood 72-Hour Hackathon",
        tagline="Build something you'd use yourself.",
        description=(
            "Teams of up to four have 72 hours to build a tool they would actually use. "
            "Submit a working project with a public repository link before the deadline. "
            "Every eligible project is scored by judges on five criteria."
        ),
        starts_at=now - timedelta(hours=48),
        ends_at=now + timedelta(hours=24),
        submission_deadline=now + timedelta(hours=24),
        min_team_size=1,
        max_team_size=4,
    )
    db.add(hackathon)
    db.flush()

    for position, (name, description, max_score) in enumerate(DEFAULT_CRITERIA, start=1):
        db.add(
            Criterion(
                hackathon_id=hackathon.id,
                name=name,
                description=description,
                max_score=max_score,
                position=position,
            )
        )
    db.flush()
    db.refresh(hackathon)

    admin, judge = users["admin@dogfood.dev"], users["judge@dogfood.dev"]

    def make_team(name, code, lead, others, created):
        team = Team(
            hackathon_id=hackathon.id, name=name, invite_code=code, created_by_id=lead.id, created_at=created
        )
        db.add(team)
        db.flush()
        db.add(TeamMember(team_id=team.id, user_id=lead.id, hackathon_id=hackathon.id, is_lead=True, joined_at=created))
        for i, member in enumerate(others, start=1):
            db.add(
                TeamMember(
                    team_id=team.id,
                    user_id=member.id,
                    hackathon_id=hackathon.id,
                    joined_at=created + timedelta(minutes=10 * i),
                )
            )
        db.flush()
        db.refresh(team)
        return team

    bandits = make_team(
        "Byte Bandits", "BYTE42",
        users["priya@dogfood.dev"], [users["arjun@dogfood.dev"]], now - timedelta(hours=46),
    )
    pointers = make_team(
        "Null Pointers", "NULL07",
        users["meera@dogfood.dev"], [users["kabir@dogfood.dev"]], now - timedelta(hours=45),
    )

    def make_submission(team, lead, title, summary, repo, demo, stack, when):
        sub = Submission(
            hackathon_id=hackathon.id,
            team_id=team.id,
            submitted_by_id=lead.id,
            title=title,
            summary=summary,
            repo_url=repo,
            demo_url=demo,
            tech_stack=stack,
            submitted_at=when,
            updated_at=when,
        )
        db.add(sub)
        db.flush()
        eligibility.apply(sub, hackathon, team)
        return sub

    queueless = make_submission(
        bandits, users["priya@dogfood.dev"],
        "QueueLess Clinic",
        "A walk-in clinic queue that texts patients when they're three places from the front, "
        "so nobody has to sit in a crowded waiting room. Front-desk staff manage the queue "
        "from a single screen.",
        "https://github.com/example/queueless-clinic",
        "https://queueless.example.com",
        "FastAPI, React, SQLite",
        now - timedelta(hours=6),
    )
    fieldnote = make_submission(
        pointers, users["meera@dogfood.dev"],
        "FieldNote",
        "An offline-first crop diary for small farms. Log sowing, watering and pest sightings "
        "without signal; it syncs when you're back in range and flags patterns across seasons.",
        "https://github.com/example/fieldnote",
        "",
        "Flutter, SQLite",
        now - timedelta(hours=4),
    )

    # One completed evaluation...
    done = JudgeAssignment(
        submission_id=queueless.id, judge_id=judge.id, assigned_by_id=admin.id,
        status="completed", assigned_at=now - timedelta(hours=3), completed_at=now - timedelta(hours=2),
    )
    # ...and one still pending.
    pending = JudgeAssignment(
        submission_id=fieldnote.id, judge_id=judge.id, assigned_by_id=admin.id,
        status="pending", assigned_at=now - timedelta(hours=3),
    )
    db.add_all([done, pending])
    db.flush()

    given = [17, 21, 16, 18, 12]  # Innovation, Technical, UX, Impact, Presentation
    snapshot = [
        {"criterion_id": c.id, "name": c.name, "max_score": c.max_score, "score": s}
        for c, s in zip(hackathon.criteria, given)
    ]
    raw_total = float(sum(given))
    max_total = float(sum(c.max_score for c in hackathon.criteria))
    db.add(
        Evaluation(
            assignment_id=done.id,
            submission_id=queueless.id,
            judge_id=judge.id,
            scores=snapshot,
            raw_total=raw_total,
            max_total=max_total,
            normalized_score=scoring.normalize(raw_total, max_total),
            feedback="Clear problem, working demo. The SMS timing logic needs tests, and the staff screen could use bigger tap targets.",
            submitted_at=now - timedelta(hours=2),
        )
    )
    db.flush()

    # A draft (unpublished) result so the admin sees a ranking preview straight away.
    scoring.calculate_results(db, hackathon)
    db.commit()
    return True


def reset() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo data.")
    parser.add_argument("--reset", action="store_true", help="Wipe the database first.")
    args = parser.parse_args()
    if args.reset:
        reset()
        print("Database reset and demo data seeded.")
    else:
        from .database import init_db

        init_db()
        with SessionLocal() as db:
            print("Demo data seeded." if seed(db) else "Database already has data; nothing seeded.")
