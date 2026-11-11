"""Screenshots of the module's real pages against the throwaway local API. Usage: shoot_pages.py [name_filter]"""

from __future__ import annotations

import contextlib
import json
import pathlib
import sys
import urllib.request

from playwright.sync_api import Page, sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "shots"
OUT.mkdir(exist_ok=True)
TOKEN = (HERE / "token.txt").read_text(encoding="utf-8").strip()
WEB = "http://localhost:5173"
DEMO = "http://localhost:3001"
API = "http://localhost:8040/api/v1"
ONLY = sys.argv[1] if len(sys.argv) > 1 else ""
HIDE_DEVTOOLS = "#nuxt-devtools-container, nuxt-devtools-frame { display: none !important; }"


def api_get(path: str) -> dict:
    request = urllib.request.Request(f"{API}{path}", headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def settle(page: Page, seconds: float = 2.5) -> None:
    with contextlib.suppress(Exception):
        page.wait_for_load_state("networkidle", timeout=60_000)
    page.wait_for_timeout(int(seconds * 1000))
    page.add_style_tag(content=HIDE_DEVTOOLS)


def shot(page: Page, name: str) -> None:
    page.screenshot(path=str(OUT / f"{name}.png"))
    print("saved", name, flush=True)


def wanted(name: str) -> bool:
    return ONLY in name


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    context = browser.new_context(
        viewport={"width": 820, "height": 1180}, device_scale_factor=1.5, color_scheme="light"
    )
    context.add_init_script(
        f"localStorage.setItem('token', {json.dumps(TOKEN)}); localStorage.setItem('dlh-active-module', 'site-care');"
    )
    page = context.new_page()
    errors: list[str] = []
    page.on("console", lambda message: errors.append(message.text[:300]) if message.type == "error" else None)
    page.on("pageerror", lambda error: errors.append(f"PAGEERROR {str(error)[:300]}"))

    if wanted("list"):
        page.set_viewport_size({"width": 820, "height": 2300})
        page.goto(f"{WEB}/dashboard/site-care", timeout=240_000)
        settle(page, 4)
        shot(page, "list-to-write")
        page.set_viewport_size({"width": 820, "height": 1180})
        page.get_by_role("tab", name="Sans email").click()
        settle(page, 1.5)
        shot(page, "list-no-email")
        page.get_by_role("tab", name="Tous").click()
        settle(page, 1.5)
        shot(page, "list-all")

    if wanted("drawer"):
        page.set_viewport_size({"width": 820, "height": 2600})
        page.goto(f"{WEB}/dashboard/site-care", timeout=240_000)
        settle(page, 3)
        page.get_by_role("button", name="Jardins Guillot").first.click()
        settle(page, 2)
        shot(page, "drawer")

    if wanted("search"):
        page.set_viewport_size({"width": 820, "height": 1400})
        page.goto(f"{WEB}/dashboard/site-care/search", timeout=240_000)
        settle(page, 3)
        shot(page, "search-1-target")
        for name in ("search-2-zone", "search-3-criteria", "search-4-launch"):
            page.get_by_role("button", name="Suivant").click()
            settle(page, 1)
            shot(page, name)

    if wanted("watch"):
        page.set_viewport_size({"width": 820, "height": 1500})
        page.goto(f"{WEB}/dashboard/site-care/watch", timeout=240_000)
        settle(page, 3)
        shot(page, "watch")

    if wanted("care"):
        page.set_viewport_size({"width": 820, "height": 1180})
        page.goto(f"{WEB}/dashboard/site-care/care-plans", timeout=240_000)
        settle(page, 3)
        shot(page, "care-plans")

    if wanted("settings"):
        page.set_viewport_size({"width": 820, "height": 3000})
        page.goto(f"{WEB}/dashboard/settings/site-care", timeout=240_000)
        settle(page, 3)
        shot(page, "settings")

    if wanted("menu"):
        page.set_viewport_size({"width": 1366, "height": 900})
        page.goto(f"{WEB}/dashboard/site-care", timeout=240_000)
        settle(page, 3)
        shot(page, "desktop-list")

    if wanted("page"):
        sites = api_get("/site-care/sites?tab=all&limit=100")["sites"]
        for label, business in (
            ("php", "Jardins Guillot"),
            ("hacked", "Bellanger Électricité"),
            ("mail", "Garage Fabre"),
        ):
            site = next(site for site in sites if site["business_name"] == business)
            slug = api_get(f"/site-care/sites/{site['id']}")["page_url"].rsplit("/", 1)[-1]
            phone = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
            prospect_page = phone.new_page()
            prospect_page.on(
                "console", lambda message: errors.append(message.text[:300]) if message.type == "error" else None
            )
            prospect_page.goto(f"{DEMO}/bilan/{slug}?internal=1", timeout=240_000)
            settle(prospect_page, 3)
            prospect_page.screenshot(path=str(OUT / f"page-{label}.png"), full_page=True)
            print(
                "saved page",
                label,
                "height",
                prospect_page.evaluate("document.documentElement.scrollHeight"),
                flush=True,
            )
            phone.close()

    print("console errors:", len(errors))
    for error in errors[:12]:
        print("  ", error)
    browser.close()
