# Judging

This document explains exactly how a project goes from "submitted" to "ranked": who judges it, how they score, how the scores become one number, and what happens when scores are missing. All of the scoring code is in one file, `backend/app/services/scoring.py`. The rules below match it line for line.

See also: [ARCHITECTURE.md](ARCHITECTURE.md) · [DATA-MODEL.md](DATA-MODEL.md)

## 1. The pipeline at a glance

```
Submission ─► Eligibility ─► Judge assignment ─► Evaluation(s) ─► Normalization ─► Average ─► Rank ─► Publish ─► Certificates
             (automatic)      (organizer)        (judge, per      (per judge)       (per       (all
                                                  criterion)                          project)   projects)
```

Every step is visible in the UI:

- **Participants** see their eligibility checks immediately after submitting.
- **Judges** see the normalized score update live while they score.
- **Admins** see a draft ranking with the full working before anything is public.
- **After publishing**, teams see their rank, per-criterion scores and anonymous feedback.

## 2. Eligibility, the gate before judging

A project is only judged if it's eligible. The checks run automatically on every save, and again when the team's size changes.

| Rule | Passes when |
|---|---|
| Submitted before the deadline | the save time ≤ `submission_deadline` |
| Team size | `min_team_size` ≤ members ≤ `max_team_size` (1–4 in the demo) |
| Project summary | at least 50 characters, so judges have something to read |
| Source code link | a full `http(s)://` URL |
| Demo link | if given, a full `http(s)://` URL |

**Why this approach:** automated, explainable checks catch rule-breaking submissions *before* a judge wastes time on them. Each failed check says how to fix it ("19 characters. Needs at least 50."), so teams fix problems themselves.

**Limit:** links are checked for format, not fetched. Fetching would need internet access, and the platform must run offline.

## 3. Judge assignment strategy

### How it works

Assignment is **manual and done by the organizer**, on *Admin → Submissions & judges*. The system enforces the rules that keep it fair:

| Rule | Enforced by |
|---|---|
| Only **eligible** submissions can be assigned | API returns 409 otherwise |
| Only accounts with the **judge** role can be assigned | API returns 404 otherwise |
| A judge can't be assigned to the same submission twice | database unique constraint |
| Assigning a judge **locks the submission**: the team can't edit it or add members | `locked` flag, 409 on edit/join |
| A judge sees **only their own** assignments; others return 404 | ownership check on every judge endpoint |
| A **pending** assignment can be removed and given to someone else | `DELETE /api/admin/assignments/{id}` |
| A **completed** evaluation can't be removed | API returns 409 |

The admin UI helps with coverage:

- The overview shows how many eligible submissions have no judge yet.
- The *Needs a judge* filter lists them.
- The *Scores* page shows every assignment, so an organizer can spot a judge with too much or too little work.

### Recommended practice

1. **Give every eligible project at least one judge.** Unjudged projects aren't ranked.
2. **For fairness, prefer a full panel:** assign every judge to every project when the event is small enough (for example 3 judges × 10 projects). Every project is then scored by the same people, so one judge's strictness applies to everyone equally.
3. **When a full panel isn't possible, give each project the same number of judges** (for example 2), and mix strict and generous judges across projects.
4. **Conflicts of interest:** judges and participants are separate accounts with separate roles. A judge account can't create or join a team (403), so a judge can never score their own team. If a judge personally knows a team, don't assign them. If it's already assigned and still pending, remove it.

### Why manual rather than automatic

- **Hackathons are small.** A handful of judges and tens of projects is a five-minute job for a human.
- **Organizers know things the system doesn't:** who knows whom, who understands hardware or ML, who's only around on day two. Auto-assignment would need all of that as input and would still get it wrong.
- **It's predictable and auditable.** Every assignment records who made it (`assigned_by_id`) and when.

An automatic round-robin assigner would be a straightforward extension (see [§9](#9-possible-extensions)). It isn't needed for the MVP.

## 4. Scoring methodology

A judge opens an assignment, reads the project (summary, repository, demo link, tech stack) and scores **every criterion** on the rubric.

| Rule | Detail |
|---|---|
| Scale | Whole numbers from **0 to the criterion's maximum** |
| Completeness | **All** criteria must be scored. The submit button stays disabled, and the API rejects partial scores (422). |
| Validation | Out-of-range scores, unknown criteria or duplicates are rejected (422) |
| Feedback | Optional free text, up to 1000 characters, shown to the team **anonymously** ("Judge 1") |
| Finality | Once submitted, an evaluation can't be edited, and the judge is asked to confirm first |
| Closing | After results are published, scoring is closed (409) |

### Default rubric

This is seeded into the database. Admins can edit it on *Admin → Criteria*.

| Criterion | What judges look for | Range |
|---|---|---|
| Innovation | How new or surprising is the idea? | 0–20 |
| Technical Implementation | Does it work, and is it built well? | 0–25 |
| User Experience | Is it easy and pleasant to use? | 0–20 |
| Impact | Would it matter to real people? | 0–20 |
| Presentation | Is the demo and write-up clear? | 0–15 |
| **Total** | | **0–100** |

**Why weighted maxima instead of a flat 1–10 per criterion:** the maximum *is* the weight. Technical Implementation matters most (25%), and Presentation least (15%). Judges see the weight while scoring instead of applying hidden multipliers afterwards.

**Why whole numbers:** decimals invite false precision ("is this a 17.5 or a 17.25?") and slow judges down without making rankings more accurate.

## 5. Score ranges at each stage

| Value | Range | Precision | Where |
|---|---|---|---|
| Criterion score | 0 – `max_score` (each `max_score` 1–100) | integer | `Evaluation.scores[].score` |
| Raw total | 0 – sum of max scores | integer (stored as float) | `Evaluation.raw_total` |
| Maximum possible | sum of max scores at scoring time (100 by default) | integer | `Evaluation.max_total` |
| Normalized score | **0.00 – 100.00** | 2 decimals | `Evaluation.normalized_score` |
| Final score | **0.00 – 100.00** | 2 decimals | `Result.final_score` |
| Rank | 1 – number of ranked projects | integer, ties share | `Result.rank` |

## 6. Normalization

```
normalized_score = (raw_score / maximum_possible_score) × 100      rounded to 2 decimals
```

It's computed **once per evaluation**, at submission time, and stored.

**Example:** a judge scores 18 + 22 + 17 + 16 + 13 = **86** out of **100**, so 86 ÷ 100 × 100 = **86.00**.

### Why normalize at all?

1. **The rubric can change.** An admin can add, remove or re-weight criteria during the event. An evaluation made against a 100-point rubric and one made against a 110-point rubric can't be compared by raw totals. As percentages they can.
2. **Each evaluation keeps a snapshot** of the criteria as they were when it was scored (name, max and score). Its normalized score is computed against *that* maximum, so editing the rubric later can never silently change a submitted score.
3. **Percentages are easy to explain.** "86 out of 100" needs no footnote.

### What this normalization deliberately does *not* do

It doesn't correct for judge *strictness*. Methods like z-scores rescale each judge by their own mean and spread. We chose not to, for three reasons:

- **Small samples make them unstable.** A judge who scores three projects has a meaningless standard deviation. One outlier would reshuffle the ranking.
- **They're hard to explain.** A team told "your 86 became 71 because your judge is generous" can't check that. The platform's promise is that every score shows its working.
- **Fair assignment solves the same problem more simply.** If every project gets the same judges (the full panel in §3), strictness affects everyone equally, and plain averages are already fair.

## 7. Aggregation and final score

```
final_score = average(normalized_scores of every completed evaluation for the project)
              rounded to 2 decimals
```

**Example with two judges:**

| Judge | Raw | Max | Normalized |
|---|---|---|---|
| Judge A | 84 | 100 | 84.00 |
| Judge B | 70 | 100 | 70.00 |
| **Final** | | | **average(84.00, 70.00) = 77.00** |

**Why the mean:** every judge's opinion counts equally. It's the method people expect, and it works with any number of judges, including one.

We considered the **median**. It resists one extreme judge, but with the usual one to three judges it throws away information. With two judges it's the same as the mean anyway.

### Ranking

- Projects are sorted by `final_score`, highest first.
- **Ties share a rank** (standard competition ranking: 1, 1, 3). Two projects with identical scores are equally good by the rubric, and a tie-break like "submitted earlier" would reward something that wasn't judged.
- Certificates follow the rank:
  - Rank 1: **Winner**
  - Rank 2: **First Runner-up**
  - Rank 3: **Second Runner-up**
  - Everyone else with a submission: **Participant**
- Results are **recalculated from scratch** each time, so the ranking is always a pure function of the stored evaluations.

## 8. Missing and incomplete scores

| Situation | What happens | Why |
|---|---|---|
| A judge tries to submit with a criterion unscored | Rejected (UI and API). There are no partial evaluations. | A missing criterion would silently count as 0 and drag the project down. |
| A project's assignment is still **pending** | Only **completed** evaluations are averaged. The pending one is ignored, not counted as 0. | Treating "not scored yet" as "scored zero" would punish the team for a judge's delay. |
| A project has **no** completed evaluations | Listed as **Not ranked**, with the note "No completed evaluations yet" | There's nothing to rank on. |
| A project is **ineligible** | Listed as **Not ranked**, with the note "Not eligible". Can't be assigned to judges. | Eligibility is the gate. |
| Admin presses **Publish** while evaluations are pending | Blocked with a warning listing each pending evaluation. The admin can wait, or choose **Publish anyway**, which ranks on completed scores only. | The organizer makes the call knowingly, and nothing is published by accident. |
| A pending judge is unavailable | The admin removes the pending assignment and assigns another judge | Keeps judging moving |
| Criteria are edited after some evaluations exist | Old evaluations keep their snapshot and normalized score. New ones use the new rubric. The admin sees a warning. | Nobody's submitted score changes silently. |
| Results need correcting after publishing | **Unpublish**: certificates are withdrawn and changes are allowed again. Then publish again, which recalculates. | Mistakes can be fixed, and the certificates always match the ranking. |

## 9. Transparency

| Who | Sees |
|---|---|
| Judge | Their own scores, raw total and normalized score, live while scoring and afterwards |
| Admin | Every evaluation with judge names (*Scores*), and the draft or published ranking with each judge's `raw / max × 100 = normalized` plus the average (*Results*) |
| Participant (after publishing) | Their rank, their final score with the same working, per-criterion scores and feedback from each judge (as "Judge 1", "Judge 2"), and the full leaderboard |
| Anyone with a certificate code | That the certificate is genuine (`/verify/<code>`) |

Judges are anonymous to participants, so teams can't lobby or blame individual judges.

## 10. Where each rule is tested

`backend/tests/test_flow.py` covers the following. Run it with `docker compose run --rm app pytest`.

| Rule | Test |
|---|---|
| Normalization and averaging formulas | `test_normalize_formula` |
| Multi-judge average and ranking order | `test_multiple_judges_are_averaged_and_ranked` |
| Stored normalized score, no double submit | `test_judge_scores_and_normalized_score_is_stored` |
| Out-of-range and missing scores rejected | `test_evaluation_rejects_out_of_range_and_missing_scores` |
| Only eligible projects assignable, no duplicates, submission locks | `test_ineligible_submission_cannot_be_assigned`, `test_same_judge_cannot_be_assigned_twice`, `test_admin_assigns_judge_and_submission_locks` |
| Publish blocked while pending unless confirmed | `test_publish_blocks_on_pending_unless_confirmed` |
| Full lifecycle ending in rank and certificate | `test_full_participant_flow_ends_with_result_and_certificate` |
| Judges isolated from each other | `test_judge_cannot_open_someone_elses_assignment` |

## 11. Possible extensions

Not built, because the MVP doesn't need them:

- **Automatic assignment:** round-robin over judges, sorted by current load, skipping flagged conflicts.
- **Evaluation reopening:** let an admin send an evaluation back to its judge.
- **Per-judge calibration:** optional z-score normalization for large events where every judge scores many projects.
