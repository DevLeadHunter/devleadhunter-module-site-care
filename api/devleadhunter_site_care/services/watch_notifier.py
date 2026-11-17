"""
What the watch tells the owner at once: a site the background check just found hacked, or with a new point to fix.

The watch page keeps every change; a notification carries the ones worth a message today. A hacked site is always
told. A point that got worse is told a few times a day at most: the day a PHP branch stops being fixed, hundreds of
sites get worse within the week, so past that count one last notification sends the owner to the watch page.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.notification_service import notification_service

from devleadhunter_site_care import MODULE_KEY, NOTIFICATION_TAG
from devleadhunter_site_care.catalog import FIX_LEAD_ORDER, PointState, WatchEventKind
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.models.watch_event import SiteCareWatchEvent
from devleadhunter_site_care.services.site_points import SitePoint

logger = logging.getLogger(__name__)

WATCH_PAGE_URL: str = "/dashboard/site-care/watch"


@dataclass(frozen=True)
class WatchNotification:
    """
    One notification of the watch, worded and addressed.

    Attributes:
        user_id: The owner it goes to.
        level: The core's visual level (``warning`` for a hack, ``info`` otherwise).
        title: The business, or what happened to several.
        body: What the check found, after the module's tag.
        url: The dashboard page it opens.
        tag: The push tag: a later notification with the same tag replaces it on the device.
    """

    user_id: int
    level: str
    title: str
    body: str
    url: str
    tag: str


class WatchNotifier:
    """Words what a pass of the watch found, counts the day's notifications and hands them to the core."""

    WORSE_NOTIFICATIONS_PER_DAY: ClassVar[int] = 5
    _OWNER_TIME_ZONE: ClassVar[ZoneInfo] = ZoneInfo("Europe/Paris")
    _LAST_LEAD_RANK: ClassVar[int] = len(FIX_LEAD_ORDER)

    def __init__(self) -> None:
        self._counted_day: date | None = None
        self._worse_site_count_by_owner: dict[int, int] = {}

    @staticmethod
    def latest_event_id(db: Session) -> int:
        """
        The last change the watch recorded, to tell apart what a pass adds.

        Args:
            db: Active database session.

        Returns:
            Its identifier, 0 when nothing was ever recorded.
        """
        return int(db.execute(select(func.max(SiteCareWatchEvent.id))).scalar() or 0)

    def notifications_of_pass(
        self, db: Session, site_ids: Sequence[int], event_id_before_pass: int, now: datetime
    ) -> list[WatchNotification]:
        """
        What a pass of the watch found that is worth telling, counted in the day's notifications.

        Args:
            db: Active database session, the pass committed.
            site_ids: The sites the pass read again.
            event_id_before_pass: What :meth:`latest_event_id` gave before the pass stored its checks.
            now: The current instant (naive UTC).

        Returns:
            One notification per hacked site, then one per site that got worse while the day's count allows it.
        """
        event_kinds_by_site: dict[int, set[str]] = defaultdict(set)
        worse_point_keys_by_site: dict[int, set[str]] = defaultdict(set)
        for site_id, kind, point_key in db.execute(
            select(SiteCareWatchEvent.site_id, SiteCareWatchEvent.kind, SiteCareWatchEvent.point_key).where(
                SiteCareWatchEvent.id > event_id_before_pass,
                SiteCareWatchEvent.site_id.in_(site_ids),
                SiteCareWatchEvent.kind.in_((WatchEventKind.HACKED.value, WatchEventKind.WORSE.value)),
            )
        ).all():
            event_kinds_by_site[site_id].add(kind)
            if kind == WatchEventKind.WORSE.value and point_key is not None:
                worse_point_keys_by_site[site_id].add(point_key)
        if not event_kinds_by_site:
            return []
        changed_sites: list[SiteCareSite] = list(
            db.execute(
                select(SiteCareSite)
                .where(SiteCareSite.id.in_(list(event_kinds_by_site)), SiteCareSite.archived_at.is_(None))
                .order_by(SiteCareSite.id)
            ).scalars()
        )
        hacked_site_ids: set[int] = {
            site_id for site_id, kinds in event_kinds_by_site.items() if WatchEventKind.HACKED.value in kinds
        }
        notifications: list[WatchNotification] = [
            self._hacked_notification(site) for site in changed_sites if site.id in hacked_site_ids
        ]
        today: date = self._owner_day(now)
        for site in changed_sites:
            if site.id in hacked_site_ids:
                continue
            worse_points: list[SitePoint] = self._points_still_to_fix(site, worse_point_keys_by_site[site.id])
            if not worse_points:
                continue
            notification: WatchNotification | None = self._worse_notification_within_the_day(site, worse_points, today)
            if notification is not None:
                notifications.append(notification)
        return notifications

    async def send(self, notifications: Sequence[WatchNotification]) -> None:
        """
        Hand the notifications to the core, one at a time; one that fails is logged and the others still leave.

        Args:
            notifications: What :meth:`notifications_of_pass` returned.
        """
        for notification in notifications:
            try:
                await notification_service.notify_module_event(
                    user_id=notification.user_id,
                    category=MODULE_KEY,
                    level=notification.level,
                    title=notification.title,
                    body=notification.body,
                    url=notification.url,
                    tag=notification.tag,
                )
            except Exception:
                logger.warning("[SiteCare] could not send the watch notification %s", notification.tag, exc_info=True)

    @classmethod
    def _owner_day(cls, now: datetime) -> date:
        """The day the owner lives ``now`` (naive UTC) in: the day's count starts again at his midnight."""
        return now.replace(tzinfo=UTC).astimezone(cls._OWNER_TIME_ZONE).date()

    @classmethod
    def _points_still_to_fix(cls, site: SiteCareSite, point_keys: set[str]) -> list[SitePoint]:
        """The points of a site that got worse and are still to fix, the most pressing first."""
        points: list[SitePoint] = [
            SitePoint.from_json(stored)
            for stored in site.points or []
            if stored["key"] in point_keys and stored["state"] == PointState.FIX.value
        ]
        return sorted(
            points,
            key=lambda point: FIX_LEAD_ORDER.index(point.key) if point.key in FIX_LEAD_ORDER else cls._LAST_LEAD_RANK,
        )

    @staticmethod
    def _site_url(site: SiteCareSite) -> str:
        """The dashboard page of a site."""
        return f"/dashboard/site-care/sites/{site.id}"

    def _hacked_notification(self, site: SiteCareSite) -> WatchNotification:
        """The notification of a site the watch just found hacked."""
        return WatchNotification(
            user_id=site.user_id,
            level="warning",
            title=site.business_name,
            body=(
                f"{NOTIFICATION_TAG} · site piraté. Des liens cachés vers des casinos sont apparus sur sa page d’accueil."
            ),
            url=self._site_url(site),
            tag=f"site-care-watch-{site.id}",
        )

    def _worse_notification_within_the_day(
        self, site: SiteCareSite, worse_points: list[SitePoint], today: date
    ) -> WatchNotification | None:
        """
        The notification of a site that got worse, while the owner's count of the day allows one.

        Args:
            site: The site.
            worse_points: Its points that got worse, the most pressing first.
            today: The owner's day.

        Returns:
            The site's own notification up to the day's count, then once the one that sends to the watch page,
            then None until the next day.
        """
        if self._counted_day != today:
            self._counted_day = today
            self._worse_site_count_by_owner = {}
        worse_site_count: int = self._worse_site_count_by_owner.get(site.user_id, 0) + 1
        self._worse_site_count_by_owner[site.user_id] = worse_site_count
        count_sent_to_the_watch_page: int = self.WORSE_NOTIFICATIONS_PER_DAY + 1
        if worse_site_count > count_sent_to_the_watch_page:
            return None
        if worse_site_count == count_sent_to_the_watch_page:
            return WatchNotification(
                user_id=site.user_id,
                level="info",
                title="D’autres points à corriger",
                body=(
                    f"{NOTIFICATION_TAG} · plus de {self.WORSE_NOTIFICATIONS_PER_DAY} sites en ont un nouveau "
                    "aujourd’hui. La suite est sur la page Veille."
                ),
                url=WATCH_PAGE_URL,
                tag="site-care-watch-more",
            )
        most_pressing_fact: str = worse_points[0].fact
        return WatchNotification(
            user_id=site.user_id,
            level="info",
            title=site.business_name,
            body=(
                f"{NOTIFICATION_TAG} · nouveau point à corriger. {most_pressing_fact}"
                if len(worse_points) == 1
                else f"{NOTIFICATION_TAG} · {len(worse_points)} nouveaux points à corriger, à commencer par "
                f"celui-ci. {most_pressing_fact}"
            ),
            url=self._site_url(site),
            tag=f"site-care-watch-{site.id}",
        )


watch_notifier = WatchNotifier()
