"""The sites of an owner: their list, their check, their email address."""

from __future__ import annotations

import re
import secrets
import unicodedata
from dataclasses import dataclass, field

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now

from devleadhunter_site_care.catalog import (
    FIX_LEAD_ORDER,
    WATCH_LEAD_ORDER,
    PointKey,
    PointState,
    SiteStatus,
    SiteTab,
)
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.models.watch_event import SiteCareWatchEvent
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings
from devleadhunter_site_care.services.site_points import SitePoint, SitePointReader
from devleadhunter_site_care.services.site_reader import HomePageFacts, SiteAddress, SiteReader, SiteReading
from devleadhunter_site_care.services.site_summary import SiteSummarizer, SiteSummary, WritingRules
from devleadhunter_site_care.services.wordpress_releases import wordpress_releases

_UNREAD_STATUSES: tuple[str, ...] = (SiteStatus.UNREACHABLE.value, SiteStatus.UNREADABLE.value)
_NO_LEAD_RANK: int = 999
_EMAIL_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


class SiteCareError(ValueError):
    """Something the owner asked for cannot be done; the message says why, in French."""


@dataclass
class SiteListing:
    """
    One page of « Mes prospects ».

    Attributes:
        total_count: Every site of the owner.
        with_email_count: Those with an address.
        to_fix_count: Those that deserve a message.
        written_count: Those already written to.
        tab_counts: How many sites each tab holds.
        trades: The trade keys present, for the filter.
        matching_count: How many sites the tab and the filters match.
        sites: The page's sites.
    """

    total_count: int = 0
    with_email_count: int = 0
    to_fix_count: int = 0
    written_count: int = 0
    tab_counts: dict[SiteTab, int] = field(default_factory=dict)
    trades: list[str] = field(default_factory=list)
    matching_count: int = 0
    sites: list[SiteCareSite] = field(default_factory=list)


class SiteService:
    """Lists, checks and edits the sites of an owner."""

    def list_sites(
        self,
        db: Session,
        user_id: int,
        *,
        tab: SiteTab,
        trade: str | None,
        kind: str | None,
        text: str | None,
        limit: int,
        offset: int,
    ) -> SiteListing:
        """
        A page of the owner's sites.

        Args:
            db: Active database session.
            user_id: The owner.
            tab: The tab asked for.
            trade: A trade key to keep, None for every trade.
            kind: A kind of issue to keep, None for every kind.
            text: Words of a name, a city or an address to look for.
            limit: How many sites at most.
            offset: How many to skip.

        Returns:
            The counts of the whole list and the page asked for, the most pressing sites first.
        """
        owned: ColumnElement[bool] = and_(SiteCareSite.user_id == user_id, SiteCareSite.archived_at.is_(None))
        listing: SiteListing = SiteListing(
            total_count=self._count(db, owned),
            with_email_count=self._count(db, and_(owned, SiteCareSite.email.is_not(None))),
            to_fix_count=self._count(db, and_(owned, SiteCareSite.status == SiteStatus.TO_WRITE.value)),
            written_count=self._count(db, and_(owned, SiteCareSite.written_at.is_not(None))),
            tab_counts={each: self._count(db, and_(owned, self.tab_filter(each))) for each in SiteTab},
            trades=sorted(
                trade_key
                for trade_key in db.execute(select(SiteCareSite.trade).where(owned).distinct()).scalars()
                if trade_key
            ),
        )
        matching: ColumnElement[bool] = and_(owned, self.tab_filter(tab))
        if trade:
            matching = and_(matching, SiteCareSite.trade == trade)
        if kind:
            matching = and_(matching, SiteCareSite.kinds_filter.like(f"%,{kind},%"))
        if text and text.strip():
            matching = and_(matching, SiteCareSite.search_text.like(f"%{self.folded(text)}%"))
        listing.matching_count = self._count(db, matching)
        listing.sites = list(
            db.execute(
                select(SiteCareSite)
                .where(matching)
                .order_by(SiteCareSite.lead_rank, SiteCareSite.id)
                .limit(limit)
                .offset(offset)
            ).scalars()
        )
        return listing

    def get(self, db: Session, user_id: int, site_id: int) -> SiteCareSite | None:
        """
        One of the owner's sites.

        Args:
            db: Active database session.
            user_id: The owner.
            site_id: The site.

        Returns:
            The site, or None when it is not his or was taken out of the list.
        """
        site: SiteCareSite | None = db.get(SiteCareSite, site_id)
        if site is None or site.user_id != user_id or site.archived_at is not None:
            return None
        return site

    @staticmethod
    def tab_of(site: SiteCareSite) -> SiteTab:
        """The tab a site falls under."""
        if site.written_at is not None:
            return SiteTab.WRITTEN
        if site.status in _UNREAD_STATUSES:
            return SiteTab.REVIEW
        if site.status == SiteStatus.NOTHING.value:
            return SiteTab.NOTHING
        return SiteTab.TO_WRITE if site.email else SiteTab.NO_EMAIL

    @staticmethod
    def tab_filter(tab: SiteTab) -> ColumnElement[bool]:
        """The same rule as :meth:`tab_of`, as a query filter."""
        if tab == SiteTab.ALL:
            return SiteCareSite.id.is_not(None)
        if tab == SiteTab.WRITTEN:
            return SiteCareSite.written_at.is_not(None)
        not_written: ColumnElement[bool] = SiteCareSite.written_at.is_(None)
        if tab == SiteTab.REVIEW:
            return and_(not_written, SiteCareSite.status.in_(_UNREAD_STATUSES))
        if tab == SiteTab.NOTHING:
            return and_(not_written, SiteCareSite.status == SiteStatus.NOTHING.value)
        deserves_message: ColumnElement[bool] = and_(not_written, SiteCareSite.status == SiteStatus.TO_WRITE.value)
        if tab == SiteTab.TO_WRITE:
            return and_(deserves_message, SiteCareSite.email.is_not(None))
        return and_(deserves_message, SiteCareSite.email.is_(None))

    @staticmethod
    def summary_of(site: SiteCareSite, rules: WritingRules) -> SiteSummary:
        """
        A site's stored check, summed up with the owner's writing rules.

        Args:
            site: The site.
            rules: The owner's choices.

        Returns:
            The summary.
        """
        return SiteSummarizer.summarize(
            [SitePoint.from_json(point) for point in site.points or []],
            rules,
            was_reached=site.status != SiteStatus.UNREACHABLE.value,
            was_read=site.status not in _UNREAD_STATUSES,
        )

    async def apply_reading(
        self, db: Session, site: SiteCareSite, reading: SiteReading, settings: OwnerSettings
    ) -> SiteSummary:
        """
        Store what a check read on a site, and note what changed since the previous check (the caller commits).

        Args:
            db: Active database session.
            site: The site, new or already stored.
            reading: What was just read.
            settings: The owner's settings.

        Returns:
            The check, summed up.
        """
        previous_states: dict[str, str] = {point["key"]: point["state"] for point in site.points or []}
        was_reached_before: bool = bool(site.points) and site.status != SiteStatus.UNREACHABLE.value
        is_first_check: bool = not site.points
        points: list[SitePoint] = SitePointReader(
            today=reading.read_at.date(),
            wordpress_branch=await wordpress_releases.current_branch(),
            listing_phone=site.phone,
        ).points_of(reading)
        summary: SiteSummary = SiteSummarizer.summarize(
            points, settings.writing_rules, was_reached=reading.was_reached, was_read=reading.was_read
        )
        site.points = [point.to_json() for point in points]
        site.reading = reading.to_json()
        site.checked_at = reading.read_at
        self._store_summary(site, summary)
        if site.email is None:
            found: str | None = self.best_email(reading.emails, site.host)
            if found is not None:
                site.email, site.email_source = found, "site"
        self._note_changes(
            db,
            site,
            points,
            previous_states,
            is_first_check=is_first_check,
            stopped_answering=not reading.was_reached and (is_first_check or was_reached_before),
        )
        return summary

    def apply_rules_to_all(self, db: Session, user_id: int, rules: WritingRules) -> None:
        """
        Sum every site of an owner up again after he changed his writing rules.

        Args:
            db: Active database session.
            user_id: The owner.
            rules: His new choices.
        """
        sites = db.execute(
            select(SiteCareSite).where(SiteCareSite.user_id == user_id, SiteCareSite.archived_at.is_(None))
        ).scalars()
        for site in sites:
            if site.status not in _UNREAD_STATUSES:
                self._store_summary(site, self.summary_of(site, rules))
        db.commit()

    async def recheck(self, db: Session, site: SiteCareSite, settings: OwnerSettings) -> None:
        """
        Read a site again and store the new check.

        The database connection is given back while the site is read: a slow site never holds one.

        Args:
            db: Active database session.
            site: The site to check again.
            settings: The owner's settings.
        """
        website: str = site.website
        db.commit()
        async with SiteReader() as reader:
            reading: SiteReading = await reader.read(website)
        db.refresh(site)
        await self.apply_reading(db, site, reading, settings)
        db.commit()

    async def find_email(self, db: Session, site: SiteCareSite) -> bool:
        """
        Look for an email address on the site's home, contact and legal pages.

        Args:
            db: Active database session.
            site: The site without an address.

        Returns:
            True when an address was found and stored.
        """
        website: str = site.website
        host: str = site.host
        db.commit()
        async with SiteReader() as reader:
            reading: SiteReading = await reader.read(website)
            emails: list[str] = list(reading.emails)
            if self.best_email(emails, host) is None and reading.contact_page_urls:
                emails += await reader.read_emails_of_pages(reading.contact_page_urls)
        db.refresh(site)
        found: str | None = self.best_email(emails, host)
        if found is None:
            return False
        site.email, site.email_source = found, "site"
        db.commit()
        return True

    def set_email(self, db: Session, site: SiteCareSite, email: str) -> None:
        """
        Store the address the owner typed for a site.

        Args:
            db: Active database session.
            site: The site.
            email: The address; an empty one removes the site's address.

        Raises:
            SiteCareError: The text is not an email address.
        """
        cleaned: str = email.strip().lower()
        if cleaned and not _EMAIL_PATTERN.match(cleaned):
            raise SiteCareError("Cette adresse e-mail n’est pas valide.")
        site.email, site.email_source = (cleaned, "manual") if cleaned else (None, None)
        db.commit()

    def archive(self, db: Session, site: SiteCareSite) -> None:
        """
        Take a site out of the list. Its host stays known, so no search brings it back.

        Args:
            db: Active database session.
            site: The site.
        """
        site.archived_at = naive_utc_now()
        db.commit()

    @staticmethod
    def best_email(emails: list[str], host: str) -> str | None:
        """
        The address of a business among those its pages show.

        Args:
            emails: The addresses read on the site.
            host: The site's host.

        Returns:
            An address on the site's own domain first, else one on a public mailbox; never a third party's (the
            agency that built the site signs its pages too).
        """
        own_domain: str = SiteAddress.mail_domain_of(host)
        own: list[str] = [email for email in emails if email.split("@")[-1] == own_domain]
        if own:
            return next((email for email in own if email.split("@")[0] in ("contact", "info", "accueil")), own[0])
        return next((email for email in emails if email.split("@")[-1] in HomePageFacts.PUBLIC_MAILBOX_DOMAINS), None)

    @staticmethod
    def folded(text: str) -> str:
        """Text in lower case without accents, the form the list's search compares."""
        plain: str = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
        return re.sub(r"\s+", " ", plain.lower()).strip()

    @classmethod
    def new_page_slug(cls, business_name: str) -> str:
        """
        The address of the page prepared for a business: its name, then a part nobody can guess.

        Args:
            business_name: The business.

        Returns:
            A slug such as « jardins-guillot-x7k2m9qa ».
        """
        name_part: str = re.sub(r"[^a-z0-9]+", "-", cls.folded(business_name)).strip("-")[:60] or "site"
        return f"{name_part}-{secrets.token_hex(4)}"

    @classmethod
    def search_text_of(cls, business_name: str, city: str | None, host: str) -> str:
        """What the list's search field looks into for a site."""
        return cls.folded(f"{business_name} {city or ''} {host}")[:600]

    @staticmethod
    def lead_rank_of(summary: SiteSummary) -> int:
        """How pressing a site's leading point is: fixes first, in the catalogue's lead order."""
        lead: SitePoint | None = summary.lead
        if lead is None:
            return _NO_LEAD_RANK
        if lead.state == PointState.FIX and lead.key in FIX_LEAD_ORDER:
            return FIX_LEAD_ORDER.index(lead.key)
        if lead.key in WATCH_LEAD_ORDER:
            return 100 + WATCH_LEAD_ORDER.index(lead.key)
        return _NO_LEAD_RANK - 1

    def _store_summary(self, site: SiteCareSite, summary: SiteSummary) -> None:
        """Copy onto a site what the list filters and sorts on."""
        site.status = summary.status.value
        site.lead_point = summary.lead.key.value if summary.lead else None
        site.lead_rank = self.lead_rank_of(summary)
        site.kinds_filter = summary.kinds_filter_value

    @staticmethod
    def _note_changes(
        db: Session,
        site: SiteCareSite,
        points: list[SitePoint],
        previous_states: dict[str, str],
        *,
        is_first_check: bool,
        stopped_answering: bool,
    ) -> None:
        """Record what a check found that the previous one had not: a hack, a site gone, a point that got worse."""
        if site.id is None:
            db.flush()
        if stopped_answering:
            db.add(SiteCareWatchEvent(user_id=site.user_id, site_id=site.id, kind="unreachable"))
            return
        for point in points:
            if point.state != PointState.FIX or previous_states.get(point.key.value) == PointState.FIX.value:
                continue
            if point.key == PointKey.HACKED:
                db.add(SiteCareWatchEvent(user_id=site.user_id, site_id=site.id, kind="hacked"))
            elif not is_first_check:
                db.add(
                    SiteCareWatchEvent(user_id=site.user_id, site_id=site.id, kind="worse", point_key=point.key.value)
                )

    @staticmethod
    def _count(db: Session, condition: ColumnElement[bool]) -> int:
        """How many sites match a condition."""
        return int(db.execute(select(func.count()).select_from(SiteCareSite).where(condition)).scalar() or 0)


site_service = SiteService()
