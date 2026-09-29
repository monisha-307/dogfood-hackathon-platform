"""Record the 5-minute demo video: one complete event lifecycle, captioned.

Needs a FRESH database and the app running:
    docker compose down -v && docker compose up --build -d
Then:
    pip install playwright && playwright install chromium
    python e2e/record_demo.py
Output: e2e/video/dogfood-demo.webm (and .mp4 if ffmpeg is on PATH).
Runs for about 4.5 minutes in real time (set DEMO_PACE to change the speed).
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.getenv("BASE_URL", "http://localhost:8000")
OUT = Path(__file__).parent / "video"
OUT.mkdir(exist_ok=True)
SIZE = {"width": 1280, "height": 800}
TOTAL_STEPS = 10
# Multiplies every pause. 1.7 gives about 4.5 minutes, with time to read each caption.
PACE = float(os.getenv("DEMO_PACE", "1.7"))

CAPTION_JS = """([step, text]) => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div');
    el.id = 'demo-caption';
    el.style.cssText = `position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:99999;
      max-width:900px;width:calc(100% - 80px);background:rgba(0,0,0,.9);color:#fff;border-radius:10px;
      padding:14px 20px;font:500 19px/1.4 'Archivo Variable',system-ui,sans-serif;
      box-shadow:0 0 0 2px #FFD60A;pointer-events:none`;
    document.body.appendChild(el);
  }
  el.innerHTML = (step ? `<div style="color:#FFD60A;font-size:14px;font-weight:700;margin-bottom:2px">${step}</div>` : '') + text;
}"""

CARD_JS = """([title, sub]) => {
  const el = document.createElement('div');
  el.id = 'demo-card';
  el.style.cssText = `position:fixed;inset:0;z-index:100000;background:#000;color:#fff;display:flex;
    flex-direction:column;justify-content:center;padding:0 90px;font-family:'Archivo Variable',system-ui,sans-serif`;
  el.innerHTML = `<div style="width:90px;height:10px;background:#FFD60A;margin-bottom:26px"></div>
    <div style="font-size:54px;font-weight:850;font-stretch:125%;line-height:1.05">${title}</div>
    <div style="font-size:23px;color:#d0d3da;margin-top:18px;max-width:900px;line-height:1.45">${sub}</div>`;
  document.body.appendChild(el);
}"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=SIZE, record_video_dir=str(OUT), record_video_size=SIZE)
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())

        def wait(sec):
            page.wait_for_timeout(int(sec * PACE * 1000))

        def caption(text, step=None, hold=4.5):
            label = f"Step {step} of {TOTAL_STEPS}" if step else ""
            page.evaluate(CAPTION_JS, [label, text])
            wait(hold)

        def card(title, sub, hold=6):
            page.evaluate(CARD_JS, [title, sub])
            wait(hold)
            page.evaluate("document.getElementById('demo-card')?.remove()")

        def typ(locator, text, delay=35):
            locator.click()
            locator.fill("")
            locator.press_sequentially(text, delay=delay)

        def scroll(px, steps=6):
            for _ in range(steps):
                page.mouse.wheel(0, px / steps)
                wait(0.25)

        def sign_in(role):
            page.get_by_role("button", name=re.compile(f"^{role}")).click()

        def sign_out():
            page.get_by_role("button", name="Sign out").click()
            expect(page.get_by_role("heading", name="Sign in")).to_be_visible()

        # ------------------------------------------------------------------ intro
        page.goto(BASE + "/login")
        expect(page.get_by_role("heading", name="Sign in")).to_be_visible()
        card(
            "Dogfood Hackathon Platform",
            "One complete event lifecycle in five minutes: team → submission → eligibility → "
            "judge assignment → scoring → normalization → published results → certificate.<br><br>"
            "Self-hosted with <b>docker compose up</b>. No cloud services. Seeded demo data.",
            hold=7,
        )
        caption("The sign-in page shows the event and a live countdown. "
                "Each role has a one-click demo account.", step=1, hold=6)

        # ------------------------------------------------------------------ participant
        sign_in("Participant")
        expect(page.get_by_role("heading", name="Hi, Alex")).to_be_visible()
        caption("Participant view. The progress track shows the six steps of the event "
                "and the one thing to do next. Alex has no team yet.", step=2, hold=6)
        scroll(420)
        caption("Participants can see exactly how they'll be judged: five weighted criteria, 100 points.", hold=4.5)
        scroll(-420)

        page.get_by_role("link", name="Set up your team").click()
        caption("Create a team, or join one with a teammate's invite code.", step=3, hold=3)
        typ(page.get_by_label("Team name"), "Late Night Labs")
        page.get_by_role("button", name="Create team").click()
        expect(page.get_by_role("heading", name="Late Night Labs")).to_be_visible()
        caption("Team created. Alex is the lead, with a code to invite teammates.", hold=4.5)

        page.get_by_role("link", name="Submit project").first.click()
        caption("Submit the project. First, with a summary that's too short…", step=4, hold=2.5)
        typ(page.get_by_label("Project title"), "Standup Bot")
        typ(page.get_by_label("Summary"), "A bot for standups.")
        typ(page.get_by_label("Source code link"), "https://github.com/example/standup-bot", delay=20)
        typ(page.get_by_label("Tech stack"), "Python, Slack API")
        page.get_by_role("button", name="Submit project").click()
        expect(page.get_by_text("Saved, but it isn’t eligible yet")).to_be_visible()
        caption("Eligibility runs automatically. The summary check fails and says exactly how to fix it.", hold=6)

        typ(
            page.get_by_label("Summary"),
            "Collects async standups in team chat and posts one tidy digest every morning, "
            "so nobody sits through a 20-minute call to say 'no blockers'.",
            delay=18,
        )
        page.get_by_role("button", name="Update submission").click()
        expect(page.get_by_text("Submitted. Your project passed every eligibility check.")).to_be_visible()
        caption("Fixed and resubmitted. Every check passes, so the project can now be judged.", hold=5)
        sign_out()

        # ------------------------------------------------------------------ admin: assign
        sign_in("Organizer")
        expect(page.get_by_role("heading", name="Dogfood 72-Hour Hackathon")).to_be_visible()
        caption("Organizer view. Counts, judging progress and what to do next.", step=5, hold=5)
        page.get_by_role("link", name="Submissions & judges").click()
        card_loc = page.locator("section.sub-card", has=page.get_by_role("heading", name="Standup Bot"))
        card_loc.scroll_into_view_if_needed()
        caption("Each submission shows its eligibility checks and judges. "
                "Only eligible projects can be assigned.", hold=5)
        card_loc.get_by_role("button", name="Assign judge").click()
        expect(page.get_by_text("Assigned to Standup Bot.")).to_be_visible()
        caption("Judge assigned. The submission is now locked, so the judge scores exactly what everyone else sees.", hold=5.5)
        page.get_by_role("link", name="Criteria").click()
        caption("The rubric lives in the database. Organizers can edit it; submitted scores keep a snapshot.", hold=5)
        sign_out()

        # ------------------------------------------------------------------ judge
        sign_in("Judge")
        expect(page.get_by_role("heading", name="Assigned projects")).to_be_visible()
        caption("Judge view. Only this judge's assignments, with a completion bar.", step=6, hold=5)
        page.locator("tr", has=page.get_by_text("Standup Bot")).get_by_role("link", name="Score project").click()
        caption("Score every criterion from 0 to its maximum.", hold=3)
        for name, value in [("Innovation", "18"), ("Technical Implementation", "22"),
                            ("User Experience", "17"), ("Impact", "16"), ("Presentation", "13")]:
            box = page.get_by_role("spinbutton", name=name)
            box.click()
            box.fill(value)
            wait(0.9)
        expect(page.locator(".live-total")).to_contain_text("86.00")
        page.locator(".live-total").scroll_into_view_if_needed()
        caption("Normalization happens live: raw ÷ max × 100 = 86 ÷ 100 × 100 = 86.00.", step=7, hold=6)
        typ(page.get_by_label("Feedback for the team"), "Genuinely useful. Add a snooze option for weekends.", delay=22)
        page.get_by_role("button", name="Submit evaluation").click()
        expect(page.get_by_text("Evaluation submitted.")).to_be_visible()
        caption("Submitted after a confirmation. Evaluations are final, and the team sees the feedback anonymously.", hold=5)
        sign_out()

        # ------------------------------------------------------------------ admin: results
        sign_in("Organizer")
        page.get_by_role("link", name="Results").click()
        page.get_by_role("button", name="Calculate results").click()
        expect(page.get_by_text("Results recalculated.")).to_be_visible()
        caption("A private draft ranking. Final score = average of each judge's normalized score, "
                "with the working shown.", step=8, hold=5)
        page.locator("table.leaderboard").scroll_into_view_if_needed()
        wait(4)
        page.evaluate("window.scrollTo(0, 0)")
        page.get_by_role("button", name="Publish results").click()
        expect(page.get_by_role("button", name="Publish anyway")).to_be_visible()
        caption("One seeded evaluation is still pending, so publishing is blocked until the organizer decides. "
                "Pending scores are ignored, never counted as zero.", hold=7)
        page.get_by_role("button", name="Publish anyway").click()
        expect(page.get_by_text("Published. Participants can now see")).to_be_visible()
        caption("Published. Certificates are issued to every member of every team that submitted.", hold=5)
        page.get_by_role("button", name="Download results (CSV)").scroll_into_view_if_needed()
        caption("Results export as CSV, or the whole event as JSON. Everything runs offline in one container.", hold=5)
        page.get_by_role("link", name="Scores").click()
        caption("Every judge's per-criterion scores, raw total, normalized score and feedback.", hold=5)
        sign_out()

        # ------------------------------------------------------------------ participant: result
        sign_in("Participant")
        expect(page.get_by_role("heading", name="Hi, Alex")).to_be_visible()
        caption("Back as the participant: every step on the track is complete.", step=9, hold=4.5)
        page.get_by_role("link", name="Results", exact=True).click()
        expect(page.locator(".result-big").first).to_have_text("1")
        caption("Rank 1 with 86.00, and exactly how that number was calculated.", hold=5)
        scroll(700, steps=8)
        caption("Per-criterion scores, anonymous judge feedback and the full leaderboard.", hold=5)
        page.evaluate("window.scrollTo(0, 0)")
        page.get_by_role("link", name="View certificate").click()
        expect(page.locator(".cert-name")).to_have_text("Alex Morgan")
        caption("A printable certificate. 'Print or save as PDF' uses the browser.", step=10, hold=5)
        code = page.locator(".cert-verify").inner_text().rsplit("/", 1)[-1].strip()
        page.goto(f"{BASE}/verify/{code}")
        expect(page.get_by_role("heading", name="Verified")).to_be_visible()
        caption("Anyone can check a certificate at its public verification link, without signing in.", hold=5.5)

        card(
            "One full lifecycle, done",
            "Team → submission → eligibility → judge assignment → scoring → normalization → "
            "results → certificate.<br><br>FastAPI · React · SQLite · Docker Compose · Apache-2.0<br>"
            "32 automated tests · runs fully offline",
            hold=7,
        )

        video_path = page.video.path()
        ctx.close()
        browser.close()

    final = OUT / "dogfood-demo.webm"
    shutil.move(video_path, final)
    print("Saved", final)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        mp4 = OUT / "dogfood-demo.mp4"
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", str(final), "-c:v", "libx264", "-crf", "20",
             "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)],
            check=True,
        )
        print("Saved", mp4)


if __name__ == "__main__":
    main()
