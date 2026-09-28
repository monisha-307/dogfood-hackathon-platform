# Dogfood Hackathon Platform

A self-hosted judging platform for a 72-hour hackathon. It covers the whole journey, from a participant forming a team to printing a certificate, in one Docker container with no cloud services.

```bash
docker compose up --build
```

Open **http://localhost:8000** and click one of the demo accounts on the sign-in page.

---

## Problem

Small hackathons usually judge with a mix of Google Forms, spreadsheets and group chats. Things get lost along the way:

- Submissions arrive that break the rules, and nobody notices until judging.
- Judges score on different scales, so their totals can't be compared fairly.
- Organizers do the ranking by hand in a spreadsheet, and teams never see how their score was worked out.
- Certificates are made one by one in a design tool.

## Solution

One small app with three roles that hand work to each other:

| Role | What they do |
|---|---|
| **Participant** | Creates or joins a team, submits the project, sees eligibility right away, and later sees their rank, judge feedback and certificate. |
| **Judge** | Sees only their assigned projects, scores each criterion, adds feedback, and watches the normalized score update live. |
| **Organizer (admin)** | Checks eligibility, assigns judges, configures criteria, previews the ranking, and publishes results. Publishing also issues certificates. |

Every score shows its working: a team can see exactly how their final number was calculated.

---

## Quick start

**You only need Docker Desktop (or Docker Engine with the Compose plugin).** You don't need Node, Python, a database or a cloud account.

```bash
unzip dogfood-hackathon-platform.zip
cd dogfood-hackathon-platform
docker compose up --build
```

| | |
|---|---|
| App | http://localhost:8000 |
| Health check | http://localhost:8000/api/health returns `{"status":"ok"}` |
| API docs (Swagger) | http://localhost:8000/api/docs |

The first build takes a few minutes while it downloads the base images and packages. After that it starts in seconds. Stop it with `Ctrl+C` or `docker compose down`.

### Demo credentials

The sign-in page has a one-click button for each role, so you don't need to type these.

| Role | Email | Password | Starting state |
|---|---|---|---|
| Organizer (admin) | `admin@dogfood.dev` | `Admin@123` | Two submissions: one judged, one pending |
| Judge | `judge@dogfood.dev` | `Judge@123` | One evaluation done, one pending |
| Participant | `participant@dogfood.dev` | `Participant@123` | **No team yet**, so you can run the full flow |
| Other participants | `priya@`, `arjun@`, `meera@`, `kabir@dogfood.dev` | `Demo@2026` | Already on the two seeded teams |

All names, teams and projects are made up.

---

## Five-minute demo

This is the complete critical flow. An optional browser script, `e2e/demo_flow.py`, runs exactly these steps automatically (see [Tests](#tests)).

1. **Participant:** Sign in as *Participant*. The overview shows a six-step progress track and the next thing to do.
2. **Team:** Click *Set up your team* and create a team (e.g. "Late Night Labs"). You get an invite code for teammates.
3. **Submit:** Go to *Submission* and enter a title, a short summary (try under 50 characters first) and a repo link, then click *Submit project*.
4. **Eligibility:** A short summary fails one check, and the page says exactly why. Lengthen it and click *Update submission*. Every check turns green.
5. **Assign a judge:** Sign out, then sign in as *Organizer*. Under *Submissions & judges*, click *Assign judge* on your project. The submission is now locked.
6. **Score:** Sign in as *Judge* and open your project. Score all five criteria. The black panel shows `raw ÷ max × 100` updating live. Click *Submit evaluation*.
7. **Calculate:** Sign in as *Organizer* and open *Results*. Click *Calculate results* to see the draft ranking and the working for every score.
8. **Publish:** Click *Publish results*. One seeded evaluation is still pending, so the app warns you first. Click *Publish anyway*.
9. **Result:** Sign in as *Participant* and open *Results*. You see your rank, final score, per-criterion scores and anonymous judge feedback.
10. **Certificate:** Click *View certificate*, then *Print or save as PDF*. The verification link at the bottom works without signing in.

To start over, see [Resetting demo data](#resetting-demo-data).

---

## Scoring formula

All scoring lives in one file: `backend/app/services/scoring.py`.

```
normalized_score = (raw_score / maximum_possible_score) * 100     # per judge
final_score      = average(normalized_scores)                     # per project
```

Example with two judges:

| Judge | Raw | Max | Normalized |
|---|---|---|---|
| Judge A | 84 | 100 | 84.00 |
| Judge B | 70 | 100 | 70.00 |
| **Final** | | | **average(84.00, 70.00) = 77.00** |

The rules:

- **Ranking:** Projects are ordered by final score. Equal scores share a rank (1, 1, 3).
- **Who gets ranked:** Only eligible projects with at least one completed evaluation. Others are listed as *Not ranked*, with the reason.
- **Rubric snapshots:** Each evaluation stores the criteria as they were when it was scored. If an admin later changes the criteria, old evaluations stay valid. Because everything is normalized to 100, scores stay comparable.
- **Pending evaluations:** Publishing is blocked while evaluations are pending, unless the organizer confirms. Then projects are ranked on completed scores only.
- **Where the working is shown:** The calculation appears on the admin Results page, the public leaderboard, and each participant's result.

### Default criteria

These are seeded into the database and can be edited under *Criteria*.

| Criterion | Max |
|---|---|
| Innovation | 20 |
| Technical Implementation | 25 |
| User Experience | 20 |
| Impact | 20 |
| Presentation | 15 |
| **Total** | **100** |

### Eligibility rules

Eligibility is checked on every submit and again when team size changes.

1. Submitted before the deadline.
2. Team size is within the allowed range (1 to 4).
3. Summary is at least 50 characters.
4. Source code link is a valid http(s) URL.
5. If a demo link is given, it's a valid http(s) URL.

Ineligible submissions can't be assigned to judges.

---

## Architecture

```
            Browser (React SPA)
                    │  same origin, JSON over /api, Bearer JWT
                    ▼
┌───────────────── one container, port 8000 ─────────────────┐
│  FastAPI                                                    │
│   ├─ /api/*        routers: auth, participant, judge,       │
│   │                admin, results                           │
│   ├─ services/     eligibility.py, scoring.py               │
│   └─ /*            serves the built React app (index.html)  │
│                                                             │
│  SQLAlchemy ──► SQLite  (/data/dogfood.db, Docker volume)   │
└─────────────────────────────────────────────────────────────┘
```

The design choices:

- **One container, one port, one process.** The Dockerfile has two stages. Node builds the React app, and that stage is thrown away. Python serves both the API and the static files. There's no nginx, no CORS setup and no second service to break.
- **Ten tables**, matching the brief: `User`, `Hackathon`, `Team`, `TeamMember`, `Submission`, `Criterion`, `JudgeAssignment`, `Evaluation`, `Result`, `Certificate`.
- **Rules live in the database** where it matters. For example, "one team per person" is a unique constraint.
- **Results are recalculated from scratch** every time. That makes calculation idempotent and easy to trust.

### Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18, Vite 5, React Router, plain CSS, Archivo font bundled locally |
| Backend | FastAPI, SQLAlchemy 2, Pydantic 2 |
| Database | SQLite |
| Auth | Local JWT (HS256, PyJWT) and bcrypt password hashing |
| Tests | Pytest with FastAPI TestClient |
| Deploy | Docker multi-stage build and Docker Compose |

### Project structure

```
dogfood-hackathon-platform/
├── Dockerfile              # node build stage → python runtime
├── docker-compose.yml
├── e2e/demo_flow.py        # optional browser test of the full flow
├── backend/
│   ├── app/
│   │   ├── main.py         # app, health, security headers, SPA serving
│   │   ├── models.py       # the 10 tables
│   │   ├── security.py     # bcrypt + JWT
│   │   ├── deps.py         # current user, role guards
│   │   ├── seed.py         # demo data + reset CLI
│   │   ├── routers/        # auth, participant, judge, admin, results
│   │   └── services/       # eligibility.py, scoring.py
│   └── tests/test_flow.py  # critical-flow tests
└── frontend/
    └── src/
        ├── pages/          # participant/, judge/, admin/, Login, Verify
        └── components/     # Layout, Leaderboard, ui
```

---

## Tests

With Docker (no local Python needed):

```bash
docker compose run --rm app pytest
```

Or locally:

```bash
cd backend
pip install -r requirements.txt
pytest
```

There are 25 tests, and they run in about 2 seconds. They focus on the critical flow:

| Area | What's checked |
|---|---|
| Login | Success, case-insensitive email, and the same error for a wrong password or an unknown email. Sign-up can't create an admin. |
| Teams | Create, join by invite code, one team per person, can't join a team that's being judged. |
| Submission and eligibility | A team is required. Short summaries and bad links fail. Fixing them passes. |
| Judge assignment | Works for eligible projects only. No duplicates. The submission locks. |
| Evaluation | Scores are stored and normalized. Out-of-range and missing scores are rejected. No double submits. |
| Scoring | The formula, multi-judge averaging and ranking order. |
| Publication | Blocked while evaluations are pending unless confirmed. Results and certificates are hidden until published. Certificate verification works. Unpublishing revokes certificates. |
| Authorization | Unauthenticated requests get 401. Every cross-role call gets 403. A judge can't open another judge's assignment. |

Tests use a throwaway database and never touch the Docker volume.

**Optional browser test.** `e2e/demo_flow.py` clicks through the entire demo flow in Chromium and screenshots each step. It needs a fresh database and Playwright:

```bash
docker compose down -v && docker compose up --build     # terminal 1
pip install playwright && playwright install chromium   # terminal 2
python e2e/demo_flow.py
```

---

## Resetting demo data

Demo data is seeded automatically on first start, and only when the database is empty.

```bash
# Option 1: wipe the volume and start fresh
docker compose down -v
docker compose up --build

# Option 2: reset while the app is running
docker compose exec app python -m app.seed --reset
```

Seed dates are relative to the first start: the event began 48 hours ago and closes in 24 hours. That keeps the deadline in the future, however long after packaging you run it.

---

## Offline and self-hosted

Once the Docker images are built, the app needs **no internet access at runtime**:

- No Firebase, Supabase, Auth0 or any hosted service.
- No external APIs, no CDN, no web fonts from Google. The Archivo font files are bundled into the build.
- The database is a single SQLite file in a Docker volume (`dogfood-data`).
- The JWT signing secret is generated on first start and stored in the volume with permissions `0600`. It's never in the source or the image. You can supply your own with the `JWT_SECRET` environment variable.

This was checked by loading every page for all three roles with all non-localhost network requests blocked. The result was zero external requests.

## Security notes

- **Passwords:** Hashed with bcrypt (cost 12). Login spends the same bcrypt time when an email doesn't exist, so response timing doesn't reveal which accounts are registered.
- **Tokens:** Expire after 8 hours. The signing algorithm is pinned, so a token can't choose its own `alg`.
- **Roles:** Checked against the database on every request, not trusted from the token.
- **Cross-account access:** Judges get a 404, not a 403, for other judges' assignments, so ids can't be probed.
- **Headers:** `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and `no-store` on API responses.
- **Container:** Runs as a non-root user (uid 10001). Static file serving is guarded against path traversal.

---

## Known limitations

- **Single hackathon.** The data model supports several, but the app always uses the most recent one.
- **Auth token in `localStorage`.** Fine for a self-hosted MVP, but a production build should move to httpOnly cookies with CSRF protection.
- **No login rate limiting.** Put the app behind a reverse proxy with rate limits if it's exposed to the internet.
- **Evaluations are final.** Reopening an evaluation is a P1 feature and isn't built. A pending assignment can still be removed and reassigned.
- **Links aren't fetched.** Eligibility checks that a repository link is a valid URL, not that the repository exists. Fetching it would need network access, which breaks the offline rule.
- **No email.** Teammates share invite codes themselves, and certificates are printed or saved as PDF from the browser.
- **SQLite suits one server.** That's plenty for an event of this size.

## Local development (optional)

```bash
# terminal 1: API on :8000 (creates ./data on first run)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# terminal 2: React on :5173, proxying /api to :8000
cd frontend && npm install && npm run dev
```
