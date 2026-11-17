"""What the watch tells the owner at once: a site found hacked, a point that got worse, and no more than a day bears."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pytest
from conftest import CHECK_DAY, reading_of
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from models.user import User
from services.notification_service import NotificationService

from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.models.watch_event import SiteCareWatchEvent
from devleadhunter_site_care.services import watch_service as watch_service_module
from devleadhunter_site_care.services.owner_settings_service import owner_settings_service
from devleadhunter_site_care.services.site_reader import SiteReader, SiteReading
from devleadhunter_site_care.services.site_service import site_service
from devleadhunter_site_care.services.watch_notifier import WatchNotifier
from devleadhunter_site_care.services.watch_service import watch_service

_TAG: str = "🛠️ Entretien de sites"
_INVALID_CERTIFICATE_FACT: str = (
    "Le certificat de sécurité du site n’est pas valable : le navigateur affiche un avertissement avant d’ouvrir "
    "la page."
)


@pytest.fixture(autouse=True)
def no_notification_counted_yet(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts a day of its own: the watch has told nothing yet."""
    monkeypatch.setattr(watch_service_module, "watch_notifier", WatchNotifier())


@pytest.fixture
def notifications_sent(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """What the watch hands to the core's notifications, instead of a real push."""
    sent: list[dict[str, Any]] = []

    async def notify(_self: NotificationService, **notification: Any) -> None:
        sent.append(notification)

    monkeypatch.setattr(NotificationService, "notify_module_event", notify)
    return sent


@pytest.fixture
def site_answers(monkeypatch: pytest.MonkeyPatch) -> dict[str, SiteReading]:
    """What each site answers when the watch reads it again; a host missing here is a healthy site."""
    answer_by_host: dict[str, SiteReading] = {}

    async def read(_self: SiteReader, website: str) -> SiteReading:
        host: str = website.split("//")[-1].strip("/").removeprefix("www.")
        return answer_by_host.get(host, reading_of(host))

    monkeypatch.setattr(SiteReader, "read", read)
    return answer_by_host


def _site_last_checked_a_month_ago(
    db: Session, owner: User, business_name: str, host: str, **first_check_facts: Any
) -> SiteCareSite:
    """A site of the module whose only check, a month old, read a healthy home page but for ``first_check_facts``."""
    site = SiteCareSite(
        user_id=owner.id,
        business_name=business_name,
        trade="paysagiste",
        city="Reims",
        website=f"https://www.{host}/",
        host=host,
        status="",
        page_slug=site_service.new_page_slug(business_name),
        search_text=site_service.search_text_of(business_name, "Reims", host),
    )
    db.add(site)
    asyncio.run(
        site_service.apply_reading(
            db, site, reading_of(host, **first_check_facts), owner_settings_service.get(db, owner.id)
        )
    )
    site.checked_at = naive_utc_now() - timedelta(days=30)
    db.commit()
    return site


def _make_due_again(db: Session, site: SiteCareSite) -> None:
    """Age a site's check, as if a week had passed since the watch last read it."""
    db.refresh(site)
    site.checked_at = naive_utc_now() - timedelta(days=30)
    db.commit()


def _run_watch_pass() -> None:
    """One pass of the watch, without waiting for the minutes between two passes."""
    watch_service._next_pass_after = 0.0
    asyncio.run(watch_service.recheck_due_sites())


def _event_kinds(db: Session, site: SiteCareSite) -> list[str]:
    """The kinds of the changes recorded on a site, oldest first."""
    return list(
        db.execute(
            select(SiteCareWatchEvent.kind).where(SiteCareWatchEvent.site_id == site.id).order_by(SiteCareWatchEvent.id)
        ).scalars()
    )


@pytest.mark.usefixtures("site_care_module_switched_on", "background_sessions")
class TestWatchNotifications:
    def test_a_site_found_hacked_is_told_at_once(
        self,
        db: Session,
        owner: User,
        site_answers: dict[str, SiteReading],
        notifications_sent: list[dict[str, Any]],
    ) -> None:
        site = _site_last_checked_a_month_ago(db, owner, "Bellanger Électricité", "bellanger-electricite.test")
        site_answers["bellanger-electricite.test"] = reading_of(
            "bellanger-electricite.test", gambling_links=["bahis.example"], has_hidden_gambling_link=True
        )

        _run_watch_pass()

        assert notifications_sent == [
            {
                "user_id": owner.id,
                "category": "site-care",
                "level": "warning",
                "title": "Bellanger Électricité",
                "body": (
                    f"{_TAG} · site piraté. Des liens cachés vers des casinos sont apparus sur sa page d’accueil."
                ),
                "url": f"/dashboard/site-care/sites/{site.id}",
                "tag": f"site-care-watch-{site.id}",
            }
        ]

    def test_a_point_that_got_worse_is_told_once(
        self,
        db: Session,
        owner: User,
        site_answers: dict[str, SiteReading],
        notifications_sent: list[dict[str, Any]],
    ) -> None:
        site = _site_last_checked_a_month_ago(db, owner, "Jardins Guillot", "jardins-guillot.test")
        site_answers["jardins-guillot.test"] = reading_of("jardins-guillot.test", https="invalid_certificate")

        _run_watch_pass()
        _make_due_again(db, site)
        _run_watch_pass()

        assert [(sent["title"], sent["level"], sent["body"], sent["url"]) for sent in notifications_sent] == [
            (
                "Jardins Guillot",
                "info",
                f"{_TAG} · nouveau point à corriger. {_INVALID_CERTIFICATE_FACT}",
                f"/dashboard/site-care/sites/{site.id}",
            )
        ]

    def test_a_site_gets_one_notification_whatever_got_worse_and_a_hack_comes_first(
        self,
        db: Session,
        owner: User,
        site_answers: dict[str, SiteReading],
        notifications_sent: list[dict[str, Any]],
    ) -> None:
        _site_last_checked_a_month_ago(db, owner, "Jardins Guillot", "jardins-guillot.test")
        _site_last_checked_a_month_ago(db, owner, "Bellanger Électricité", "bellanger-electricite.test")
        site_answers["jardins-guillot.test"] = reading_of(
            "jardins-guillot.test", https="invalid_certificate", powered_by="PHP/7.4.33"
        )
        site_answers["bellanger-electricite.test"] = reading_of(
            "bellanger-electricite.test",
            https="invalid_certificate",
            gambling_links=["bahis.example"],
            has_hidden_gambling_link=True,
        )

        _run_watch_pass()

        assert [(sent["title"], sent["body"].removeprefix(f"{_TAG} · ")) for sent in notifications_sent] == [
            (
                "Bellanger Électricité",
                "site piraté. Des liens cachés vers des casinos sont apparus sur sa page d’accueil.",
            ),
            (
                "Jardins Guillot",
                f"2 nouveaux points à corriger, à commencer par celui-ci. {_INVALID_CERTIFICATE_FACT}",
            ),
        ]

    def test_a_point_already_to_fix_before_an_unreadable_check_is_not_told_as_new(
        self,
        db: Session,
        owner: User,
        site_answers: dict[str, SiteReading],
        notifications_sent: list[dict[str, Any]],
    ) -> None:
        site = _site_last_checked_a_month_ago(db, owner, "Jardins Guillot", "jardins-guillot.test")
        site_answers["jardins-guillot.test"] = reading_of("jardins-guillot.test", powered_by="PHP/7.4.33")
        _run_watch_pass()
        told_when_it_got_worse: int = len(notifications_sent)
        _make_due_again(db, site)
        site_answers["jardins-guillot.test"] = SiteReading(
            host="jardins-guillot.test", read_at=CHECK_DAY, error="ConnectError"
        )
        _run_watch_pass()
        _make_due_again(db, site)
        site_answers["jardins-guillot.test"] = reading_of("jardins-guillot.test", powered_by="PHP/7.4.33")

        _run_watch_pass()

        assert (told_when_it_got_worse, len(notifications_sent)) == (1, 1)
        assert _event_kinds(db, site) == ["worse", "unreachable"]

    def test_a_hacked_site_is_told_once_even_across_an_unreadable_check(
        self,
        db: Session,
        owner: User,
        site_answers: dict[str, SiteReading],
        notifications_sent: list[dict[str, Any]],
    ) -> None:
        host: str = "bellanger-electricite.test"
        hacked: SiteReading = reading_of(host, gambling_links=["bahis.example"], has_hidden_gambling_link=True)
        unreadable: SiteReading = SiteReading(host=host, read_at=CHECK_DAY, error="ConnectError")
        site = _site_last_checked_a_month_ago(db, owner, "Bellanger Électricité", host)

        for answer in (unreadable, hacked, unreadable, hacked):
            site_answers[host] = answer
            _run_watch_pass()
            _make_due_again(db, site)

        assert [sent["title"] for sent in notifications_sent] == ["Bellanger Électricité"]
        assert _event_kinds(db, site) == ["unreachable", "hacked", "unreachable"]

    def test_past_the_day_s_count_one_notification_sends_to_the_watch_page(
        self,
        db: Session,
        owner: User,
        site_answers: dict[str, SiteReading],
        notifications_sent: list[dict[str, Any]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        hosts: list[str] = [f"garage-{number}.test" for number in range(1, 8)]
        for number, host in enumerate(hosts, start=1):
            _site_last_checked_a_month_ago(db, owner, f"Garage {number}", host)
            site_answers[host] = reading_of(host, powered_by="PHP/7.4.33")

        for _ in range(3):
            _run_watch_pass()
        told_the_first_day: list[tuple[str, str]] = [(sent["title"], sent["url"]) for sent in notifications_sent]
        _site_last_checked_a_month_ago(db, owner, "Garage 8", "garage-8.test")
        site_answers["garage-8.test"] = reading_of("garage-8.test", powered_by="PHP/7.4.33")
        the_next_day: datetime = naive_utc_now() + timedelta(days=1)
        monkeypatch.setattr(watch_service_module, "naive_utc_now", lambda: the_next_day)
        _run_watch_pass()

        assert [title for title, _ in told_the_first_day] == [
            "Garage 1",
            "Garage 2",
            "Garage 3",
            "Garage 4",
            "Garage 5",
            "D’autres points à corriger",
        ]
        assert told_the_first_day[-1][1] == "/dashboard/site-care/watch"
        assert notifications_sent[5]["body"] == (
            f"{_TAG} · plus de 5 sites en ont un nouveau aujourd’hui. La suite est sur la page Veille."
        )
        assert [sent["title"] for sent in notifications_sent[6:]] == ["Garage 8"]
