# Dogfood Hackathon Platform

<<<<<<< HEAD
A self-hosted judging platform for a 72-hour hackathon. It covers the whole journey, from a participant forming a team to printing a certificate, in one Docker container with no cloud services.
=======
A self-hosted judging portal for a 72-hour hackathon. It runs one complete event lifecycle, from a participant forming a team to a verifiable certificate, in **one Docker container**, with **no cloud services** and **no internet needed at runtime**.
>>>>>>> 97e6bd8 (Initial hackathon submission)

```bash
docker compose up --build
```

<<<<<<< HEAD
Open **http://localhost:8000** and click one of the demo accounts on the sign-in page.
=======
Then open **http://localhost:8000** and click a demo account.

**License:** [Apache-2.0](LICENSE)

| Document | What's in it |
|---|---|
| [README.md](README.md) | Setup, demo accounts, the flow for each role, testing, shutdown (this file) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, request and data flow, deployment, security, technical decisions |
| [DATA-MODEL.md](DATA-MODEL.md) | All 10 tables, fields, relationships, seed data, import/export paths |
| [JUDGING.md](JUDGING.md) | Judge assignment, scoring, normalization, aggregation, missing scores |
| [acceptance-report.txt](acceptance-report.txt) | Acceptance checklist and what was actually verified |
| [LICENSE](LICENSE) / [NOTICE](NOTICE) | Apache License 2.0, third-party notices |

**Demo video:** *(add the link to the 5-minute walkthrough here after uploading it)*
>>>>>>> 97e6bd8 (Initial hackathon submission)

---

## Problem

<<<<<<< HEAD
Small hackathons usually judge with a mix of Google Forms, spreadsheets and group chats. Things get lost along the way:

- Submissions arrive that break the rules, and nobody notices until judging.
- Judges score on different scales, so their totals can't be compared fairly.
- Organizers do the ranking by hand in a spreadsheet, and teams never see how their score was worked out.
=======
Small hackathons usually judge with a mix of forms, spreadsheets and group chats, and things slip:

- Submissions that break the rules aren't noticed until judging.
- Judges score on different scales, so their totals can't be compared.
- Organizers rank by hand, and teams never see how their score was worked out.
>>>>>>> 97e6bd8 (Initial hackathon submission)
- Certificates are made one by one in a design tool.

## Solution

One small app with three roles that hand work to each other:

| Role | What they do |
|---|---|
<<<<<<< HEAD
| **Participant** | Creates or joins a team, submits the project, sees eligibility right away, and later sees their rank, judge feedback and certificate. |
| **Judge** | Sees only their assigned projects, scores each criterion, adds feedback, and watches the normalized score update live. |
| **Organizer (admin)** | Checks eligibility, assigns judges, configures criteria, previews the ranking, and publishes results. Publishing also issues certificates. |

Every score shows its working: a team can see exactly how their final number was calculated.

---

## Quick start

**You only need Docker Desktop (or Docker Engine with the Compose plugin).** You don't need Node, Python, a database or a cloud account.

```bash
unzip dogfood-hackathon-platform.zip
=======
| **Participant** | Creates or joins a team, submits the project, sees eligibility straight away, and later sees their rank, judge feedback and certificate. |
| **Judge** | Sees only their assigned projects, scores each criterion, adds feedback, and watches the normalized score update live. |
| **Organizer (admin)** | Checks eligibility, assigns judges, configures criteria, previews the ranking, publishes results (which issues certificates) and exports data. |

Every score shows its working. A team can see exactly how their final number was calculated.

---

## 1. Run it

### What you need

You need **Docker** with the Compose plugin (Docker Desktop on Windows/macOS, or Docker Engine on Linux). You don't need Node, Python, a database or a cloud account.

### Start

```bash
unzip dogfood-hackathon-platform.zip        # or: git clone <repository-url>
>>>>>>> 97e6bd8 (Initial hackathon submission)
cd dogfood-hackathon-platform
docker compose up --build
```

<<<<<<< HEAD
| | |
|---|---|
| App | http://localhost:8000 |
| Health check | http://localhost:8000/api/health returns `{"status":"ok"}` |
| API docs (Swagger) | http://localhost:8000/api/docs |

The first build takes a few minutes while it downloads the base images and packages. After that it starts in seconds. Stop it with `Ctrl+C` or `docker compose down`.

### Demo credentials
=======
- The first build downloads the base images and packages, which takes a few minutes. Later starts take seconds.
- Plain `docker compose up` works too. It builds automatically if the image doesn't exist yet. Use `--build` after changing code.
- To run in the background, add `-d`.

It's ready when the logs show `Uvicorn running on http://0.0.0.0:8000`, or when `docker compose ps` shows `(healthy)`.

| | |
|---|---|
| App | **http://localhost:8000** |
| Health check | http://localhost:8000/api/health returns `{"status":"ok"}`. It also queries the database, so "ok" means the API **and** the database are up. |
| API docs (Swagger) | http://localhost:8000/api/docs |

On first start, the portal **seeds itself** with a demo event: 1 hackathon, 5 criteria, 7 accounts, 2 teams, 2 submissions, 1 completed evaluation, 1 pending evaluation and a draft ranking. It seeds only when the database is empty, so your data is never overwritten.

If port 8000 is taken, change the left side of `"8000:8000"` in `docker-compose.yml`, for example to `"8080:8000"`, and open that port instead.

### Demo accounts
>>>>>>> 97e6bd8 (Initial hackathon submission)

The sign-in page has a one-click button for each role, so you don't need to type these.

| Role | Email | Password | Starting state |
|---|---|---|---|
| Organizer (admin) | `admin@dogfood.dev` | `Admin@123` | Two submissions: one judged, one pending |
| Judge | `judge@dogfood.dev` | `Judge@123` | One evaluation done, one pending |
<<<<<<< HEAD
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
=======
| Participant | `participant@dogfood.dev` | `Participant@123` | **No team yet**, so you can run the whole flow |
| Seeded team members | `priya@dogfood.dev`, `arjun@dogfood.dev`, `meera@dogfood.dev`, `kabir@dogfood.dev` | `Demo@2026` | Already on *Byte Bandits* and *Null Pointers* |

You can also create new participant accounts with **Create an account** on the sign-in page. All names, teams and projects are made up.

---

## 2. Participant flow

Sign in as **Participant** (`participant@dogfood.dev` / `Participant@123`).

1. **Overview.** A six-step progress track (Team, Submit, Eligibility, Judging, Results, Certificate) shows where you are, with one button for the next step. It also lists the judging criteria and their weights.
2. **Create a team.** Click **Set up your team**, enter a name such as `Late Night Labs`, and click **Create team**. You become the team lead and get a six-character invite code.
   - *To join instead:* another participant enters that code under **Join a team**. Try it with a new account from **Create an account**.
3. **Submit.** Go to **Submission**. Fill in the project title, summary, source code link (for example `https://github.com/example/standup-bot`) and, optionally, the demo link and tech stack. Click **Submit project**.
4. **Eligibility.** The checks appear immediately.
   - To see a failure, first enter a summary under 50 characters. The *Project summary* check fails and says why.
   - Lengthen the summary and click **Update submission**. Every check turns green.
5. **Wait for judging.** The overview shows *Waiting for a judge*, then *Being judged*. Once a judge is assigned, the submission is locked.
6. **Results.** After the organizer publishes, **Results** shows your rank, final score, the calculation, per-criterion scores, anonymous judge feedback and the full leaderboard.
7. **Certificate.** Click **View certificate**, then **Print or save as PDF**. The verification link at the bottom opens a public page confirming it's genuine; no sign-in needed.

## 3. Judge flow

Sign in as **Judge** (`judge@dogfood.dev` / `Judge@123`).

1. **Assigned projects.** This lists only your assignments, with a progress bar (for example *1 of 2 scored*) and a status for each.
2. Click **Score project** on a pending one. The left side shows the submission: summary, links, tech stack and eligibility.
3. **Score every criterion** using the number box or the slider. Each has a range from 0 to its maximum:
   - Innovation 0–20
   - Technical Implementation 0–25
   - User Experience 0–20
   - Impact 0–20
   - Presentation 0–15
4. Watch the black panel. It shows the raw total and the normalized score live (`raw ÷ max × 100`).
5. Optionally add feedback. The team sees it anonymously, as "Judge 1".
6. Click **Submit evaluation** and confirm. Scores are final. The project moves to *Completed*, and **View scores** shows what you submitted.

## 4. Admin flow

Sign in as **Organizer** (`admin@dogfood.dev` / `Admin@123`).

1. **Overview.** Counts of participants, teams, submissions and evaluations, plus a *What to do next* list and judging progress.
2. **Submissions & judges.**
   - Each submission shows its eligibility checks and its judges.
   - Filter with *Needs a judge*, *Being judged*, *Judged* or *Ineligible*.
   - Pick a judge and click **Assign judge**.
   - To reassign, click **Remove** on a *pending* judge.
3. **Criteria.** Edit names, descriptions and maximum points, or add and delete criteria. The page warns you if evaluations already exist (see [JUDGING.md §8](JUDGING.md#8-missing-and-incomplete-scores)).
4. **Scores.** Every assignment, with each judge's per-criterion scores, raw total, normalized score and feedback.
5. **Results.**
   1. Click **Calculate results** for a private draft ranking. It shows the working for every score.
   2. Click **Publish results**. If any evaluations are still pending, you'll get a warning listing them. Choose **Wait for judges** or **Publish anyway**; the second ranks on completed scores only.
   3. Publishing makes results visible to participants and issues certificates.
   4. **Unpublish** withdraws them so you can make changes.
   5. **Export data:** **Download results (CSV)** or **Download full export (JSON)**.
6. **Teams** and **Participants.** Read-only lists with invite codes, members and submission status. Participants has a search box.

## 5. One complete event lifecycle (the 5-minute demo)

This is the order that shows the whole lifecycle once. Timings are approximate.

| Time | Who | Do this | You should see |
|---|---|---|---|
| 0:00 | — | Open http://localhost:8000 | Sign-in page with a countdown and the three demo buttons |
| 0:20 | Participant | Click **Participant**, then **Set up your team**, name it `Late Night Labs`, **Create team** | Team page with an invite code |
| 0:50 | Participant | **Submission**: title `Standup Bot`, summary `A bot for standups.`, repo link, **Submit project** | Red *Project summary* check: "19 characters. Needs at least 50." |
| 1:20 | Participant | Lengthen the summary, **Update submission** | "Submitted. Your project passed every eligibility check." |
| 1:40 | Admin | Sign out, click **Organizer**, open **Submissions & judges**, click **Assign judge** on *Standup Bot* | "Assigned to Standup Bot." The project is now *Being judged*. |
| 2:20 | Judge | Sign out, click **Judge**, **Score project** on *Standup Bot*, enter 18 / 22 / 17 / 16 / 13, add feedback | The live panel shows 86 / 100 → **86.00** |
| 3:00 | Judge | **Submit evaluation**, confirm | "Evaluation submitted." |
| 3:20 | Admin | Sign in as **Organizer**, open **Results**, **Calculate results** | Draft ranking with the working |
| 3:40 | Admin | **Publish results**, then **Publish anyway** (the seeded *FieldNote* evaluation is still pending) | "Published." |
| 4:10 | Participant | Sign in as **Participant**, open **Results** | Rank **1**, **86.00**, per-criterion scores, feedback, leaderboard |
| 4:35 | Participant | **View certificate**, then open the verification link | "Winner" certificate, then the public *Verified* page |

`e2e/demo_flow.py` performs exactly these steps automatically (see [Testing](#6-testing)). To run the demo again, [reset the demo data](#8-reset-the-demo-data).

---

## 6. Testing

### Backend tests (the main suite)

This needs no local Python:
>>>>>>> 97e6bd8 (Initial hackathon submission)

```bash
docker compose run --rm app pytest
```

<<<<<<< HEAD
Or locally:
=======
Or locally, with Python 3.12:
>>>>>>> 97e6bd8 (Initial hackathon submission)

```bash
cd backend
pip install -r requirements.txt
pytest
```

<<<<<<< HEAD
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
=======
There are **32 tests**, and they run in about 2 seconds. They use a throwaway database and never touch your data volume.

| Area | What's checked |
|---|---|
| Login | Success; case-insensitive email; the same error for a wrong password or an unknown email; sign-up can't create an admin |
| Teams | Create, join by invite code, one team per person, can't join a team that's being judged |
| Submission and eligibility | A team is required; short summaries and bad links fail; fixing them passes |
| Judge assignment | Eligible projects only, no duplicates, the submission locks |
| Evaluation | Scores stored and normalized; out-of-range and missing scores rejected; no double submits |
| Scoring | The formula, multi-judge averaging, ranking order |
| Publication | Blocked while pending unless confirmed; hidden until published; certificate verification; unpublish revokes |
| Full lifecycle | Participant, team, submission, eligibility, assignment, judging, normalization, publish, result, certificate, in one test |
| Authorization | 401 without a token, 403 across roles, a judge can't open another judge's assignment |
| Health and exports | `/api/health` fails with 503 if the database is down; CSV/JSON exports are correct, admin-only, free of password hashes and safe from spreadsheet formula injection |

### Browser test (optional)

`e2e/demo_flow.py` clicks through the whole lifecycle in Chromium, checks each step, saves screenshots to `e2e/screenshots/`, and fails on any browser console error. It needs a **fresh** database:

```bash
docker compose down -v && docker compose up --build -d
pip install playwright && playwright install chromium
python e2e/demo_flow.py
```

`e2e/record_demo.py` runs the same lifecycle at a watchable pace with on-screen captions, and records it to `e2e/video/`. It's useful for making the demo video.

---

## 7. Shut down

| Goal | Command |
|---|---|
| Stop (when running in the foreground) | `Ctrl+C` |
| Stop and remove the container, **keep the data** | `docker compose down` |
| Stop and **delete all data** (the next start reseeds) | `docker compose down -v` |
| Also remove the built image | `docker compose down -v --rmi local` |

## 8. Reset the demo data
>>>>>>> 97e6bd8 (Initial hackathon submission)

```bash
# Option 1: wipe the volume and start fresh
docker compose down -v
docker compose up --build

<<<<<<< HEAD
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
=======
# Option 2: reset while it's running
docker compose exec app python -m app.seed --reset
```

Seed dates are relative to the first start: the event began 48 hours earlier and closes 24 hours later. So the deadline is always in the future on a fresh start.

## 9. Export and backup

- **Results as CSV** and a **full JSON export** are on *Admin → Results → Export data*.
- **Database backup:** `docker compose cp app:/data/dogfood.db ./backup.db`

Details, including restore, are in [DATA-MODEL.md §7](DATA-MODEL.md#7-import-and-export-paths).

---

## Scoring in one paragraph

Each judge scores every criterion with a whole number from 0 to that criterion's maximum. Their total is normalized to 100: `normalized = raw ÷ max × 100`. A project's final score is the **average** of its judges' normalized scores. Projects are ranked by final score, and equal scores share a rank. Pending evaluations are ignored rather than counted as zero, and publishing warns you about them first.

The full reasoning and the edge cases are in [JUDGING.md](JUDGING.md).

## Architecture in one paragraph

A React single-page app talks JSON to a FastAPI backend on the same origin. FastAPI also serves the built frontend, so there's one container, one process and one port. SQLAlchemy stores everything in a single SQLite file on a Docker volume. Eligibility and scoring rules live in two small service modules, and permissions are enforced on the server for every request.

Full detail is in [ARCHITECTURE.md](ARCHITECTURE.md).

| Layer | Choice |
|---|---|
| Frontend | React 18, Vite 5, React Router, plain CSS, Archivo font bundled locally |
| Backend | FastAPI, SQLAlchemy 2, Pydantic 2 |
| Database | SQLite |
| Auth | Local JWT (HS256) with bcrypt password hashing |
| Tests | Pytest with FastAPI TestClient; optional Playwright browser test |
| Deploy | Docker multi-stage build and Docker Compose |

```
dogfood-hackathon-platform/
├── Dockerfile  docker-compose.yml  LICENSE  NOTICE
├── README.md  ARCHITECTURE.md  DATA-MODEL.md  JUDGING.md  acceptance-report.txt
├── backend/
│   ├── app/          main.py, models.py, security.py, deps.py, seed.py,
│   │                 routers/ (auth, participant, judge, admin, export, results),
│   │                 services/ (eligibility.py, scoring.py)
│   └── tests/        test_flow.py, test_export_health.py
├── frontend/src/     pages/ (participant, judge, admin), components/, api.js
└── e2e/              demo_flow.py, record_demo.py
```

## Offline and self-hosted

Once the Docker image is built, the app needs **no internet access**:

- No Firebase, Supabase, Auth0 or any hosted service. No external APIs.
- No CDN and no Google Fonts. The Archivo font files are bundled into the build.
- The database is a single SQLite file in the Docker volume `dogfood-data`.
- The JWT signing secret is generated on first start and stored in the volume with permissions `0600`. It's never in the source or the image. You can supply your own with the `JWT_SECRET` environment variable.

This was checked by loading every page for all three roles with every non-localhost network request blocked. The result was zero external requests.

## Security notes

- **Passwords:** bcrypt (cost 12). Login spends the same time on unknown emails, so timing doesn't reveal which accounts exist.
- **Tokens:** expire after 8 hours. The algorithm is pinned, so a token can't choose its own `alg`.
- **Roles:** checked against the database on every request.
- **Cross-account access:** judges get a 404, not a 403, for other judges' assignments.
- **Exports:** admin-only. Passwords are never included, and CSV cells are protected against formula injection.
- **Headers:** `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and `no-store` on the API.
- **Container:** runs as a non-root user (uid 10001). Static file serving is guarded against path traversal.

## Known limitations

- **Single active hackathon.** The data model scopes everything by event, but the app always uses the most recent one.
- **Auth token in `localStorage`.** Fine for a self-hosted MVP; production should use httpOnly cookies with CSRF protection.
- **No login rate limiting.** Put the app behind a reverse proxy with rate limits if it's exposed to the internet.
- **Evaluations are final.** Reopening isn't built; a *pending* assignment can be removed and reassigned.
- **Links aren't fetched.** Eligibility checks URL format only, because fetching would need network access.
- **No email.** Invite codes are shared by hand, and certificates are printed or saved as PDF.
- **No bulk import.** Participants self-register. Export is supported (CSV/JSON).
- **No schema migrations.** After model changes, run `docker compose down -v`.
>>>>>>> 97e6bd8 (Initial hackathon submission)

## Local development (optional)

```bash
# terminal 1: API on :8000 (creates ./data on first run)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# terminal 2: React on :5173, proxying /api to :8000
cd frontend && npm install && npm run dev
```
<<<<<<< HEAD
=======

## License

Licensed under the [Apache License, Version 2.0](LICENSE). See [NOTICE](NOTICE) for third-party attributions.
>>>>>>> 97e6bd8 (Initial hackathon submission)
