"""
The watch: what just changed on the owner's sites and the dates coming up, each a reason to write today.

It also keeps the checks fresh: the background loop reads again, a few at a time, the sites whose check is old.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import ClassVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.database import SessionLocal

from devleadhunter_site_care.catalog import KIND_LABELS, IssueKind, PointKey, PointState, SiteStatus, WatchEventKind
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.models.watch_event import SiteCareWatchEvent
from devleadhunter_site_care.services.owner_settings_service import owner_settings_service
from devleadhunter_site_care.services.site_points import FrenchDates, SitePoint
from devleadhunter_site_care.services.site_reader import SiteReader, SiteReading
from devleadhunter_site_care.services.site_service import site_service
from devleadhunter_site_care.services.watch_notifier import WatchNotification, watch_notifier

logger = logging.getLogger(__name__)

# A change a check noted, with the site it was noted on.
NotedChange = tuple[SiteCareWatchEvent, SiteCareSite]


@dataclass
class WatchLine:
    """
    One line of the watch page.

    Attributes:
        key: A stable identifier of the line.
        kind: The kind of issue, which picks the icon.
        tone: ``red``, ``amber`` or ``neutral``.
        title: What happened.
        detail: The explanation.
        consequence: What the date changes for its sites, without their count (a date's line only).
        when_label: When it was seen, or how far the date is.
        site_count: How many sites the line is about.
        action_label: The wording of its button.
        site_id: The single site to open, None when the line is about several.
        tab: The tab of « Mes prospects » that holds those sites.
        kind_filter: The kind of issue to filter that tab on.
    """

    key: str
    kind: IssueKind
    tone: str
    title: str
    detail: str
    when_label: str
    site_count: int
    action_label: str
    site_id: int | None = None
    tab: str | None = None
    kind_filter: str | None = None
    consequence: str = ""


@dataclass(frozen=True)
class WatchSiteChange:
    """
    What the last readings found on one site that the reading before had not.

    Attributes:
        key: A stable identifier of the change.
        site: The site.
        kind: The kind of issue, which picks the icon and the colour of the tag.
        kind_label: The word of the tag (« Site piraté », « Site disparu »).
        sentence: What was seen, in one short sentence.
        tech: The technology to name next to the tag (« PHP 7.4 »), empty when there is none.
        seen_at: When the reading saw it.
    """

    key: str
    site: SiteCareSite
    kind: IssueKind
    kind_label: str
    sentence: str
    tech: str
    seen_at: datetime


@dataclass(frozen=True)
class WatchDate:
    """
    A date after which some sites will have a problem.

    Attributes:
        key: A stable identifier of the date (« php-8.2 », « certificates »), which « Mes prospects » filters on.
        days_left: How many days are left before the nearest of its sites is concerned.
        line: Its wording.
        sites: The sites concerned.
    """

    key: str
    days_left: int
    line: WatchLine
    sites: list[SiteCareSite]


class WatchService:
    """Builds the watch page and refreshes the old checks."""

    _RECENT_DAYS: ClassVar[int] = 7
    _RECHECK_AFTER_DAYS: ClassVar[int] = 7
    _SITES_PER_PASS: ClassVar[int] = 3
    _SECONDS_BETWEEN_PASSES: ClassVar[float] = 300.0
    _CERTIFICATES_KEY: ClassVar[str] = "certificates"
    _HACKED_SENTENCE: ClassVar[str] = "Des liens cachés vers des casinos sur la page d’accueil"
    _GONE_LABEL: ClassVar[str] = "Site disparu"
    _GONE_SENTENCE: ClassVar[str] = "Son adresse ne mène plus nulle part"

    def __init__(self) -> None:
        self._next_pass_after: float = 0.0

    def recent_changes(self, noted_changes: list[NotedChange], now: datetime) -> list[WatchLine]:
        """
        The changes of the last days as lines, the way the applications before v1.6.0 list them.

        Args:
            noted_changes: The changes that still hold, from :meth:`changes_that_still_hold`.
            now: The current instant (naive UTC).

        Returns:
            Hacked sites one by one, then the sites that stopped answering together, then the points that got worse.
        """
        lines: list[WatchLine] = []
        gone: list[NotedChange] = []
        for event, site in noted_changes:
            if event.kind == WatchEventKind.UNREACHABLE.value:
                gone.append((event, site))
            elif event.kind == WatchEventKind.HACKED.value:
                lines.append(self._hacked_line(event, site, now))
            else:
                worse: WatchLine | None = self._worse_line(event, site, now)
                if worse is not None:
                    lines.append(worse)
        if gone:
            lines.append(self._gone_line(gone, now))
        return sorted(lines, key=lambda line: (line.tone != "red", line.kind != IssueKind.HACK))

    def new_issues(self, noted_changes: list[NotedChange]) -> list[WatchSiteChange]:
        """
        The sites on which the last readings found an issue the reading before had not: a hack, a point to fix.

        Args:
            noted_changes: The changes that still hold, from :meth:`changes_that_still_hold`.

        Returns:
            One change per site and point, the hacked sites first, then the latest seen first.
        """
        changes: list[WatchSiteChange] = []
        for event, site in noted_changes:
            if event.kind == WatchEventKind.HACKED.value:
                changes.append(
                    WatchSiteChange(
                        key=f"hacked-{site.id}",
                        site=site,
                        kind=IssueKind.HACK,
                        kind_label=KIND_LABELS[IssueKind.HACK],
                        sentence=self._HACKED_SENTENCE,
                        tech="",
                        seen_at=event.created_at,
                    )
                )
            elif event.kind == WatchEventKind.WORSE.value:
                point: SitePoint | None = self._point_to_fix(site, event.point_key)
                if point is not None:
                    changes.append(
                        WatchSiteChange(
                            key=f"worse-{site.id}-{point.key.value}",
                            site=site,
                            kind=point.kind or IssueKind.REVIEW,
                            kind_label=KIND_LABELS[point.kind or IssueKind.REVIEW],
                            sentence=point.sentence or point.fact,
                            tech=point.tech,
                            seen_at=event.created_at,
                        )
                    )
        return sorted(changes, key=lambda change: change.kind != IssueKind.HACK)

    def gone_sites(self, noted_changes: list[NotedChange]) -> list[WatchSiteChange]:
        """
        The sites that stopped answering since the reading before, and still do not answer.

        Args:
            noted_changes: The changes that still hold, from :meth:`changes_that_still_hold`.

        Returns:
            One change per site, the latest seen first.
        """
        return [
            WatchSiteChange(
                key=f"gone-{site.id}",
                site=site,
                kind=IssueKind.REVIEW,
                kind_label=self._GONE_LABEL,
                sentence=self._GONE_SENTENCE,
                tech="",
                seen_at=event.created_at,
            )
            for event, site in noted_changes
            if event.kind == WatchEventKind.UNREACHABLE.value
        ]

    def upcoming_dates(self, db: Session, user_id: int, now: datetime) -> list[WatchDate]:
        """
        The dates after which some sites will have a problem: a PHP branch's end, certificates that expire.

        Args:
            db: Active database session.
            user_id: The owner.
            now: The current instant (naive UTC).

        Returns:
            One date per PHP branch that ends and one for the certificates that expire, the nearest first.
        """
        sites = db.execute(
            select(SiteCareSite).where(
                SiteCareSite.user_id == user_id,
                SiteCareSite.archived_at.is_(None),
                SiteCareSite.kinds_filter != "",
            )
        ).scalars()
        php_sites: dict[tuple[str, str], list[SiteCareSite]] = defaultdict(list)
        certificate_sites: list[tuple[SiteCareSite, int]] = []
        for site in sites:
            for stored in site.points or []:
                if stored["state"] != PointState.WATCH.value:
                    continue
                point: SitePoint = SitePoint.from_json(stored)
                if point.key == PointKey.PHP and point.data.get("end_iso"):
                    php_sites[(point.data["version"], point.data["end_iso"])].append(site)
                elif point.key == PointKey.HTTPS and point.data.get("variant") == "expiring":
                    certificate_sites.append((site, int(point.data.get("days", 0))))
        dates: list[WatchDate] = []
        today: date = now.date()
        for (version, end_iso), concerned in php_sites.items():
            end: date = date.fromisoformat(end_iso)
            days_left: int = (end - today).days
            dates.append(
                WatchDate(
                    key=f"php-{version}",
                    days_left=days_left,
                    line=self._php_line(version, end, days_left, concerned),
                    sites=concerned,
                )
            )
        if certificate_sites:
            dates.append(
                WatchDate(
                    key=self._CERTIFICATES_KEY,
                    days_left=min(days_left for _, days_left in certificate_sites),
                    line=self._certificate_line(certificate_sites),
                    sites=[site for site, _ in certificate_sites],
                )
            )
        return sorted(dates, key=lambda watch_date: watch_date.days_left)

    def upcoming_date(self, db: Session, user_id: int, key: str, now: datetime) -> WatchDate | None:
        """
        One of the dates coming up, by its key.

        Args:
            db: Active database session.
            user_id: The owner.
            key: The date's key, as the watch page links it.
            now: The current instant (naive UTC).

        Returns:
            The date, or None when no site of the owner is concerned by it any more.
        """
        return next((each for each in self.upcoming_dates(db, user_id, now) if each.key == key), None)

    def followed_site_count(self, db: Session, user_id: int, now: datetime, *, is_reread_only: bool) -> int:
        """
        How many sites of the owner the watch follows, or how many of them it read again over the last days.

        Args:
            db: Active database session.
            user_id: The owner.
            now: The current instant (naive UTC).
            is_reread_only: Count only the sites whose last check is at most seven days old.

        Returns:
            The count.
        """
        followed = (
            select(func.count())
            .select_from(SiteCareSite)
            .where(SiteCareSite.user_id == user_id, SiteCareSite.archived_at.is_(None))
        )
        if is_reread_only:
            followed = followed.where(SiteCareSite.checked_at >= now - timedelta(days=self._RECHECK_AFTER_DAYS))
        return int(db.execute(followed).scalar() or 0)

    async def recheck_due_sites(self) -> None:
        """Read again a few sites whose check is old, at most once every few minutes, and tell what that found."""
        now_monotonic: float = time.monotonic()
        if now_monotonic < self._next_pass_after:
            return
        self._next_pass_after = now_monotonic + self._SECONDS_BETWEEN_PASSES
        with SessionLocal() as db:
            due: list[tuple[int, str]] = [
                (site_id, website)
                for site_id, website in db.execute(
                    select(SiteCareSite.id, SiteCareSite.website)
                    .where(
                        SiteCareSite.archived_at.is_(None),
                        SiteCareSite.checked_at < naive_utc_now() - timedelta(days=self._RECHECK_AFTER_DAYS),
                    )
                    .order_by(SiteCareSite.checked_at)
                    .limit(self._SITES_PER_PASS)
                ).all()
            ]
        if not due:
            return
        async with SiteReader() as reader:
            readings: list[SiteReading] = [await reader.read(website) for _, website in due]
        with SessionLocal() as db:
            event_id_before_pass: int = watch_notifier.latest_event_id(db)
            for (site_id, _), reading in zip(due, readings, strict=True):
                site: SiteCareSite | None = db.get(SiteCareSite, site_id)
                if site is None or site.archived_at is not None:
                    continue
                await site_service.apply_reading(db, site, reading, owner_settings_service.get(db, site.user_id))
            db.commit()
            pass_notifications: list[WatchNotification] = watch_notifier.notifications_of_pass(
                db, [site_id for site_id, _ in due], event_id_before_pass, naive_utc_now()
            )
        await watch_notifier.send(pass_notifications)

    def changes_that_still_hold(self, db: Session, user_id: int, now: datetime) -> list[NotedChange]:
        """
        The changes of the last days that still hold: a site still hacked, still silent, a point still to fix.

        Args:
            db: Active database session.
            user_id: The owner.
            now: The current instant (naive UTC).

        Returns:
            Each change once per site and point, the latest first.
        """
        rows = db.execute(
            select(SiteCareWatchEvent, SiteCareSite)
            .join(SiteCareSite, SiteCareSite.id == SiteCareWatchEvent.site_id)
            .where(
                SiteCareWatchEvent.user_id == user_id,
                SiteCareWatchEvent.created_at >= now - timedelta(days=self._RECENT_DAYS),
                SiteCareSite.archived_at.is_(None),
            )
            .order_by(SiteCareWatchEvent.created_at.desc())
        ).all()
        fresh: list[NotedChange] = []
        seen: set[tuple[str, int, str | None]] = set()
        for event, site in rows:
            mark: tuple[str, int, str | None] = (event.kind, site.id, event.point_key)
            if mark in seen:
                continue
            seen.add(mark)
            if event.kind == WatchEventKind.UNREACHABLE.value:
                is_still_holding: bool = site.status == SiteStatus.UNREACHABLE.value
            elif event.kind == WatchEventKind.HACKED.value:
                is_still_holding = self._is_still_hacked(site)
            else:
                is_still_holding = self._point_to_fix(site, event.point_key) is not None
            if is_still_holding:
                fresh.append((event, site))
        return fresh

    @staticmethod
    def _point_to_fix(site: SiteCareSite, point_key: str | None) -> SitePoint | None:
        """A point of the site's last check, None when it is no longer to fix."""
        stored: dict | None = next((point for point in site.points or [] if point["key"] == point_key), None)
        if stored is None or stored["state"] != PointState.FIX.value:
            return None
        return SitePoint.from_json(stored)

    @staticmethod
    def seen_label(moment: datetime, now: datetime) -> str:
        """« Vu aujourd’hui », « Vu hier » or « Vu il y a 3 jours »."""
        days: int = (now.date() - moment.date()).days
        if days <= 0:
            return "Vu aujourd’hui"
        return "Vu hier" if days == 1 else f"Vu il y a {days} jours"

    @staticmethod
    def _place(site: SiteCareSite) -> str:
        """A business with its city: « Bellanger Électricité, à Mulhouse »."""
        return f"{site.business_name}, à {site.city}" if site.city else site.business_name

    @staticmethod
    def _is_still_hacked(site: SiteCareSite) -> bool:
        """Whether the site's last check still finds hidden gambling links (a later check may have ruled it out)."""
        return any(
            point["key"] == PointKey.HACKED.value and point["state"] == PointState.FIX.value
            for point in site.points or []
        )

    def _hacked_line(self, event: SiteCareWatchEvent, site: SiteCareSite, now: datetime) -> WatchLine:
        return WatchLine(
            key=f"hacked-{site.id}",
            kind=IssueKind.HACK,
            tone="red",
            title="Un site piraté",
            detail=f"{self._place(site)} : des liens cachés vers des casinos sur la page d’accueil.",
            when_label=self.seen_label(event.created_at, now),
            site_count=1,
            action_label="Voir ce prospect",
            site_id=site.id,
        )

    def _worse_line(self, event: SiteCareWatchEvent, site: SiteCareSite, now: datetime) -> WatchLine | None:
        point: SitePoint | None = self._point_to_fix(site, event.point_key)
        if point is None:
            return None
        return WatchLine(
            key=f"worse-{site.id}-{point.key.value}",
            kind=point.kind or IssueKind.REVIEW,
            tone="red",
            title="Un nouveau point à corriger",
            detail=f"{self._place(site)} : {point.fact[:1].lower()}{point.fact[1:]}",
            when_label=self.seen_label(event.created_at, now),
            site_count=1,
            action_label="Voir ce prospect",
            site_id=site.id,
        )

    def _gone_line(self, gone: list[NotedChange], now: datetime) -> WatchLine:
        count: int = len(gone)
        latest: datetime = max(event.created_at for event, _ in gone)
        if count == 1:
            site: SiteCareSite = gone[0][1]
            return WatchLine(
                key=f"gone-{site.id}",
                kind=IssueKind.REVIEW,
                tone="neutral",
                title="Un site ne répond plus",
                detail=f"{self._place(site)} : son adresse ne mène plus nulle part. Cette entreprise n’a plus de site.",
                when_label=self.seen_label(latest, now),
                site_count=1,
                action_label="Voir ce prospect",
                site_id=site.id,
            )
        return WatchLine(
            key="gone",
            kind=IssueKind.REVIEW,
            tone="neutral",
            title=f"{count} sites ne répondent plus",
            detail="Leur adresse ne mène plus nulle part. Ces entreprises n’ont plus de site.",
            when_label=self.seen_label(latest, now),
            site_count=count,
            action_label=f"Voir ces {count} prospects",
            tab="review",
        )

    @staticmethod
    def _php_line(version: str, end: date, days_left: int, sites: list[SiteCareSite]) -> WatchLine:
        count: int = len(sites)
        several: bool = count > 1
        return WatchLine(
            key=f"php-{version}",
            kind=IssueKind.LATE,
            tone="amber",
            title=f"PHP {version} s’arrête le {FrenchDates.full(end)}",
            detail=(
                f"{count} sites de vos prospects tournent encore avec PHP {version}. Après cette date, ils ne "
                "reçoivent plus de correctifs de sécurité."
                if several
                else f"{sites[0].business_name} tourne encore avec PHP {version}. Après cette date, son site ne "
                "reçoit plus de correctifs de sécurité."
            ),
            when_label=f"Dans {days_left} jours" if days_left > 1 else "Demain",
            site_count=count,
            action_label=f"Voir ces {count} prospects" if several else "Voir ce prospect",
            site_id=None if several else sites[0].id,
            tab="all" if several else None,
            kind_filter=IssueKind.LATE.value if several else None,
            consequence=(
                "Après cette date, ces sites ne reçoivent plus de correctifs de sécurité."
                if several
                else "Après cette date, son site ne reçoit plus de correctifs de sécurité."
            ),
        )

    @staticmethod
    def _certificate_line(sites: list[tuple[SiteCareSite, int]]) -> WatchLine:
        count: int = len(sites)
        days: list[int] = sorted(days_left for _, days_left in sites)
        several: bool = count > 1
        span: str = f"Dans {days[0]} à {days[-1]} jours" if days[0] != days[-1] else f"Dans {days[0]} jours"
        return WatchLine(
            key=WatchService._CERTIFICATES_KEY,
            kind=IssueKind.SECURITY,
            tone="amber",
            title=(
                f"{count} cadenas de sécurité expirent bientôt" if several else "Un cadenas de sécurité expire bientôt"
            ),
            detail=(
                "Ils n’ont pas été renouvelés à temps. Le jour de l’expiration, le navigateur affichera un "
                "avertissement à leurs visiteurs."
                if several
                else f"Celui de {sites[0][0].business_name} n’a pas été renouvelé à temps. Le jour de l’expiration, "
                "le navigateur affichera un avertissement à ses visiteurs."
            ),
            when_label=span,
            site_count=count,
            action_label=f"Voir ces {count} prospects" if several else "Voir ce prospect",
            site_id=None if several else sites[0][0].id,
            tab="all" if several else None,
            kind_filter=IssueKind.SECURITY.value if several else None,
            consequence=(
                "Ils n’ont pas été renouvelés à temps. Le jour de l’expiration, le navigateur affichera un "
                "avertissement à leurs visiteurs."
                if several
                else "Il n’a pas été renouvelé à temps. Le jour de l’expiration, le navigateur affichera un "
                "avertissement à ses visiteurs."
            ),
        )


watch_service = WatchService()
