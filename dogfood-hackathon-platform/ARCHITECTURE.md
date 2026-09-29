# Architecture

This document explains how the Dogfood Hackathon Platform is put together: the pieces, how a request moves through them, how it's deployed, and why it's built this way.

For the database tables see [DATA-MODEL.md](DATA-MODEL.md). For scoring rules see [JUDGING.md](JUDGING.md).

## 1. The short version

It's one container running one process on one port.

```
                 Browser  (React single-page app)
                    │
                    │  same origin, JSON over /api/*, "Authorization: Bearer <JWT>"
                    ▼
┌──────────────────────── Docker container · port 8000 · uid 10001 ────────────────────────┐
│                                                                                           │
│   Uvicorn ─► FastAPI app  (backend/app/main.py)                                           │
│                ├─ middleware      security headers on every response                      │
│                ├─ /api/health     liveness + a real read of the users table               │
│                ├─ /api/*          routers: auth · participant · judge · admin ·           │
│                │                           export · results                               │
│                │                    └─► services: eligibility.py · scoring.py             │
│                └─ /*              the built React app (index.html + /assets)              │
│                                                                                           │
│   SQLAlchemy 2 ORM ─► SQLite file  /data/dogfood.db   ◄── Docker named volume             │
│                       JWT secret   /data/.jwt_secret  (generated on first start, 0600)    │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

There's no reverse proxy, no second service, no message queue, no cache and no external API. Once the image is built, the app works fully offline.

## 2. Components

### 2.1 Frontend (`frontend/`)

A React 18 single-page app, built with Vite 5 and plain CSS. React Router handles navigation.

| Piece | File | Job |
|---|---|---|
| Entry | `src/main.jsx` | Mounts the app, loads the bundled Archivo font and `styles.css`. |
| Routes | `src/App.jsx` | One route tree per role (`/participant/*`, `/judge/*`, `/admin/*`), plus public `/login`, `/register` and `/verify/:code`. `RequireRole` redirects anyone on the wrong route to their own home. |
| API client | `src/api.js` | `api()` wraps `fetch`: it adds the Bearer token, turns FastAPI error payloads into readable messages, and signs the user out on a 401. `download()` does authenticated file downloads for the exports. |
| Session | `src/auth.jsx` | Holds the signed-in user. The token lives in `localStorage` (see [Security](#6-security-model)). |
| Shared UI | `src/components/` | `Layout` (role-aware sidebar), `Leaderboard` (ranking plus the score working), and `ui.jsx` (badges, alerts, the `useLoad`/`useAction` data hooks, formatters). |
| Pages | `src/pages/{participant,judge,admin}/` | One file per screen. |

The frontend holds no business rules. Eligibility, scoring, ranking and permissions all live on the server. The browser only shows what the API returns, and the API refuses anything a role isn't allowed to do, even if someone calls it directly.

### 2.2 Backend (`backend/app/`)

A FastAPI app with SQLAlchemy 2 and Pydantic 2.

| Module | Job |
|---|---|
| `main.py` | Builds the app. The lifespan hook creates tables and seeds demo data on first start. Also holds the security-header middleware, `/api/health`, router registration, and static/SPA serving with a path-traversal guard. |
| `config.py` | Reads settings from environment variables (see [§5.3](#53-configuration)). Loads or creates the JWT secret. |
| `database.py` | Engine, session factory, `utcnow()`, and the `PRAGMA foreign_keys=ON` hook. |
| `models.py` | The ten tables. |
| `security.py` | bcrypt hashing, plus JWT encode/decode with the algorithm pinned to HS256. |
| `deps.py` | Dependency chain: `get_db` → `get_current_user` → `require_role(...)` → `get_hackathon`. |
| `schemas.py` | Pydantic request bodies with validation (lengths, email format, password rules, score ≥ 0). |
| `serializers.py` | ORM objects to JSON, plus derived states (submission *stage*, hackathon *phase*, *locked*). |
| `services/eligibility.py` | The eligibility rules. Pure functions, each returning a readable check. |
| `services/scoring.py` | Normalization, averaging, ranking, publishing and certificate issuing, all in one file. |
| `routers/*.py` | HTTP endpoints, grouped by who uses them (table below). |
| `seed.py` | Demo data plus the `python -m app.seed [--reset]` CLI. |

#### API surface

Every endpoint is listed below with its access rule. You can also browse them interactively at `/api/docs` (Swagger UI).

| Router | Endpoints | Who |
|---|---|---|
| health | `GET /api/health` | public |
| auth | `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me` | public / any signed-in user |
| participant | `GET /api/hackathon` (public); `GET/POST /api/teams…`, `POST /api/teams/join`, `GET/PUT /api/submissions/me` | participant |
| judge | `GET /api/judge/assignments`, `GET /api/judge/assignments/{id}`, `POST /api/judge/assignments/{id}/evaluation` | judge (own assignments only) |
| admin | `GET /api/admin/overview`, `…/participants`, `…/judges`, `…/teams`, `…/submissions`, `…/evaluations`; `POST/DELETE /api/admin/assignments`; `GET/POST/PUT/DELETE /api/admin/criteria`; `GET /api/admin/results`, `POST …/results/calculate`, `…/publish`, `…/unpublish` | admin |
| export | `GET /api/admin/export/results.csv`, `GET /api/admin/export/event.json` | admin |
| results | `GET /api/results` (any signed-in user; empty until published), `GET /api/results/me`, `GET /api/certificates/me` (participant), `GET /api/certificates/verify/{code}` (public) | mixed |

### 2.3 Database

SQLite through SQLAlchemy 2. There are ten tables (User, Hackathon, Team, TeamMember, Submission, Criterion, JudgeAssignment, Evaluation, Result, Certificate), described field by field in [DATA-MODEL.md](DATA-MODEL.md).

- The schema is created at startup with `Base.metadata.create_all()`. There's no migration tool (see [§7](#7-known-trade-offs)).
- Foreign keys are enforced (`PRAGMA foreign_keys=ON` on every connection).
- Important rules are database constraints, not just application checks. One team per person per hackathon is a unique constraint, and so is one evaluation per assignment and one judge per submission.

## 3. How a request flows

Every authenticated API call goes through the same chain.

```
HTTP request
  └─ security_headers middleware
      └─ router function
          ├─ get_db()               → one SQLAlchemy session per request, closed afterwards
          ├─ get_current_user()     → decode JWT (HS256 only) → load User from the DB
          ├─ require_role("…")      → 403 unless the user's role in the DB matches
          ├─ get_hackathon()        → the current event
          ├─ Pydantic body          → 422 with field-level messages if invalid
          ├─ business rule checks   → 404 / 409 with a message the UI shows as-is
          ├─ services.*             → eligibility / scoring
          ├─ db.commit()
          └─ serializers.*          → JSON response
```

Two details matter:

1. **The role comes from the database, not the token.** The token only identifies the user. If an admin changed someone's role, the change would apply on their next request.
2. **Errors are written for people.** Every `HTTPException` detail is a sentence the UI can show directly, like "Judging has started, so this submission can't be changed."

### 3.1 The event lifecycle, end to end

This is the critical path, and which component does each step.

| # | Step | Actor | Endpoint | Server-side effect |
|---|---|---|---|---|
| 1 | Sign in | anyone | `POST /api/auth/login` | bcrypt check, JWT issued |
| 2 | Create or join a team | participant | `POST /api/teams` or `/api/teams/join` | `Team` + `TeamMember` rows; unique constraint stops a second team |
| 3 | Submit a project | participant | `PUT /api/submissions/me` | `Submission` upserted |
| 4 | Eligibility check | server | (same call) | `eligibility.apply()` stores the checks and the status |
| 5 | Assign a judge | admin | `POST /api/admin/assignments` | `JudgeAssignment(pending)`; the submission is now locked |
| 6 | Score | judge | `POST /api/judge/assignments/{id}/evaluation` | `Evaluation` with a rubric snapshot and normalized score; assignment set to `completed` |
| 7 | Calculate | admin | `POST /api/admin/results/calculate` | `Result` rows rebuilt from scratch (draft) |
| 8 | Publish | admin | `POST /api/admin/results/publish` | Recalculate, issue `Certificate`s, set `results_published` |
| 9 | See the result | participant | `GET /api/results/me`, `GET /api/results` | Rank, working, anonymous feedback |
| 10 | Certificate | participant / public | `GET /api/certificates/me`, `/verify/{code}` | Printable certificate, public verification |

## 4. Frontend ↔ backend ↔ database connectivity

- **Browser to API.** Same origin. FastAPI serves both the SPA and `/api`, so there's no CORS configuration to get wrong. In development, Vite proxies `/api` to `localhost:8000` (`vite.config.js`).
- **API to database.** One SQLAlchemy engine pointed at `DATABASE_URL` (default `sqlite:////data/dogfood.db` in Docker).
- **Proving it works.** `GET /api/health` reads the `users` table through a real session (a bare `SELECT 1` would succeed in SQLite without touching the file). It returns `{"status":"ok"}` only if that works, and HTTP 503 otherwise. The Docker `HEALTHCHECK` calls this endpoint every 10 seconds, so `docker compose ps` only shows *healthy* when the process is up **and** the database answers.

## 5. Deployment

### 5.1 Image (`Dockerfile`)

It's a multi-stage build.

1. **`node:20-slim` stage.** Runs `npm ci` from the committed lockfile, then `npm run build` produces `dist/`. This stage is thrown away.
2. **`python:3.12-slim` stage.**
   - Runs `pip install` with pinned versions.
   - Creates an unprivileged user `dogfood` (uid 10001) and a `/data` directory it owns.
   - Copies `backend/` and the built `dist/` into `/app/static`.
   - Declares a `HEALTHCHECK`, and runs `uvicorn app.main:app` on port 8000 as that user.

`.dockerignore` keeps `node_modules`, caches, local databases and secrets out of the build context.

### 5.2 Compose (`docker-compose.yml`)

There's one service, `app`. It publishes `8000:8000` and mounts the named volume `dogfood-data` at `/data`. That volume holds everything that must survive a restart: the SQLite file and the JWT secret.

Startup sequence:

1. Uvicorn starts, and the FastAPI lifespan hook runs.
2. `init_db()` creates any missing tables.
3. If `SEED_DEMO_DATA=true` **and** the `users` table is empty, `seed()` inserts the demo event. It never runs twice and never touches real data.
4. The app serves requests. The healthcheck turns *healthy* within about 10 seconds.

### 5.3 Configuration

All settings are environment variables. The defaults work out of the box.

| Variable | Default (Docker) | Meaning |
|---|---|---|
| `DATA_DIR` | `/data` | Where the database and JWT secret live |
| `DATABASE_URL` | `sqlite:///$DATA_DIR/dogfood.db` | SQLAlchemy URL |
| `STATIC_DIR` | `/app/static` | Built frontend |
| `SEED_DEMO_DATA` | `true` | Seed the demo event when the database is empty |
| `JWT_SECRET` | *(generated)* | Pin the signing key. If unset, it's generated once and stored in `$DATA_DIR/.jwt_secret` |
| `TOKEN_TTL_MINUTES` | `480` | Session length |
| `BCRYPT_ROUNDS` | `12` | Password hashing cost (the tests use 4 for speed) |

## 6. Security model

| Concern | How it's handled |
|---|---|
| Passwords | bcrypt, cost 12. A dummy hash is checked when the email is unknown, so timing doesn't reveal which accounts exist. The error message is identical either way. |
| Sessions | HS256 JWTs with an 8-hour expiry. Decoding pins `algorithms=["HS256"]`, so a token can't choose its own algorithm. |
| Authorization | `require_role()` on every protected route, with the role read from the database. Judges get **404**, not 403, for other judges' assignments, so ids can't be probed. |
| Self-registration | Always creates a participant. A `role` field in the request body is ignored. |
| Input | Pydantic validation on every body. Score ranges are validated against the criteria in the database. |
| Output | CSV exports neutralize spreadsheet formulas (`=`, `+`, `-`, `@`), because team and project names are user-controlled. |
| Headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` on `/api/*`. |
| Static files | Resolved paths must stay inside `STATIC_DIR`; anything else falls back to `index.html`. |
| Container | Runs as a non-root user. No secrets in the image or the repository. |

## 7. Technical decisions and why

| Decision | Why | What we gave up |
|---|---|---|
| **One container, FastAPI serves the SPA** | One port and one process. A fresh machine needs only Docker. There's no CORS, no nginx config, no service ordering. | Static files aren't served by a dedicated web server. That's fine at hackathon scale. |
| **SQLite in a named volume** | Zero setup, one file to back up, works offline, plenty fast for hundreds of users. | One writer at a time and one server. Moving to Postgres is a `DATABASE_URL` change plus a driver. |
| **Recalculate results from scratch** | Calculation is idempotent: pressing the button twice can't drift. The ranking is always a pure function of the stored evaluations. | Slightly more work per calculation (irrelevant at this size). |
| **Rubric snapshot in each evaluation** | Admins can edit criteria mid-event without corrupting submitted scores. Normalizing to 100 keeps old and new evaluations comparable. | Some duplicated data in each evaluation row. |
| **Lock a submission once a judge is assigned** | A judge must score the version everyone else sees. No moving target. | Teams can't fix typos after assignment. An admin can remove a *pending* assignment to unlock it. |
| **Rules as database constraints** | "One team per person" still holds under concurrent requests or a bug in the application code. | None worth noting. |
| **Single active hackathon** | Keeps every screen simple. The data model already scopes everything by `hackathon_id`. | Running two events at once needs an event picker. |
| **`create_all`, no migrations** | Nothing to run by hand. The schema is created on first start. | Schema changes need `docker compose down -v`, or Alembic added later. |
| **Token in `localStorage`** | Simple, and no CSRF handling needed for a same-origin MVP. | Readable by injected script. Production should use httpOnly cookies with CSRF protection. |

## 8. Testing architecture

- **Backend (`backend/tests/`, pytest, 32 tests).** They run against a throwaway SQLite file with the real app, through FastAPI's `TestClient`, reseeded before every test. They cover the whole lifecycle plus authorization. Run them with `docker compose run --rm app pytest`.
- **Browser (`e2e/demo_flow.py`, optional).** Playwright clicks through the full lifecycle in Chromium against a running container, asserts each step and saves screenshots. It fails on any browser console error.
- **Demo recording (`e2e/record_demo.py`, optional).** The same flow, paced for humans and captioned, recorded to video.
