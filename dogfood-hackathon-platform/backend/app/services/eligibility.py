"""Basic, explainable eligibility rules.

Every rule produces a check the participant can read, so an ineligible
submission always says exactly what to fix.
"""
from datetime import datetime
from urllib.parse import urlparse

from ..database import utcnow
from ..models import Hackathon, Submission, Team

MIN_SUMMARY_CHARS = 50


def _is_web_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and "." in parsed.netloc


def _check(rule: str, passed: bool, detail: str) -> dict:
    return {"rule": rule, "passed": bool(passed), "detail": detail}


def evaluate(
    hackathon: Hackathon,
    team: Team,
    summary: str,
    repo_url: str,
    demo_url: str,
    submitted_at: datetime | None = None,
) -> list[dict]:
    submitted_at = submitted_at or utcnow()
    size = len(team.members)
    summary_len = len(summary.strip())

    checks = [
        _check(
            "Submitted before the deadline",
            submitted_at <= hackathon.submission_deadline,
            "Submitted on time."
            if submitted_at <= hackathon.submission_deadline
            else "This was submitted after the submission deadline.",
        ),
        _check(
            "Team size",
            hackathon.min_team_size <= size <= hackathon.max_team_size,
            f"{size} member(s). Allowed: {hackathon.min_team_size}–{hackathon.max_team_size}.",
        ),
        _check(
            "Project summary",
            summary_len >= MIN_SUMMARY_CHARS,
            f"{summary_len} characters. Needs at least {MIN_SUMMARY_CHARS}.",
        ),
        _check(
            "Source code link",
            _is_web_url(repo_url),
            "Link looks valid."
            if _is_web_url(repo_url)
            else "Add a full http(s) link to your repository.",
        ),
    ]
    if demo_url.strip():
        checks.append(
            _check(
                "Demo link",
                _is_web_url(demo_url),
                "Link looks valid." if _is_web_url(demo_url) else "The demo link isn't a valid http(s) URL.",
            )
        )
    return checks


def apply(submission: Submission, hackathon: Hackathon, team: Team) -> None:
    """(Re)run the rules and store the outcome on the submission."""
    checks = evaluate(
        hackathon,
        team,
        submission.summary,
        submission.repo_url,
        submission.demo_url,
        submitted_at=submission.submitted_at,
    )
    submission.eligibility_checks = checks
    submission.eligibility_status = "eligible" if all(c["passed"] for c in checks) else "ineligible"
