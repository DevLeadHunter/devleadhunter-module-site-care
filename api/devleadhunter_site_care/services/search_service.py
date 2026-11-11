"""
The module's search: it brings in businesses the core's searches discarded because they already have a website.

Those businesses were found, named and located by the core; the module only reads their site and keeps them. A
search runs in the module's background loop, a few sites at a time, and never holds a database connection while a
site is read.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import ClassVar

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.database import SessionLocal
from enums.prospect_search import CandidateRejectReason
from models.prospect_search_candidate import ProspectSearchCandidate
from services.prospect_search.trade_catalog import TradeCatalog, TradeProfile
from services.website_liveness_service import WebsiteLivenessService

from devleadhunter_site_care.catalog import NOT_AN_OWN_SITE_HOSTS
from devleadhunter_site_care.models.search import SiteCareSearch
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings, owner_settings_service
from devleadhunter_site_care.services.site_reader import SiteAddress, SiteReader, SiteReading
from devleadhunter_site_care.services.site_service import SiteCareError, site_service

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES: tuple[str, ...] = ("pending", "running")
COUNTRY_LABELS: dict[str, str] = {
    "FR": "France",
    "CH": "Suisse",
    "BE": "Belgique",
    "CA": "Québec",
    "LU": "Luxembourg",
}


@dataclass(frozen=True)
class AvailableTrade:
    """
    A trade the base holds businesses for.

    Attributes:
        key: The core's trade key.
        label: Its name.
        count_by_country: How many businesses are available in each country.
    """

    key: str
    label: str
    count_by_country: dict[str, int]


@dataclass(frozen=True)
class CandidateToRead:
    """What a batch keeps of a core candidate once the database connection is given back."""

    candidate_id: int
    business_name: str
    trade_key: str
    city: str | None
    country: str
    website: str
    host: str
    phone: str | None
    email: str | None
    google_rating: float | None
    google_reviews_count: int | None
    google_maps_url: str | None


class SearchService:
    """Creates the module's searches and runs them batch by batch."""

    _BATCH_SIZE: ClassVar[int] = 6
    _CANDIDATES_SCANNED_PER_BATCH: ClassVar[int] = 60
    _SITES_READ_TOGETHER: ClassVar[int] = 4
    MAX_REQUESTED_COUNT: ClassVar[int] = 300

    def available_trades(self, db: Session, user_id: int) -> list[AvailableTrade]:
        """
        The trades the owner's base holds businesses for, with how many per country.

        Args:
            db: Active database session.
            user_id: The owner.

        Returns:
            The trades by label; a business already in the module is not counted.
        """
        counted = db.execute(
            select(ProspectSearchCandidate.trade, ProspectSearchCandidate.country, func.count())
            .where(self._available(user_id))
            .group_by(ProspectSearchCandidate.trade, ProspectSearchCandidate.country)
        ).all()
        by_key: dict[str, dict[str, int]] = {}
        labels: dict[str, str] = {}
        for typed_trade, country, count in counted:
            profile: TradeProfile = TradeCatalog.resolve(typed_trade)
            labels[profile.key] = profile.label
            countries: dict[str, int] = by_key.setdefault(profile.key, {})
            countries[country] = countries.get(country, 0) + int(count)
        return sorted(
            (AvailableTrade(key, labels[key], counts) for key, counts in by_key.items()),
            key=lambda trade: site_service.folded(trade.label),
        )

    def create(
        self, db: Session, user_id: int, *, trades: list[str], country: str, cities: list[str], requested_count: int
    ) -> SiteCareSearch:
        """
        Queue a search for the background loop.

        Args:
            db: Active database session.
            user_id: The owner.
            trades: Trade keys; none means every trade.
            country: The country to search in.
            cities: Cities to keep; none means the whole country.
            requested_count: How many sites the owner wants.

        Returns:
            The queued search.

        Raises:
            SiteCareError: A search of the owner is already running.
        """
        if self._active_search(db, user_id) is not None:
            raise SiteCareError("Une recherche tourne déjà. Attendez qu’elle se termine pour en lancer une autre.")
        search: SiteCareSearch = SiteCareSearch(
            user_id=user_id,
            trades=[TradeCatalog.resolve(trade).key for trade in trades if trade.strip()],
            country=country.upper()[:2],
            cities=[city.strip() for city in cities if city.strip()][:20],
            requested_count=max(1, min(requested_count, self.MAX_REQUESTED_COUNT)),
        )
        db.add(search)
        db.commit()
        return search

    def current(self, db: Session, user_id: int) -> SiteCareSearch | None:
        """
        The search the owner is waiting for, else his last one.

        Args:
            db: Active database session.
            user_id: The owner.

        Returns:
            The search, or None when he never launched one.
        """
        return (
            self._active_search(db, user_id)
            or db.execute(
                select(SiteCareSearch)
                .where(SiteCareSearch.user_id == user_id)
                .order_by(SiteCareSearch.id.desc())
                .limit(1)
            ).scalar_one_or_none()
        )

    async def run_next_batch(self) -> bool:
        """
        Read the next sites of the oldest unfinished search and store them.

        Returns:
            True when a search was worked on, False when none is waiting.
        """
        with SessionLocal() as db:
            search: SiteCareSearch | None = (
                db.execute(
                    select(SiteCareSearch)
                    .where(SiteCareSearch.status.in_(_ACTIVE_STATUSES))
                    .order_by(SiteCareSearch.id)
                )
                .scalars()
                .first()
            )
            if search is None:
                return False
            search_id: int = search.id
            try:
                search.status = "running"
                settings: OwnerSettings = owner_settings_service.get(db, search.user_id)
                batch: list[CandidateToRead] = self._next_candidates(db, search)
                db.commit()
            except Exception as exc:
                db.rollback()
                self._fail(search_id, exc)
                return True
        if not batch:
            self._complete(search_id)
            return True
        try:
            readings: list[SiteReading] = await self._read_sites([candidate.website for candidate in batch])
            with SessionLocal() as db:
                await self._store_batch(db, search_id, batch, readings, settings)
        except Exception as exc:
            self._fail(search_id, exc)
        return True

    def _next_candidates(self, db: Session, search: SiteCareSearch) -> list[CandidateToRead]:
        """
        The next businesses of the base that match a search, the search's cursor moved past everything looked at.

        A network's outlet, a page on someone else's platform and a host already in the module are passed over.
        """
        wanted: int = min(self._BATCH_SIZE, search.requested_count - search.imported_count)
        known_hosts: set[str] = set(
            db.execute(select(SiteCareSite.host).where(SiteCareSite.user_id == search.user_id)).scalars()
        )
        batch: list[CandidateToRead] = []
        while len(batch) < wanted:
            rows: list[ProspectSearchCandidate] = list(
                db.execute(
                    select(ProspectSearchCandidate)
                    .where(self._matching(search), ProspectSearchCandidate.id > search.last_candidate_id)
                    .order_by(ProspectSearchCandidate.id)
                    .limit(self._CANDIDATES_SCANNED_PER_BATCH)
                ).scalars()
            )
            if not rows:
                break
            for row in rows:
                search.last_candidate_id = row.id
                host: str = SiteAddress.bare_host(SiteAddress.host_of(row.website or ""))
                if not host or host in known_hosts or not self._is_own_site(row, host):
                    continue
                known_hosts.add(host)
                profile: TradeProfile = TradeCatalog.resolve(row.trade)
                batch.append(
                    CandidateToRead(
                        candidate_id=row.id,
                        business_name=row.name,
                        trade_key=profile.key,
                        city=row.city or row.searched_city,
                        country=row.country,
                        website=row.website or "",
                        host=host,
                        phone=row.phone,
                        email=row.email,
                        google_rating=row.google_rating,
                        google_reviews_count=row.google_reviews_count,
                        google_maps_url=row.google_maps_url,
                    )
                )
                if len(batch) >= wanted:
                    break
        return batch

    async def _read_sites(self, websites: list[str]) -> list[SiteReading]:
        """Read several sites, a few at a time, with no database connection held."""
        gate: asyncio.Semaphore = asyncio.Semaphore(self._SITES_READ_TOGETHER)
        async with SiteReader() as reader:

            async def read_one(website: str) -> SiteReading:
                async with gate:
                    return await reader.read(website)

            return list(await asyncio.gather(*(read_one(website) for website in websites)))

    async def _store_batch(
        self,
        db: Session,
        search_id: int,
        batch: list[CandidateToRead],
        readings: list[SiteReading],
        settings: OwnerSettings,
    ) -> None:
        """Store the sites of a batch with their check, and close the search once it has what was asked."""
        search: SiteCareSearch | None = db.get(SiteCareSearch, search_id)
        if search is None:
            return
        for candidate, reading in zip(batch, readings, strict=True):
            site: SiteCareSite = SiteCareSite(
                user_id=search.user_id,
                search_id=search.id,
                candidate_id=candidate.candidate_id,
                business_name=candidate.business_name[:255],
                trade=candidate.trade_key,
                city=candidate.city,
                country=candidate.country,
                website=candidate.website[:500],
                host=candidate.host[:190],
                phone=candidate.phone,
                email=(candidate.email or "").strip().lower() or None,
                email_source="listing" if candidate.email else None,
                google_rating=candidate.google_rating,
                google_reviews_count=candidate.google_reviews_count,
                google_maps_url=candidate.google_maps_url,
                status="",
                page_slug=site_service.new_page_slug(candidate.business_name),
                search_text=site_service.search_text_of(candidate.business_name, candidate.city, candidate.host),
            )
            db.add(site)
            await site_service.apply_reading(db, site, reading, settings)
            search.checked_count += 1
            search.imported_count += 1
        if search.imported_count >= search.requested_count:
            search.status = "completed"
            search.completed_at = naive_utc_now()
        db.commit()

    def _complete(self, search_id: int) -> None:
        """Close a search the base has nothing left for, saying so when it found less than asked."""
        with SessionLocal() as db:
            search: SiteCareSearch | None = db.get(SiteCareSearch, search_id)
            if search is None:
                return
            search.status = "completed"
            search.completed_at = naive_utc_now()
            if search.imported_count == 0:
                search.note = "Aucune entreprise disponible pour ces critères."
            elif search.imported_count < search.requested_count:
                search.note = (
                    f"La base n’avait que {search.imported_count} entreprises pour ces critères. Les recherches "
                    "du module Sites web en apportent de nouvelles."
                )
            db.commit()

    @staticmethod
    def _fail(search_id: int, error: Exception) -> None:
        """Close a search that broke, keeping what it already brought in."""
        logger.exception("[SiteCare] search %s failed", search_id, exc_info=error)
        with SessionLocal() as db:
            search: SiteCareSearch | None = db.get(SiteCareSearch, search_id)
            if search is None:
                return
            search.status = "failed"
            search.completed_at = naive_utc_now()
            search.note = "La recherche s’est arrêtée sur une erreur. Les sites déjà regardés sont dans la liste."
            db.commit()

    @staticmethod
    def _active_search(db: Session, user_id: int) -> SiteCareSearch | None:
        """The owner's search that is queued or running."""
        return db.execute(
            select(SiteCareSearch)
            .where(SiteCareSearch.user_id == user_id, SiteCareSearch.status.in_(_ACTIVE_STATUSES))
            .order_by(SiteCareSearch.id.desc())
            .limit(1)
        ).scalar_one_or_none()

    @staticmethod
    def _available(user_id: int) -> ColumnElement[bool]:
        """The owner's businesses discarded for having a website, not yet a prospect nor in the module."""
        return and_(
            ProspectSearchCandidate.user_id == user_id,
            ProspectSearchCandidate.reject_reason == CandidateRejectReason.HAS_WEBSITE.value,
            ProspectSearchCandidate.website.is_not(None),
            ProspectSearchCandidate.prospect_id.is_(None),
            ProspectSearchCandidate.id.not_in(
                select(SiteCareSite.candidate_id).where(
                    SiteCareSite.user_id == user_id, SiteCareSite.candidate_id.is_not(None)
                )
            ),
        )

    def _matching(self, search: SiteCareSearch) -> ColumnElement[bool]:
        """The available businesses that fit a search's country, trades and cities."""
        matching: ColumnElement[bool] = and_(
            self._available(search.user_id), ProspectSearchCandidate.country == search.country
        )
        if search.trades:
            # A candidate keeps the trade as it was typed: every spelling of the asked trades is accepted.
            matching = and_(matching, self._trade_is_one_of(search.trades))
        if search.cities:
            lowered: list[str] = [city.lower() for city in search.cities]
            matching = and_(
                matching,
                or_(
                    func.lower(ProspectSearchCandidate.city).in_(lowered),
                    func.lower(ProspectSearchCandidate.searched_city).in_(lowered),
                ),
            )
        return matching

    @staticmethod
    def _trade_is_one_of(trade_keys: list[str]) -> ColumnElement[bool]:
        """Whether a candidate's typed trade is one of the asked trades, by key or by any of its names."""
        spellings: set[str] = set()
        for key in trade_keys:
            profile: TradeProfile = TradeCatalog.resolve(key)
            spellings.update({profile.key, profile.label, *profile.aliases})
        lowered: set[str] = {spelling.lower() for spelling in spellings}
        return func.lower(ProspectSearchCandidate.trade).in_(sorted(lowered))

    @staticmethod
    def _is_own_site(row: ProspectSearchCandidate, host: str) -> bool:
        """Whether the address is the business's own site: not a platform page, a directory mini-site or a network."""
        if any(marker in host for marker in NOT_AN_OWN_SITE_HOSTS):
            return False
        if WebsiteLivenessService.is_placeholder_host(WebsiteLivenessService.normalize_url(row.website or "")):
            return False
        profile: TradeProfile = TradeCatalog.resolve(row.trade)
        return (
            profile.brand_of_site(row.website or "") is None
            and profile.brand_outlet_of(row.name, row.google_category) is None
        )


search_service = SearchService()
