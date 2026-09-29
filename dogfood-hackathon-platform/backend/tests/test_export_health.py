"""Health check (backend → database connectivity) and admin export paths."""
import csv
import io

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.database import engine

from .conftest import GOOD_SUBMISSION


# ------------------------------------------------------------------ health

def test_health_touches_the_database(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_reports_database_failure(client, monkeypatch):
    class BrokenSession:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, *_):
            raise OperationalError("SELECT 1", {}, Exception("disk gone"))

    monkeypatch.setattr("app.main.SessionLocal", BrokenSession)
    r = client.get("/api/health")
    assert r.status_code == 503
    assert r.json()["status"] == "error"


def test_health_fails_when_schema_is_missing(client):
    # A real database fault, not a mock: the table health reads is gone.
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users RENAME TO users_gone"))
    try:
        assert client.get("/api/health").status_code == 503
    finally:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users_gone RENAME TO users"))
    assert client.get("/api/health").json() == {"status": "ok"}


# ------------------------------------------------------------------ export

def read_csv(text):
    return list(csv.DictReader(io.StringIO(text)))


def test_admin_exports_results_csv(client, admin):
    # The seed already calculated a draft ranking.
    r = client.get("/api/admin/export/results.csv", headers=admin)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    rows = read_csv(r.text)
    by_project = {row["project"]: row for row in rows}
    assert by_project["QueueLess Clinic"]["rank"] == "1"
    assert by_project["QueueLess Clinic"]["final_score"] == "84.00"
    assert by_project["QueueLess Clinic"]["normalized_scores"] == "84.00"
    assert by_project["FieldNote"]["status"] == "not_ranked"
    assert by_project["FieldNote"]["published"] == "no"


def test_csv_export_neutralizes_formula_injection(client, admin, participant):
    client.post("/api/teams", json={"name": "=HYPERLINK(\"http://evil\")"}, headers=participant)
    client.put("/api/submissions/me", json={**GOOD_SUBMISSION, "title": "+cmd|' /C calc'!A0"}, headers=participant)
    client.post("/api/admin/results/calculate", headers=admin)

    rows = read_csv(client.get("/api/admin/export/results.csv", headers=admin).text)
    row = next(r for r in rows if "HYPERLINK" in r["team"])
    assert row["team"].startswith("'=")
    assert row["project"].startswith("'+")


def test_event_json_export_is_complete_and_has_no_secrets(client, admin):
    r = client.get("/api/admin/export/event.json", headers=admin)
    assert r.status_code == 200
    data = r.json()
    assert data["format_version"] == 1
    assert data["hackathon"]["name"] == "Dogfood 72-Hour Hackathon"
    assert len(data["users"]) == 7
    assert len(data["teams"]) == 2
    assert len(data["submissions"]) == 2
    assert len(data["assignments"]) == 2
    assert len(data["results"]) == 2
    assert "password" not in r.text and "$2b$" not in r.text  # no bcrypt hashes


def test_exports_are_admin_only(client, judge, participant):
    for path in ("/api/admin/export/results.csv", "/api/admin/export/event.json"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=judge).status_code == 403
        assert client.get(path, headers=participant).status_code == 403
