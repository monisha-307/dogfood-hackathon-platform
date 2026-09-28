"""Optional end-to-end check: drives the whole demo flow through the real UI.

Needs a FRESH database (demo data only) and the app running:
    docker compose down -v && docker compose up --build
Then, in another terminal:
    pip install playwright && playwright install chromium
    python e2e/demo_flow.py
Screenshots land in e2e/screenshots/.
"""
import os
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.getenv("BASE_URL", "http://localhost:8000")
OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)
errors = []


def shot(page, name):
    page.wait_for_timeout(250)
    page.screenshot(path=f"{OUT}/{name}.png", full_page=True)
    print("  shot:", name)


def sign_out(page):
    page.get_by_role("button", name="Sign out").click()
    expect(page.get_by_role("heading", name="Sign in")).to_be_visible()


def demo_login(page, role):
    page.get_by_role("button", name=re.compile(f"^{role}")).click()


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1360, "height": 900})
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("dialog", lambda d: d.accept())

    print("1. login page")
    page.goto(BASE)
    expect(page.get_by_role("heading", name="Sign in")).to_be_visible()
    expect(page.get_by_text("Submissions close in")).to_be_visible()
    shot(page, "01-login")

    print("2. participant: overview, create team")
    demo_login(page, "Participant")
    expect(page.get_by_role("heading", name="Hi, Alex")).to_be_visible()
    shot(page, "02-participant-overview")
    page.get_by_role("link", name="Set up your team").click()
    page.get_by_label("Team name").fill("Late Night Labs")
    page.get_by_role("button", name="Create team").click()
    expect(page.get_by_role("heading", name="Late Night Labs")).to_be_visible()
    shot(page, "03-team")

    print("3. submission: ineligible first, then fixed")
    page.get_by_role("link", name="Submit project").first.click()
    page.get_by_label("Project title").fill("Standup Bot")
    page.get_by_label("Summary").fill("A bot for standups.")
    page.get_by_label("Source code link").fill("https://github.com/example/standup-bot")
    page.get_by_label("Tech stack").fill("Python, Slack API")
    page.get_by_role("button", name="Submit project").click()
    expect(page.get_by_text("Saved, but it isn’t eligible yet")).to_be_visible()
    shot(page, "04-submission-ineligible")
    page.get_by_label("Summary").fill(
        "Collects async standups in team chat and posts one tidy digest every morning, "
        "so nobody has to sit through a 20-minute call to say 'no blockers'."
    )
    page.get_by_role("button", name="Update submission").click()
    expect(page.get_by_text("Submitted. Your project passed every eligibility check.")).to_be_visible()
    shot(page, "05-submission-eligible")
    sign_out(page)

    print("4. admin: overview, assign judge")
    demo_login(page, "Organizer")
    expect(page.get_by_role("heading", name="Dogfood 72-Hour Hackathon")).to_be_visible()
    shot(page, "06-admin-overview")
    page.get_by_role("link", name="Submissions & judges").click()
    card = page.locator("section.sub-card", has=page.get_by_role("heading", name="Standup Bot"))
    card.get_by_role("button", name="Assign judge").click()
    expect(page.get_by_text("Assigned to Standup Bot.")).to_be_visible()
    shot(page, "07-admin-submissions")
    page.get_by_role("link", name="Criteria").click()
    expect(page.get_by_text("100 points in total")).to_be_visible()
    shot(page, "08-admin-criteria")
    sign_out(page)

    print("5. judge: score the new project")
    demo_login(page, "Judge")
    expect(page.get_by_role("heading", name="Assigned projects")).to_be_visible()
    shot(page, "09-judge-list")
    row = page.locator("tr", has=page.get_by_text("Standup Bot"))
    row.get_by_role("link", name="Score project").click()
    for name, value in [("Innovation", "18"), ("Technical Implementation", "22"), ("User Experience", "17"),
                        ("Impact", "16"), ("Presentation", "13")]:
        page.get_by_role("spinbutton", name=name).fill(value)
    page.get_by_label("Feedback for the team").fill("Genuinely useful. Add a snooze option for weekends.")
    expect(page.locator(".live-total")).to_contain_text("86.00")
    shot(page, "10-judge-scoring")
    page.get_by_role("button", name="Submit evaluation").click()
    expect(page.get_by_text("Evaluation submitted.")).to_be_visible()
    shot(page, "11-judge-submitted")
    sign_out(page)

    print("6. admin: calculate, publish (with pending confirm)")
    demo_login(page, "Organizer")
    page.get_by_role("link", name="Results").click()
    page.get_by_role("button", name="Calculate results").click()
    expect(page.get_by_text("Results recalculated.")).to_be_visible()
    page.get_by_role("button", name="Publish results").click()
    expect(page.get_by_role("button", name="Publish anyway")).to_be_visible()
    shot(page, "12-admin-publish-warning")
    page.get_by_role("button", name="Publish anyway").click()
    expect(page.get_by_text("Published. Participants can now see")).to_be_visible()
    shot(page, "13-admin-published")
    page.get_by_role("link", name="Scores").click()
    shot(page, "14-admin-scores")
    sign_out(page)

    print("7. participant: result + certificate")
    demo_login(page, "Participant")
    page.get_by_role("link", name="Results", exact=True).click()
    expect(page.locator(".result-big").first).to_have_text("1")
    shot(page, "15-participant-results")
    page.get_by_role("link", name="View certificate").click()
    expect(page.locator(".cert-name")).to_have_text("Alex Morgan")
    shot(page, "16-certificate")
    code = page.locator(".cert-verify").inner_text().rsplit("/", 1)[-1].strip()
    page.emulate_media(media="print")
    shot(page, "17-certificate-print")
    page.emulate_media(media="screen")
    page.get_by_role("link", name="Overview").click()
    shot(page, "18-participant-overview-done")

    print("8. public verify")
    page.goto(f"{BASE}/verify/{code}")
    expect(page.get_by_role("heading", name="Verified")).to_be_visible()
    shot(page, "19-verify")

    print("9. mobile")
    m = browser.new_page(viewport={"width": 390, "height": 844})
    m.on("pageerror", lambda e: errors.append(f"mobile pageerror: {e}"))
    m.goto(BASE + "/login")
    m.get_by_role("button", name=re.compile("^Organizer")).click()
    expect(m.get_by_role("heading", name="Dogfood 72-Hour Hackathon")).to_be_visible()
    m.wait_for_url("**/admin")
    m.goto(BASE + "/admin/results")
    expect(m.get_by_role("heading", name="Results", exact=True)).to_be_visible(timeout=10000)
    m.wait_for_timeout(300)
    m.screenshot(path=f"{OUT}/20-mobile-results.png", full_page=True)

    browser.close()

print("\nFLOW COMPLETE")
if errors:
    print("Browser errors/warnings:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("No console errors.")
