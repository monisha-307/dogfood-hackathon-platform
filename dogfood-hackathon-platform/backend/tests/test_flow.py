"""Tests for the critical demo flow:
login → team → submission → eligibility → assignment → evaluation →
normalization → publication → result → certificate, plus authorization.
"""
from app.models import User
from app.security import hash_password
from app.services.scoring import average, normalize

from .conftest import GOOD_SUBMISSION, login


def scores_for(client, headers, assignment_id, values):
    detail = client.get(f"/api/judge/assignments/{assignment_id}", headers=headers).json()
    return [
        {"criterion_id": c["id"], "score": v} for c, v in zip(detail["criteria"], values)
    ]


def submit_as_new_team(client, participant, team_name="Late Night Labs", body=GOOD_SUBMISSION):
    r = client.post("/api/teams", json={"name": team_name}, headers=participant)
    assert r.status_code == 201, r.text
    r = client.put("/api/submissions/me", json=body, headers=participant)
    assert r.status_code == 200, r.text
    return r.json()["submission"]


def judge_id(client, admin):
    return client.get("/api/admin/judges", headers=admin).json()["judges"][0]["id"]


# ------------------------------------------------------------------ 1. login

def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_login_success_and_me(client):
    headers = login(client, "admin@dogfood.dev", "Admin@123")
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["role"] == "admin"


def test_login_is_case_insensitive_on_email(client):
    login(client, "ADMIN@dogfood.dev", "Admin@123")


def test_login_wrong_password_and_unknown_email_look_the_same(client):
    a = client.post("/api/auth/login", json={"email": "admin@dogfood.dev", "password": "nope"})
    b = client.post("/api/auth/login", json={"email": "ghost@dogfood.dev", "password": "nope"})
    assert a.status_code == b.status_code == 401
    assert a.json()["detail"] == b.json()["detail"]


def test_register_always_creates_participant(client):
    r = client.post(
        "/api/auth/register",
        json={"full_name": "New Person", "email": "new@x.dev", "password": "Secret123", "role": "admin"},
    )
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "participant"


# ------------------------------------------------------------------ 2. teams

def test_create_team_and_join_with_invite_code(client, participant):
    team = client.post("/api/teams", json={"name": "Night Owls"}, headers=participant).json()["team"]
    assert team["members"][0]["is_lead"] is True

    client.post(
        "/api/auth/register",
        json={"full_name": "Teammate", "email": "mate@x.dev", "password": "Secret123"},
    )
    mate = login(client, "mate@x.dev", "Secret123")
    r = client.post("/api/teams/join", json={"invite_code": team["invite_code"].lower()}, headers=mate)
    assert r.status_code == 200
    assert len(r.json()["team"]["members"]) == 2


def test_cannot_be_on_two_teams(client, participant):
    client.post("/api/teams", json={"name": "Team One"}, headers=participant)
    r = client.post("/api/teams", json={"name": "Team Two"}, headers=participant)
    assert r.status_code == 409


def test_cannot_join_team_whose_project_is_being_judged(client, participant):
    # Seeded "Byte Bandits" (BYTE42) already has a judge assigned.
    r = client.post("/api/teams/join", json={"invite_code": "BYTE42"}, headers=participant)
    assert r.status_code == 409


# ------------------------------------------------------------------ 3–4. submission + eligibility

def test_submission_requires_a_team(client, participant):
    r = client.put("/api/submissions/me", json=GOOD_SUBMISSION, headers=participant)
    assert r.status_code == 409


def test_good_submission_is_eligible(client, participant):
    sub = submit_as_new_team(client, participant)
    assert sub["eligibility_status"] == "eligible"
    assert all(c["passed"] for c in sub["eligibility_checks"])
    assert sub["stage"] == "awaiting_judges"


def test_short_summary_and_bad_link_are_ineligible(client, participant):
    bad = {**GOOD_SUBMISSION, "summary": "Too short.", "repo_url": "not a link"}
    sub = submit_as_new_team(client, participant, body=bad)
    assert sub["eligibility_status"] == "ineligible"
    failed = {c["rule"] for c in sub["eligibility_checks"] if not c["passed"]}
    assert failed == {"Project summary", "Source code link"}


def test_fixing_a_submission_makes_it_eligible(client, participant):
    submit_as_new_team(client, participant, body={**GOOD_SUBMISSION, "summary": "short"})
    r = client.put("/api/submissions/me", json=GOOD_SUBMISSION, headers=participant)
    assert r.json()["submission"]["eligibility_status"] == "eligible"


# ------------------------------------------------------------------ 5. judge assignment

def test_admin_assigns_judge_and_submission_locks(client, admin, judge, participant):
    sub = submit_as_new_team(client, participant)
    r = client.post(
        "/api/admin/assignments",
        json={"submission_id": sub["id"], "judge_id": judge_id(client, admin)},
        headers=admin,
    )
    assert r.status_code == 201

    titles = [a["submission"]["title"] for a in client.get("/api/judge/assignments", headers=judge).json()["assignments"]]
    assert "Standup Bot" in titles

    # Once judging starts the team can't edit.
    r = client.put("/api/submissions/me", json=GOOD_SUBMISSION, headers=participant)
    assert r.status_code == 409


def test_ineligible_submission_cannot_be_assigned(client, admin, participant):
    sub = submit_as_new_team(client, participant, body={**GOOD_SUBMISSION, "summary": "short"})
    r = client.post(
        "/api/admin/assignments",
        json={"submission_id": sub["id"], "judge_id": judge_id(client, admin)},
        headers=admin,
    )
    assert r.status_code == 409


def test_same_judge_cannot_be_assigned_twice(client, admin):
    # Seed: FieldNote (submission 2) already has the judge.
    r = client.post(
        "/api/admin/assignments", json={"submission_id": 2, "judge_id": judge_id(client, admin)}, headers=admin
    )
    assert r.status_code == 409


# ------------------------------------------------------------------ 6. evaluation

def pending_assignment_id(client, judge):
    items = client.get("/api/judge/assignments", headers=judge).json()["assignments"]
    return next(a["id"] for a in items if a["status"] == "pending")


def test_judge_scores_and_normalized_score_is_stored(client, judge):
    aid = pending_assignment_id(client, judge)
    body = {"scores": scores_for(client, judge, aid, [10, 20, 15, 10, 9]), "feedback": "Solid."}
    r = client.post(f"/api/judge/assignments/{aid}/evaluation", json=body, headers=judge)
    assert r.status_code == 201, r.text
    ev = r.json()["assignment"]["evaluation"]
    assert ev["raw_total"] == 64 and ev["max_total"] == 100
    assert ev["normalized_score"] == 64.0

    again = client.post(f"/api/judge/assignments/{aid}/evaluation", json=body, headers=judge)
    assert again.status_code == 409


def test_evaluation_rejects_out_of_range_and_missing_scores(client, judge):
    aid = pending_assignment_id(client, judge)
    too_high = scores_for(client, judge, aid, [21, 20, 15, 10, 9])  # Innovation max is 20
    r = client.post(f"/api/judge/assignments/{aid}/evaluation", json={"scores": too_high}, headers=judge)
    assert r.status_code == 422

    missing = scores_for(client, judge, aid, [10, 10, 10, 10])  # only 4 of 5
    r = client.post(f"/api/judge/assignments/{aid}/evaluation", json={"scores": missing}, headers=judge)
    assert r.status_code == 422


# ------------------------------------------------------------------ 7. scoring

def test_normalize_formula():
    assert normalize(84, 100) == 84.0
    assert normalize(30, 40) == 75.0
    assert normalize(0, 0) == 0.0
    assert average([84.0, 70.0]) == 77.0


def test_multiple_judges_are_averaged_and_ranked(client, admin, judge, db):
    second = User(
        email="judge2@dogfood.dev", full_name="Second Judge",
        password_hash=hash_password("Judge2@123"), role="judge",
    )
    db.add(second)
    db.commit()
    judge2 = login(client, "judge2@dogfood.dev", "Judge2@123")

    # Second judge also scores QueueLess (submission 1, seeded at 84).
    client.post("/api/admin/assignments", json={"submission_id": 1, "judge_id": second.id}, headers=admin)
    aid = pending_assignment_id(client, judge2)
    client.post(
        f"/api/judge/assignments/{aid}/evaluation",
        json={"scores": scores_for(client, judge2, aid, [14, 18, 14, 14, 10])},  # 70
        headers=judge2,
    )
    # First judge finishes FieldNote at 90.
    aid = pending_assignment_id(client, judge)
    client.post(
        f"/api/judge/assignments/{aid}/evaluation",
        json={"scores": scores_for(client, judge, aid, [18, 23, 18, 18, 13])},  # 90
        headers=judge,
    )

    results = client.post("/api/admin/results/calculate", headers=admin).json()["results"]
    by_title = {r["submission"]["title"]: r for r in results}
    assert by_title["QueueLess Clinic"]["final_score"] == 77.0  # (84 + 70) / 2
    assert by_title["QueueLess Clinic"]["judge_count"] == 2
    assert by_title["FieldNote"]["final_score"] == 90.0
    assert by_title["FieldNote"]["rank"] == 1
    assert by_title["QueueLess Clinic"]["rank"] == 2


# ------------------------------------------------------------------ 8. publication

def test_publish_blocks_on_pending_unless_confirmed(client, admin, participant):
    r = client.post("/api/admin/results/publish", json={}, headers=admin)
    assert r.status_code == 409  # FieldNote is still pending in the seed

    assert client.get("/api/results", headers=participant).json()["published"] is False

    r = client.post("/api/admin/results/publish", json={"allow_pending": True}, headers=admin)
    assert r.status_code == 200 and r.json()["published"] is True


def test_full_participant_flow_ends_with_result_and_certificate(client, admin, judge, participant):
    sub = submit_as_new_team(client, participant)
    client.post(
        "/api/admin/assignments",
        json={"submission_id": sub["id"], "judge_id": judge_id(client, admin)},
        headers=admin,
    )
    # Judge clears both pending evaluations (seeded FieldNote + the new one).
    for values in ([12, 15, 12, 12, 9], [19, 24, 19, 19, 14]):
        aid = pending_assignment_id(client, judge)
        r = client.post(
            f"/api/judge/assignments/{aid}/evaluation",
            json={"scores": scores_for(client, judge, aid, values), "feedback": "Nice work."},
            headers=judge,
        )
        assert r.status_code == 201

    # Nothing visible before publishing.
    assert client.get("/api/results/me", headers=participant).json()["published"] is False
    assert client.get("/api/certificates/me", headers=participant).json()["certificate"] is None

    r = client.post("/api/admin/results/publish", json={}, headers=admin)
    assert r.status_code == 200, r.text

    mine = client.get("/api/results/me", headers=participant).json()
    assert mine["result"]["final_score"] == 95.0 and mine["result"]["rank"] == 1
    assert mine["feedback"][0]["judge"] == "Judge 1"  # judges are anonymous to teams

    cert = client.get("/api/certificates/me", headers=participant).json()["certificate"]
    assert cert["title"] == "Winner" and cert["recipient"] == "Alex Morgan"
    verified = client.get(f"/api/certificates/verify/{cert['verification_code']}")
    assert verified.status_code == 200 and verified.json()["valid"] is True

    # Scoring is closed after publishing.
    assert client.post("/api/admin/results/calculate", headers=admin).status_code == 409


def test_unpublish_revokes_certificates(client, admin, participant):
    client.post("/api/admin/results/publish", json={"allow_pending": True}, headers=admin)
    priya = login(client, "priya@dogfood.dev", "Demo@2026")
    assert client.get("/api/certificates/me", headers=priya).json()["certificate"] is not None
    client.post("/api/admin/results/unpublish", headers=admin)
    assert client.get("/api/certificates/me", headers=priya).json()["certificate"] is None


# ------------------------------------------------------------------ 9. authorization

def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/admin/overview").status_code == 401
    bad = {"Authorization": "Bearer not.a.token"}
    assert client.get("/api/auth/me", headers=bad).status_code == 401


def test_roles_cannot_cross_over(client, admin, judge, participant):
    assert client.get("/api/admin/overview", headers=participant).status_code == 403
    assert client.get("/api/admin/overview", headers=judge).status_code == 403
    assert client.get("/api/judge/assignments", headers=participant).status_code == 403
    assert client.post("/api/teams", json={"name": "Judges Team"}, headers=judge).status_code == 403
    assert client.post("/api/admin/results/publish", json={}, headers=participant).status_code == 403


def test_judge_cannot_open_someone_elses_assignment(client, admin, db):
    other = User(
        email="judge3@dogfood.dev", full_name="Other Judge",
        password_hash=hash_password("Judge3@123"), role="judge",
    )
    db.add(other)
    db.commit()
    other_headers = login(client, "judge3@dogfood.dev", "Judge3@123")
    # Assignment 2 belongs to the seeded judge.
    assert client.get("/api/judge/assignments/2", headers=other_headers).status_code == 404
