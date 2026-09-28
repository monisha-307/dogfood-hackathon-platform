import os
import tempfile

# Isolate tests from any real data *before* the app is imported.
_tmp = tempfile.mkdtemp(prefix="dogfood-tests-")
os.environ["DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["JWT_SECRET"] = "test-only-secret-not-used-anywhere-else"
os.environ["STATIC_DIR"] = os.path.join(_tmp, "no-static")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    with SessionLocal() as session:
        yield session


def login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin(client):
    return login(client, "admin@dogfood.dev", "Admin@123")


@pytest.fixture()
def judge(client):
    return login(client, "judge@dogfood.dev", "Judge@123")


@pytest.fixture()
def participant(client):
    return login(client, "participant@dogfood.dev", "Participant@123")


GOOD_SUBMISSION = {
    "title": "Standup Bot",
    "summary": "A tiny bot that collects async standups in chat and posts one tidy digest every morning.",
    "repo_url": "https://github.com/example/standup-bot",
    "demo_url": "",
    "tech_stack": "Python",
}
