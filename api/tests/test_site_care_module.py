"""The module as the core runs it: its switch, a search, the list, a sheet, the message that leaves, the page."""

from __future__ import annotations

import asyncio
import tomllib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from conftest import CHECK_DAY, reading_of
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.product_modules.contract import ENTRY_POINT_GROUP
from enums.prospect_search import CandidateRejectReason, CandidateStatus
from migrations.run_migrations import _all_migrations
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from models.prospect_search import ProspectSearch
from models.prospect_search_candidate import ProspectSearchCandidate
from models.user import User
from schemas.notification import DemoEventIn
from services.product_module_service import product_module_service

from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.models.watch_event import SiteCareWatchEvent
from devleadhunter_site_care.module import SiteCareModule
from devleadhunter_site_care.services.search_service import search_service
from devleadhunter_site_care.services.site_reader import SiteReader, SiteReading
from devleadhunter_site_care.services.watch_service import watch_service
from devleadhunter_site_care.services.worker import site_care_worker

_API_ROOT = Path(__file__).resolve().parents[1]
_SITES = "/api/v1/site-care/sites"


def _candidate(db: Session, owner: User, search: ProspectSearch, name: str, host: str, **fields: Any) -> int:
    """A business the core's search discarded because it has a website."""
    row = ProspectSearchCandidate(
        search_id=search.id,
        user_id=owner.id,
        trade="paysagiste",
        origin="google",
        name=name,
        city="Reims",
        country="FR",
        phone="02 99 00 00 00",
        website=f"https://www.{host}/",
        website_status="live",
        status=CandidateStatus.REJECTED.value,
        reject_reason=CandidateRejectReason.HAS_WEBSITE.value,
        **fields,
    )
    db.add(row)
    db.commit()
    return row.id


@pytest.fixture
def core_search(db: Session, owner: User) -> ProspectSearch:
    """A finished search of the websites module, whose discarded businesses feed this module."""
    search = ProspectSearch(user_id=owner.id, trades=["paysagiste"], status="completed")
    db.add(search)
    db.commit()
    return search


@pytest.fixture
def readings(monkeypatch: pytest.MonkeyPatch) -> dict[str, SiteReading]:
    """What each site answers when it is read; a host missing here is a healthy site."""
    by_host: dict[str, SiteReading] = {}

    async def read(_self: SiteReader, website: str) -> SiteReading:
        host = website.split("//")[-1].strip("/")
        bare_host = host.removeprefix("www.")
        return by_host.get(bare_host, reading_of(bare_host))

    async def read_pages(_self: SiteReader, urls: list[str]) -> list[str]:
        return []

    monkeypatch.setattr(SiteReader, "read", read)
    monkeypatch.setattr(SiteReader, "read_emails_of_pages", read_pages)
    return by_host


def _run_search(client: TestClient, headers: dict[str, str], **body: Any) -> dict[str, Any]:
    """Launch a search and let the background loop finish it."""
    created = client.post("/api/v1/site-care/searches", json=body, headers=headers)
    assert created.status_code == 200, created.text
    for _ in range(20):
        if not asyncio.run(search_service.run_next_batch()):
            break
    return client.get("/api/v1/site-care/searches/current", headers=headers).json()


class TestIdentity:
    def test_the_module_ships_switched_off(self, db: Session) -> None:
        assert (SiteCareModule.key, SiteCareModule.label) == ("site-care", "Entretien de sites")
        assert SiteCareModule.enabled_by_default is False
        assert product_module_service.is_enabled(db, "site-care") is False

    def test_its_entry_point_names_the_module_class(self) -> None:
        project = tomllib.loads((_API_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

        assert project["entry-points"][ENTRY_POINT_GROUP] == {
            "site-care": "devleadhunter_site_care.module:SiteCareModule"
        }

    def test_its_migration_runs_after_the_core_s(self, site_care_module_installed: SiteCareModule) -> None:
        assert ("add_site_care_tables", "devleadhunter_site_care.migrations.add_site_care_tables") in _all_migrations()

    def test_its_routes_are_closed_while_it_is_switched_off(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get(_SITES, headers=auth_headers)

        assert (response.status_code, response.json()) == (404, {"detail": "Module désactivé"})

    def test_its_routes_ask_for_the_connected_user(
        self, client: TestClient, site_care_module_switched_on: SiteCareModule
    ) -> None:
        assert client.get(_SITES).status_code in (401, 403)

    def test_the_core_runs_its_worker(self, site_care_module_installed: SiteCareModule) -> None:
        assert site_care_module_installed.background_loops() == [site_care_worker.run_forever]


@pytest.mark.usefixtures("site_care_module_switched_on", "background_sessions")
class TestSearch:
    def test_the_options_count_what_the_base_holds(
        self, client: TestClient, auth_headers: dict[str, str], db: Session, owner: User, core_search: ProspectSearch
    ) -> None:
        _candidate(db, owner, core_search, "Jardins Guillot", "jardins-guillot.test")
        _candidate(db, owner, core_search, "Jardins Imbert", "jardins-imbert.test")

        options = client.get("/api/v1/site-care/search-options", headers=auth_headers).json()

        assert options["countries"] == [{"code": "FR", "label": "France", "available_count": 2}]
        assert options["trades"] == [{"key": "paysagiste", "label": "Paysagiste", "available_by_country": {"FR": 2}}]

    def test_a_search_brings_the_discarded_businesses_in_with_their_check(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        owner: User,
        core_search: ProspectSearch,
        readings: dict[str, SiteReading],
    ) -> None:
        _candidate(db, owner, core_search, "Jardins Guillot", "jardins-guillot.test")
        _candidate(db, owner, core_search, "Jardins Imbert", "jardins-imbert.test")
        _candidate(db, owner, core_search, "Jardins Hubert", "jardins-hubert.test")
        readings["jardins-guillot.test"] = reading_of("jardins-guillot.test", powered_by="PHP/7.4.33")
        readings["jardins-hubert.test"] = SiteReading(
            host="jardins-hubert.test", read_at=CHECK_DAY, error="ConnectError"
        )

        search = _run_search(client, auth_headers, trades=["paysagiste"], country="FR", cities=[], count=10)
        listing = client.get(_SITES, headers=auth_headers).json()

        assert (search["status"], search["imported_count"]) == ("completed", 3)
        assert search["note"].startswith("La base n’avait que 3 entreprises")
        assert listing["counts"] == {"total": 3, "with_email": 2, "to_fix": 1, "written": 0}
        assert listing["tab_counts"] == {
            "to_write": 1,
            "written": 0,
            "no_email": 0,
            "nothing": 1,
            "review": 1,
            "all": 3,
        }
        assert [site["business_name"] for site in listing["sites"]] == ["Jardins Guillot"]
        assert listing["sites"][0]["lead"] == {
            "kind": "risk",
            "kind_label": "Version à risque",
            "tone": "red",
            "tech": "PHP 7.4",
            "sentence": "Plus de correctif de sécurité depuis 2022",
        }
        assert listing["sites"][0]["state"] == {"key": "to_write", "label": "À écrire", "tone": "ink"}
        assert listing["sites"][0]["email"] == "contact@jardins-guillot.test"

    def test_a_network_s_site_and_a_platform_page_are_left_out(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        owner: User,
        core_search: ProspectSearch,
        readings: dict[str, SiteReading],
    ) -> None:
        _candidate(db, owner, core_search, "Jardins Guillot", "jardins-guillot.test")
        row_id = _candidate(db, owner, core_search, "Jardins Noël", "facebook.com")
        db.get(ProspectSearchCandidate, row_id).website = "https://www.facebook.com/jardinsnoel"
        db.commit()

        search = _run_search(client, auth_headers, trades=[], country="FR", cities=[], count=10)

        assert search["imported_count"] == 1

    def test_a_business_already_in_the_module_is_never_brought_twice(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        owner: User,
        core_search: ProspectSearch,
        readings: dict[str, SiteReading],
    ) -> None:
        _candidate(db, owner, core_search, "Jardins Guillot", "jardins-guillot.test")
        _run_search(client, auth_headers, trades=[], country="FR", cities=[], count=10)

        second = _run_search(client, auth_headers, trades=[], country="FR", cities=[], count=10)

        assert (second["imported_count"], second["note"]) == (0, "Aucune entreprise disponible pour ces critères.")

    def test_a_second_search_waits_for_the_first(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        client.post("/api/v1/site-care/searches", json={"count": 5}, headers=auth_headers)

        refused = client.post("/api/v1/site-care/searches", json={"count": 5}, headers=auth_headers)

        assert refused.status_code == 409 and "tourne déjà" in refused.json()["detail"]


@pytest.fixture
def site_to_write(
    client: TestClient,
    auth_headers: dict[str, str],
    db: Session,
    owner: User,
    core_search: ProspectSearch,
    readings: dict[str, SiteReading],
) -> dict[str, Any]:
    """The sheet of a site whose PHP is no longer fixed, with an email address."""
    _candidate(db, owner, core_search, "Jardins Guillot", "jardins-guillot.test")
    readings["jardins-guillot.test"] = reading_of("jardins-guillot.test", powered_by="PHP/7.4.33", has_dmarc=False)
    _run_search(client, auth_headers, trades=[], country="FR", cities=[], count=10)
    site_id = client.get(_SITES, headers=auth_headers).json()["sites"][0]["id"]
    return client.get(f"{_SITES}/{site_id}", headers=auth_headers).json()


@pytest.mark.usefixtures("site_care_module_switched_on", "background_sessions")
class TestSheet:
    def test_the_sheet_sorts_what_was_seen_and_writes_the_message(self, site_to_write: dict[str, Any]) -> None:
        assert [point["kind_label"] for point in site_to_write["fixes"]] == ["Version à risque"]
        assert [point["kind_label"] for point in site_to_write["watches"]] == ["E-mails"]
        assert site_to_write["also"] == "Aussi : e-mails"
        assert site_to_write["good_line"].startswith("10 points sont bons : le cadenas,")
        assert site_to_write["offer"] == [{"label": "Passage à une version de PHP suivie", "price_label": "190 €"}]
        assert site_to_write["monthly_label"] == "100 € par mois"
        assert site_to_write["message"]["subject"] == "La version de PHP de votre site"
        assert site_to_write["page_url"].endswith(f"/bilan/{site_to_write['page_url'].rsplit('/', 1)[-1]}")
        assert site_to_write["page_url"] in site_to_write["message"]["paragraphs_with_link"][3]
        assert (site_to_write["can_send"], site_to_write["send_refusal"]) == (True, None)

    def test_the_first_message_leaves_through_the_core_and_makes_a_prospect(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        site_to_write: dict[str, Any],
        sender_configured: list[dict[str, Any]],
    ) -> None:
        sent = client.post(f"{_SITES}/{site_to_write['id']}/send", json={}, headers=auth_headers)

        assert sent.status_code == 200, sent.text
        sheet = sent.json()
        site = db.get(SiteCareSite, site_to_write["id"])
        db.refresh(site)
        prospect = db.get(ProspectDB, site.prospect_id)
        log = db.get(EmailLog, site.last_email_log_id)
        assert len(sender_configured) == 1
        assert sender_configured[0]["to_email"] == "contact@jardins-guillot.test"
        assert "PHP 7.4" in sender_configured[0]["html_body"]
        assert (prospect.name, prospect.email, prospect.contacted_by_module) == (
            "Jardins Guillot",
            "contact@jardins-guillot.test",
            "site-care",
        )
        assert (log.prospect_id, log.subject) == (prospect.id, "La version de PHP de votre site")
        assert sheet["tab"] == "written" and sheet["state"]["key"] == "written"
        assert (sheet["can_send"], sheet["send_refusal"].startswith("Déjà écrit le")) == (False, True)
        assert [message["kind_label"] for message in sheet["sent_messages"]] == ["Premier message"]

    def test_a_second_message_is_refused(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        site_to_write: dict[str, Any],
        sender_configured: list[dict[str, Any]],
    ) -> None:
        client.post(f"{_SITES}/{site_to_write['id']}/send", json={}, headers=auth_headers)

        again = client.post(f"{_SITES}/{site_to_write['id']}/send", json={}, headers=auth_headers)

        assert again.status_code == 409 and again.json()["detail"].startswith("Déjà écrit le")
        assert len(sender_configured) == 1

    def test_a_reply_shows_on_the_line(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        site_to_write: dict[str, Any],
        sender_configured: list[dict[str, Any]],
    ) -> None:
        client.post(f"{_SITES}/{site_to_write['id']}/send", json={}, headers=auth_headers)
        site = db.get(SiteCareSite, site_to_write["id"])
        db.refresh(site)
        db.get(EmailLog, site.last_email_log_id).replied_at = datetime(2026, 11, 12, 9, 0)
        db.commit()

        line = client.get(_SITES, params={"tab": "written"}, headers=auth_headers).json()["sites"][0]

        assert line["state"] == {"key": "replied", "label": "A répondu", "tone": "violet"}

    def test_the_address_can_be_typed_by_hand(
        self, client: TestClient, auth_headers: dict[str, str], site_to_write: dict[str, Any]
    ) -> None:
        url = f"{_SITES}/{site_to_write['id']}"

        assert client.patch(url, json={"email": "pas une adresse"}, headers=auth_headers).status_code == 422
        removed = client.patch(url, json={"email": ""}, headers=auth_headers).json()
        typed = client.patch(url, json={"email": "Patron@Jardins-Guillot.test"}, headers=auth_headers).json()

        assert (removed["tab"], removed["send_refusal"]) == ("no_email", "Pas d’adresse e-mail pour ce prospect.")
        assert (typed["tab"], typed["email"]) == ("to_write", "patron@jardins-guillot.test")

    def test_a_site_taken_out_of_the_list_is_gone(
        self, client: TestClient, auth_headers: dict[str, str], site_to_write: dict[str, Any]
    ) -> None:
        url = f"{_SITES}/{site_to_write['id']}"

        assert client.delete(url, headers=auth_headers).status_code == 204
        assert client.get(url, headers=auth_headers).status_code == 404
        assert client.get(_SITES, params={"tab": "all"}, headers=auth_headers).json()["counts"]["total"] == 0

    def test_another_user_never_sees_the_site(
        self, client: TestClient, db: Session, site_to_write: dict[str, Any]
    ) -> None:
        from services.auth_service import AuthService

        db.add(User(name="Marc Dupont", email="marc@example.com", hashed_password="x"))
        db.commit()
        stranger = {"Authorization": f"Bearer {AuthService.create_access_token({'sub': 'marc@example.com'})}"}

        assert client.get(f"{_SITES}/{site_to_write['id']}", headers=stranger).status_code == 404
        assert client.get(_SITES, params={"tab": "all"}, headers=stranger).json()["counts"]["total"] == 0


@pytest.mark.usefixtures("site_care_module_switched_on", "background_sessions")
class TestSettings:
    def test_the_owner_s_rules_are_applied_to_the_sites_already_checked(
        self, client: TestClient, auth_headers: dict[str, str], site_to_write: dict[str, Any]
    ) -> None:
        settings = client.get("/api/v1/site-care/settings", headers=auth_headers).json()
        assert settings["presenter"]["name"] == "Léo Guillaume"
        for price in settings["prices"]:
            if price["key"] == "php":
                price["price_cents"] = 24900
        for point in settings["points"]:
            if point["key"] == "php":
                point["is_enabled"] = False
        settings["presenter"]["role"] = "développeur web à Rennes"

        saved = client.put("/api/v1/site-care/settings", json=settings, headers=auth_headers)

        assert saved.status_code == 200, saved.text
        assert [p["price_cents"] for p in saved.json()["prices"] if p["key"] in ("php", "mobile")] == [24900, None]
        sheet = client.get(f"{_SITES}/{site_to_write['id']}", headers=auth_headers).json()
        # Without the PHP point, only the DMARC rule is left to watch: nothing to write about.
        assert (sheet["tab"], sheet["fixes"], sheet["lead"]["kind"]) == ("nothing", [], "mail")


@pytest.mark.usefixtures("site_care_module_switched_on", "background_sessions")
class TestPage:
    def test_the_page_is_public_and_never_indexed(self, client: TestClient, site_to_write: dict[str, Any]) -> None:
        slug = site_to_write["page_url"].rsplit("/", 1)[-1]

        response = client.get(f"/api/v1/site-care/public/pages/{slug}")

        assert response.status_code == 200
        assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
        assert response.json()["business_name"] == "Jardins Guillot"
        assert response.json()["title"]["mark"] == "depuis 2022"
        assert client.get("/api/v1/site-care/public/pages/jardins-guillot").status_code == 404

    def test_an_opened_page_is_counted_once_per_visit_and_robots_are_ignored(
        self,
        db: Session,
        site_to_write: dict[str, Any],
        site_care_module_installed: SiteCareModule,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from services.notification_service import NotificationService

        notified: list[str] = []

        async def notify(_self: NotificationService, **kwargs: Any) -> None:
            notified.append(kwargs["body"])

        monkeypatch.setattr(NotificationService, "notify_module_event", notify)
        slug = site_to_write["page_url"].rsplit("/", 1)[-1]
        opened = DemoEventIn(demo_slug=slug, event="site_care_page_opened")
        robot = DemoEventIn(demo_slug=slug, event="site_care_page_opened", is_automated_browser=True)

        for event in (robot, opened, opened):
            asyncio.run(site_care_module_installed.handle_demo_beacon(db, event))

        site = db.get(SiteCareSite, site_to_write["id"])
        db.refresh(site)
        assert site.page_open_count == 2 and site.page_opened_at is not None
        assert notified == ["🛠️ Entretien de sites · a ouvert la page préparée pour lui"]


@pytest.mark.usefixtures("site_care_module_switched_on", "background_sessions")
class TestCareAndWatch:
    def test_a_client_under_care_gets_his_monthly_report_once(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        site_to_write: dict[str, Any],
        sender_configured: list[dict[str, Any]],
    ) -> None:
        started = client.post(
            f"{_SITES}/{site_to_write['id']}/care-plan", json={"monthly_price_cents": 15000}, headers=auth_headers
        ).json()
        plans = client.get("/api/v1/site-care/care-plans", headers=auth_headers).json()
        plan_id = plans["plans"][0]["id"]

        report = client.post(f"/api/v1/site-care/care-plans/{plan_id}/report", headers=auth_headers)
        again = client.post(f"/api/v1/site-care/care-plans/{plan_id}/report", headers=auth_headers)

        assert started["state"] == {"key": "care", "label": "En suivi", "tone": "green"}
        assert plans["stats"] == {"client_count": 1, "monthly_revenue_label": "150 €", "reports_due_count": 1}
        assert (plans["plans"][0]["report_label"], plans["plans"][0]["can_send_report"]) == ("À envoyer", True)
        assert (report.status_code, report.json()["report_label"]) == (200, "Envoyé")
        assert sender_configured[0]["subject"] == "Le rapport du mois pour jardins-guillot.test"
        assert (again.status_code, again.json()["detail"]) == (409, "Le rapport de ce mois est déjà parti.")
        assert client.delete(f"/api/v1/site-care/care-plans/{plan_id}", headers=auth_headers).status_code == 204
        assert client.get("/api/v1/site-care/care-plans", headers=auth_headers).json()["plans"] == []

    def test_the_watch_tells_a_hacked_site_and_the_dates_coming_up(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        owner: User,
        core_search: ProspectSearch,
        readings: dict[str, SiteReading],
    ) -> None:
        _candidate(db, owner, core_search, "Bellanger Électricité", "bellanger-electricite.test")
        _candidate(db, owner, core_search, "Garage Jacquet", "garage-jacquet.test")
        _candidate(db, owner, core_search, "Auto Daniel", "auto-daniel.test")
        readings["bellanger-electricite.test"] = reading_of(
            "bellanger-electricite.test", gambling_links=["bahis.example"]
        )
        readings["garage-jacquet.test"] = reading_of("garage-jacquet.test", powered_by="PHP/8.2.20")
        readings["auto-daniel.test"] = reading_of("auto-daniel.test", powered_by="PHP/8.2.12")
        _run_search(client, auth_headers, trades=[], country="FR", cities=[], count=10)

        watch = client.get("/api/v1/site-care/watch", headers=auth_headers).json()

        assert [(line["title"], line["tone"], line["target"]["site_id"] is not None) for line in watch["today"]] == [
            ("Un site piraté", "red", True)
        ]
        assert watch["today"][0]["detail"].startswith("Bellanger Électricité, à Reims :")
        deadline = watch["deadlines"][0]
        assert deadline["title"] == "PHP 8.2 s’arrête le 31 décembre 2026"
        assert (deadline["site_count"], deadline["action_label"]) == (2, "Voir ces 2 prospects")
        assert deadline["target"] == {"site_id": None, "tab": "all", "kind": "late"}

    def test_an_old_check_is_refreshed_and_a_site_that_fell_is_noted(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        site_to_write: dict[str, Any],
        readings: dict[str, SiteReading],
    ) -> None:
        site = db.get(SiteCareSite, site_to_write["id"])
        site.checked_at = datetime.utcnow() - timedelta(days=30)
        db.commit()
        readings["jardins-guillot.test"] = SiteReading(
            host="jardins-guillot.test", read_at=datetime.utcnow().replace(microsecond=0), error="ConnectError"
        )
        watch_service._next_pass_after = 0.0

        asyncio.run(watch_service.recheck_due_sites())

        db.refresh(site)
        kinds = list(db.execute(select(SiteCareWatchEvent.kind).where(SiteCareWatchEvent.site_id == site.id)).scalars())
        assert (site.status, kinds) == ("unreachable", ["unreachable"])
        sheet = client.get(f"{_SITES}/{site.id}", headers=auth_headers).json()
        assert sheet["tab"] == "review" and sheet["unread_text"].startswith("L’adresse du site ne mène plus nulle part")
