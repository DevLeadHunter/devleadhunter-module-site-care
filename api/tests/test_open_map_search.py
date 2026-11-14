"""A search on the open map: what it reads of OpenStreetMap's answer, what it keeps, what it never reads twice."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from conftest import reading_of
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from devleadhunter_site_care.catalog import BusinessFamily
from devleadhunter_site_care.migrations import add_site_care_open_map_search
from devleadhunter_site_care.models.map_business import SiteCareMapBusiness
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.services.open_map import (
    OpenMapAnswer,
    OpenMapDirectory,
    OpenMapUnavailableError,
    TownLocator,
)
from devleadhunter_site_care.services.search_service import search_service
from devleadhunter_site_care.services.site_reader import SiteReader, SiteReading

_SITES = "/api/v1/site-care/sites"
_SEARCHES = "/api/v1/site-care/searches"
_EVERY_FAMILY: list[BusinessFamily] = list(BusinessFamily)


def _answer(*businesses: dict[str, str]) -> str:
    """The open map's answer for some objects: a header, then one tab-separated line per object."""
    lines: list[str] = ["\t".join(OpenMapAnswer.COLUMNS)]
    for number, business in enumerate(businesses, start=1):
        cells: dict[str, str] = {"::type": "node", "::id": str(number), "::lat": "48.1", "::lon": "-1.6", **business}
        lines.append("\t".join(cells.get(column, "") for column in OpenMapAnswer.COLUMNS))
    return "\n".join(lines) + "\n"


def _plumber(name: str, host: str, **tags: str) -> dict[str, str]:
    """A plumber of the open map with a site of his own."""
    return {"name": name, "craft": "plumber", "website": f"https://www.{host}", **tags}


@pytest.fixture
def contact_page_emails(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """The addresses a contact or legal page shows, by page address; a page missing here shows none."""
    emails_by_page: dict[str, list[str]] = {}

    async def read_emails_of_pages(_self: SiteReader, urls: list[str]) -> list[str]:
        return [email for url in urls for email in emails_by_page.get(url, [])]

    monkeypatch.setattr(SiteReader, "read_emails_of_pages", read_emails_of_pages)
    return emails_by_page


@pytest.fixture
def readings(monkeypatch: pytest.MonkeyPatch, contact_page_emails: dict[str, list[str]]) -> dict[str, SiteReading]:
    """What each site answers when it is read; a host missing here is a healthy site."""
    by_host: dict[str, SiteReading] = {}

    async def read(_self: SiteReader, website: str) -> SiteReading:
        bare_host = website.split("//")[-1].strip("/").removeprefix("www.")
        return by_host.get(bare_host, reading_of(bare_host))

    monkeypatch.setattr(SiteReader, "read", read)
    return by_host


def _run_search(client: TestClient, headers: dict[str, str], **body: Any) -> dict[str, Any]:
    """Launch a search on the open map and let the background loop finish it."""
    created = client.post(_SEARCHES, json={"source": "open_map", **body}, headers=headers)
    assert created.status_code == 200, created.text
    for _ in range(20):
        if not asyncio.run(search_service.run_next_batch()):
            break
    return client.get(f"{_SEARCHES}/current", headers=headers).json()


class TestAnswer:
    def test_an_independent_business_is_read_with_its_trade_in_french(self) -> None:
        answer = _answer(
            {
                "name": "Plomberie Guillot",
                "craft": "plumber",
                "contact:website": "plomberie-guillot.test",
                "phone": "+33 2 99 00 00 00;+33 6 00 00 00 00",
                "email": "Contact@Plomberie-Guillot.test",
                "addr:city": "Rennes",
            }
        )

        [business] = OpenMapAnswer.businesses_of(answer, _EVERY_FAMILY)

        assert (business.business_name, business.family, business.trade_label) == (
            "Plomberie Guillot",
            BusinessFamily.CRAFT,
            "Plombier",
        )
        assert (business.website, business.host) == ("https://plomberie-guillot.test", "plomberie-guillot.test")
        assert (business.city, business.phone, business.email) == (
            "Rennes",
            "+33 2 99 00 00 00",
            "contact@plomberie-guillot.test",
        )
        assert (business.map_reference, business.latitude, business.longitude) == ("node/1", 48.1, -1.6)

    def test_what_is_not_an_independent_business_s_own_site_is_left_out(self) -> None:
        answer = _answer(
            _plumber("Plomberie Guillot", "plomberie-guillot.test"),
            {"name": "Enseigne Rennes", "shop": "bakery", "website": "https://enseigne.test", "brand": "Enseigne"},
            {"name": "Agence de Rennes", "office": "insurance", "website": "https://reseau.test/agences/rennes"},
            {"name": "Mairie de Rennes", "office": "government", "website": "https://mairie-rennes.test"},
            {"name": "Parc de Rennes", "website": "https://parc-rennes.test"},
            {"craft": "painter", "website": "https://peintre-sans-nom.test"},
        )

        businesses = OpenMapAnswer.businesses_of(answer, _EVERY_FAMILY)

        assert [business.business_name for business in businesses] == ["Plomberie Guillot"]

    def test_a_site_shared_by_several_businesses_is_a_network_s(self) -> None:
        answer = _answer(
            *(
                {"name": f"Coiffure {town}", "shop": "hairdresser", "website": "https://reseau-coiffure.test"}
                for town in ("Rennes", "Vitré", "Fougères")
            ),
            {"name": "Le Fournil", "shop": "bakery", "website": "https://www.le-fournil.test/fr/"},
            {"name": "Le Fournil du port", "shop": "bakery", "website": "le-fournil.test"},
        )

        businesses = OpenMapAnswer.businesses_of(answer, _EVERY_FAMILY)

        assert [(business.business_name, business.host) for business in businesses] == [
            ("Le Fournil", "le-fournil.test")
        ]

    def test_only_the_families_asked_for_are_kept(self) -> None:
        answer = _answer(
            _plumber("Plomberie Guillot", "plomberie-guillot.test"),
            {"name": "Le Bistrot", "amenity": "restaurant", "website": "https://le-bistrot.test"},
            {"name": "Hôtel du Port", "tourism": "hotel", "website": "https://hotel-du-port.test"},
            {"name": "École du Port", "amenity": "school", "website": "https://ecole-du-port.test"},
        )

        businesses = OpenMapAnswer.businesses_of(answer, [BusinessFamily.FOOD, BusinessFamily.LODGING])

        assert [(business.business_name, business.trade_label) for business in businesses] == [
            ("Le Bistrot", "Restaurant"),
            ("Hôtel du Port", "Hôtel"),
        ]

    def test_the_question_names_the_department_and_the_families(self) -> None:
        query = OpenMapDirectory.query_of("69", [BusinessFamily.CRAFT])

        assert '["ref:INSEE"~"^(69D|69M)$"]' in query
        assert 'nwr["craft"]["website"](area.zone);nwr["craft"]["contact:website"](area.zone);' in query
        assert '"shop"]["website"' not in query


@pytest.mark.usefixtures("site_care_module_switched_on", "background_sessions")
class TestOpenMapSearch:
    def test_the_options_list_the_departments_the_families_and_what_to_keep(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        options = client.get("/api/v1/site-care/search-options", headers=auth_headers).json()
        open_map = options["open_map"]

        assert [(source["key"], source["label"]) for source in options["sources"]] == [
            ("base", "Ma base"),
            ("open_map", "OpenStreetMap"),
        ]
        assert len(open_map["departments"]) == 96
        assert {"key": "35", "label": "Ille-et-Vilaine (35)", "hint": None} in open_map["departments"]
        assert [family["key"] for family in open_map["families"]] == ["craft", "shop", "office", "food", "lodging"]
        assert [rule["key"] for rule in open_map["keep_rules"]] == ["security", "issues", "all"]
        assert (open_map["max_count"], open_map["max_departments"]) == (2000, 20)

    def test_a_search_keeps_only_the_sites_with_a_security_issue(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        open_map_answers: dict[str, str],
        readings: dict[str, SiteReading],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        open_map_answers["35"] = _answer(
            _plumber("Plomberie Guillot", "plomberie-guillot.test", email="contact@plomberie-guillot.test"),
            _plumber("Plomberie Imbert", "plomberie-imbert.test", **{"addr:city": "Vitré"}),
            {"name": "Le Fournil", "shop": "bakery", "website": "https://le-fournil.test"},
        )
        readings["plomberie-guillot.test"] = reading_of("plomberie-guillot.test", powered_by="PHP/7.4.33")
        readings["le-fournil.test"] = reading_of("le-fournil.test", has_dmarc=False, has_spf=False)

        async def town_at(_self: TownLocator, _latitude: float, _longitude: float) -> str | None:
            return "Rennes"

        monkeypatch.setattr(TownLocator, "town_at", town_at)

        search = _run_search(client, auth_headers, departments=["35"], keep_rule="security", count=50)
        listing = client.get(f"{_SITES}?tab=all", headers=auth_headers).json()

        assert (search["status"], search["checked_count"], search["imported_count"]) == ("completed", 3, 1)
        assert search["note"] == "3 sites lus, 1 gardé : la zone n’en a pas d’autres pour ces critères."
        assert (search["source_label"], search["zone_label"], search["trades_label"]) == (
            "OpenStreetMap",
            "Ille-et-Vilaine (35)",
            "Toutes les entreprises",
        )
        assert search["keep_rule_label"] == "Les sites qui ont un souci de sécurité"
        [site] = listing["sites"]
        assert (site["business_name"], site["city"], site["trade_label"]) == (
            "Plomberie Guillot",
            "Rennes",
            "Plombier-chauffagiste",
        )
        assert (site["lead"]["kind"], site["lead"]["tech"]) == ("risk", "PHP 7.4")
        assert site["email"] == "contact@plomberie-guillot.test"
        read = db.execute(select(SiteCareMapBusiness.host, SiteCareMapBusiness.was_kept)).all()
        assert sorted(read) == [
            ("le-fournil.test", False),
            ("plomberie-guillot.test", True),
            ("plomberie-imbert.test", False),
        ]

    def test_a_kept_site_without_an_address_takes_the_one_of_its_contact_page(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        open_map_answers: dict[str, str],
        readings: dict[str, SiteReading],
        contact_page_emails: dict[str, list[str]],
    ) -> None:
        open_map_answers["35"] = _answer(
            _plumber("Plomberie Guillot", "plomberie-guillot.test"),
            _plumber("Plomberie Imbert", "plomberie-imbert.test"),
        )
        for host in ("plomberie-guillot.test", "plomberie-imbert.test"):
            contact_page: str = f"https://www.{host}/contact"
            readings[host] = reading_of(host, emails=[], contact_page_urls=[contact_page])
            contact_page_emails[contact_page] = [f"contact@{host}"]
        readings["plomberie-guillot.test"].powered_by = "PHP/7.4.33"

        _run_search(client, auth_headers, departments=["35"], keep_rule="security", count=50)
        [site] = client.get(f"{_SITES}?tab=all", headers=auth_headers).json()["sites"]

        assert (site["business_name"], site["email"]) == ("Plomberie Guillot", "contact@plomberie-guillot.test")

    def test_a_town_the_list_of_communes_did_not_give_is_caught_up_later(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        open_map_answers: dict[str, str],
        readings: dict[str, SiteReading],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        open_map_answers["35"] = _answer(
            _plumber("Plomberie Guillot", "plomberie-guillot.test"),
            _plumber("Plomberie Imbert", "plomberie-imbert.test"),
        )
        _run_search(client, auth_headers, departments=["35"], keep_rule="all", count=10)

        async def town_at(_self: TownLocator, _latitude: float, _longitude: float) -> str | None:
            return "Rennes"

        monkeypatch.setattr(TownLocator, "town_at", town_at)
        asyncio.run(search_service.name_missing_towns())
        db.expire_all()

        assert db.execute(select(SiteCareSite.city)).scalars().all() == ["Rennes", "Rennes"]
        assert client.get(f"{_SITES}?tab=all&q=rennes", headers=auth_headers).json()["matching_count"] == 2

    def test_a_point_in_no_commune_is_never_asked_again(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        open_map_answers: dict[str, str],
        readings: dict[str, SiteReading],
    ) -> None:
        open_map_answers["35"] = _answer(_plumber("Plomberie Guillot", "plomberie-guillot.test"))
        _run_search(client, auth_headers, departments=["35"], keep_rule="all", count=10)

        asyncio.run(search_service.name_missing_towns())
        db.expire_all()

        assert db.execute(select(SiteCareSite.city)).scalars().all() == [None]
        assert db.execute(select(SiteCareMapBusiness.latitude, SiteCareMapBusiness.longitude)).all() == [(None, None)]

    def test_a_search_for_security_issues_leaves_a_doubtful_address_out(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        open_map_answers: dict[str, str],
        readings: dict[str, SiteReading],
    ) -> None:
        open_map_answers["35"] = _answer(
            _plumber("Plomberie Guillot", "plomberie-guillot.test"),
            _plumber("Plomberie Imbert", "plomberie-imbert.test"),
        )
        readings["plomberie-guillot.test"] = reading_of(
            "plomberie-guillot.test", gambling_links=["jeux.example"], has_hidden_gambling_link=True
        )
        readings["plomberie-imbert.test"] = reading_of(
            "plomberie-imbert.test", gambling_links=["jeux.example"], host_on_another_domain="jeux.example"
        )

        search = _run_search(client, auth_headers, departments=["35"], keep_rule="security", count=50)
        [site] = client.get(f"{_SITES}?tab=all", headers=auth_headers).json()["sites"]

        assert (search["checked_count"], search["imported_count"]) == (2, 1)
        assert (site["business_name"], site["lead"]["kind"]) == ("Plomberie Guillot", "hack")

    def test_a_site_read_once_is_never_read_again(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        open_map_answers: dict[str, str],
        readings: dict[str, SiteReading],
    ) -> None:
        open_map_answers["35"] = _answer(_plumber("Plomberie Guillot", "plomberie-guillot.test"))
        _run_search(client, auth_headers, departments=["35"], keep_rule="security", count=50)
        open_map_answers["35"] = _answer(
            _plumber("Plomberie Guillot", "plomberie-guillot.test"),
            _plumber("Plomberie Hubert", "plomberie-hubert.test"),
        )

        second = _run_search(client, auth_headers, departments=["35"], keep_rule="all", count=50)

        assert (second["checked_count"], second["imported_count"]) == (1, 1)

    def test_a_search_stops_at_the_count_asked_and_leaves_the_rest_unread(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        open_map_answers: dict[str, str],
        readings: dict[str, SiteReading],
    ) -> None:
        open_map_answers["35"] = _answer(
            *(_plumber(f"Plomberie {number}", f"plomberie-{number}.test") for number in range(1, 5))
        )

        search = _run_search(client, auth_headers, departments=["35"], keep_rule="all", count=2)
        second = _run_search(client, auth_headers, departments=["35"], keep_rule="all", count=10)

        assert (search["status"], search["imported_count"], search["note"]) == ("completed", 2, None)
        assert (second["checked_count"], second["imported_count"]) == (2, 2)
        assert second["note"] == "2 sites lus, 2 gardés : la zone n’en a pas d’autres pour ces critères."
        assert len(db.execute(select(SiteCareSite)).scalars().all()) == 4

    def test_the_map_s_phone_is_never_compared_as_the_google_listing_s(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        open_map_answers: dict[str, str],
        readings: dict[str, SiteReading],
    ) -> None:
        open_map_answers["35"] = _answer(_plumber("Plomberie Guillot", "plomberie-guillot.test", phone="0611111111"))

        _run_search(client, auth_headers, departments=["35"], keep_rule="all", count=10)
        [site] = client.get(f"{_SITES}?tab=all", headers=auth_headers).json()["sites"]

        assert site["lead"]["kind"] == "ok"

    def test_several_departments_are_gone_through_one_after_the_other(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        open_map_answers: dict[str, str],
        readings: dict[str, SiteReading],
    ) -> None:
        open_map_answers["35"] = _answer(_plumber("Plomberie Guillot", "plomberie-guillot.test"))
        open_map_answers["2A"] = _answer(_plumber("Plomberie Imbert", "plomberie-imbert.test"))

        search = _run_search(client, auth_headers, departments=["35", "2a", "35"], families=["craft"], count=10)

        assert (search["checked_count"], search["imported_count"]) == (2, 2)
        assert (search["zone_label"], search["trades_label"]) == ("Ille-et-Vilaine (35), Corse-du-Sud (2A)", "Artisans")

    def test_a_running_search_can_be_stopped(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        open_map_answers: dict[str, str],
        readings: dict[str, SiteReading],
    ) -> None:
        open_map_answers["35"] = _answer(_plumber("Plomberie Guillot", "plomberie-guillot.test"))
        client.post(_SEARCHES, json={"source": "open_map", "departments": ["35"], "count": 10}, headers=auth_headers)

        stopped = client.post(f"{_SEARCHES}/current/stop", headers=auth_headers).json()
        was_worked_on = asyncio.run(search_service.run_next_batch())

        assert (stopped["status"], stopped["note"]) == (
            "completed",
            "Recherche arrêtée à la main. Les sites déjà gardés sont dans la liste.",
        )
        assert was_worked_on is False
        assert client.get(f"{_SITES}?tab=all", headers=auth_headers).json()["sites"] == []

    def test_the_open_map_not_answering_ends_the_search_with_the_reason(
        self, client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def businesses_of(_self: OpenMapDirectory, _department: str, _families: list[BusinessFamily]) -> None:
            raise OpenMapUnavailableError("OpenStreetMap ne répond pas (HTTP 504).")

        monkeypatch.setattr(OpenMapDirectory, "businesses_of", businesses_of)

        search = _run_search(client, auth_headers, departments=["35"], count=10)

        assert search["status"] == "failed"
        assert search["note"].startswith("OpenStreetMap ne répond pas (HTTP 504).")

    def test_a_search_without_a_known_department_is_refused(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        without_zone = client.post(_SEARCHES, json={"source": "open_map", "count": 10}, headers=auth_headers)
        unknown_zone = client.post(
            _SEARCHES, json={"source": "open_map", "departments": ["99"], "count": 10}, headers=auth_headers
        )
        unknown_family = client.post(
            _SEARCHES,
            json={"source": "open_map", "departments": ["35"], "families": ["factory"], "count": 10},
            headers=auth_headers,
        )

        assert (without_zone.status_code, without_zone.json()["detail"]) == (409, "Choisissez au moins un département.")
        assert (unknown_zone.status_code, unknown_family.status_code) == (422, 422)


class TestMigration:
    def test_it_adds_the_search_s_new_columns_once(self, tmp_path: Path) -> None:
        engine = create_engine(f"sqlite:///{tmp_path / 'before.db'}")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE site_care_searches (id INTEGER PRIMARY KEY, user_id INTEGER)"))
            connection.execute(text("INSERT INTO site_care_searches (id, user_id) VALUES (1, 1)"))

        add_site_care_open_map_search.run_migration(engine)
        add_site_care_open_map_search.run_migration(engine)

        columns = {column["name"] for column in inspect(engine).get_columns("site_care_searches")}
        assert {"source", "departments", "families", "collected_departments", "keep_rule"} <= columns
        assert inspect(engine).has_table("site_care_map_businesses")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT source, keep_rule, departments FROM site_care_searches")).all() == [
                ("base", "all", None)
            ]
