"""
The module's search: it brings businesses that already have a website into the module.

A search draws from one of two sources. The owner's base holds the businesses the core's searches discarded because
they have a website: the core found, named and located them. The open map (OpenStreetMap) lists the businesses of a
French département with their site, whatever their trade. Either way the module reads each site and keeps what the
search asked for. A search runs in the module's background loop, a few sites at a time, and never holds a database
connection while a site or the open map is read.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field, replace
from typing import ClassVar

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.database import SessionLocal
from enums.prospect_search import CandidateRejectReason
from models.prospect_search_candidate import ProspectSearchCandidate
from services.prospect_search.trade_catalog import TradeCatalog, TradeProfile

from devleadhunter_site_care.catalog import (
    ACTIVE_SEARCH_STATUSES,
    BusinessFamily,
    KeepRule,
    SearchSource,
    SiteStatus,
)
from devleadhunter_site_care.french_departments import FrenchDepartments
from devleadhunter_site_care.models.search import SiteCareSearch
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.services.map_business_service import PlacedSite, map_business_service
from devleadhunter_site_care.services.open_map import (
    ListedBusiness,
    OpenMapUnavailableError,
    open_map_directory,
    town_locator,
)
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings, owner_settings_service
from devleadhunter_site_care.services.search_wording import SearchWording
from devleadhunter_site_care.services.site_reader import SiteAddress, SiteReader, SiteReading
from devleadhunter_site_care.services.site_service import SiteCareError, SiteCheck, site_service
from devleadhunter_site_care.services.site_summary import SiteSummary
from devleadhunter_site_care.services.site_to_read import SiteToRead

logger = logging.getLogger(__name__)


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
class SearchRequest:
    """
    What the owner asks a new search for.

    Attributes:
        requested_count: How many sites he wants in his list.
        source: Where the businesses come from.
        trades: In his base, the trade keys; none means every trade.
        country: In his base, the country to search in.
        cities: In his base, the cities to keep; none means the whole country.
        departments: On the open map, the French départements to go through.
        families: On the open map, the families of businesses; none means every family.
        keep_rule: On the open map, which of the sites read enter the list.
    """

    requested_count: int
    source: SearchSource = SearchSource.OWN_BASE
    trades: list[str] = field(default_factory=list)
    country: str = FrenchDepartments.COUNTRY_CODE
    cities: list[str] = field(default_factory=list)
    departments: list[str] = field(default_factory=list)
    families: list[BusinessFamily] = field(default_factory=list)
    keep_rule: KeepRule = KeepRule.EVERY_SITE


@dataclass(frozen=True)
class BatchPlan:
    """
    What the next pass of a search does, decided while the database connection is held.

    Attributes:
        sites: The businesses whose site the pass reads.
        keep_rule: Which of them enter the list.
        sites_read_together: How many sites are read at once.
        department_to_collect: The département to fetch from the open map first, when no listed site is left.
        families: The families to fetch there.
    """

    sites: list[SiteToRead]
    keep_rule: KeepRule
    sites_read_together: int
    department_to_collect: str | None = None
    families: list[BusinessFamily] = field(default_factory=list)


@dataclass(frozen=True)
class CheckedSite:
    """
    A business whose site was just read and checked.

    Attributes:
        site: The business.
        reading: What its site answered.
        check: What the reading says.
        is_kept: Whether the search keeps the site.
        city: Its town, named from where it is when the source gave none.
        contact_page_emails: The addresses its contact and legal pages show, read when nothing else gave one.
    """

    site: SiteToRead
    reading: SiteReading
    check: SiteCheck
    is_kept: bool
    city: str | None
    contact_page_emails: list[str]


class SearchService:
    """Creates the module's searches and runs them batch by batch."""

    _BATCH_SIZE: ClassVar[int] = 6
    _CANDIDATES_SCANNED_PER_BATCH: ClassVar[int] = 60
    _SITES_READ_TOGETHER: ClassVar[int] = 4
    _OPEN_MAP_BATCH_SIZE: ClassVar[int] = 60
    _OPEN_MAP_SITES_READ_TOGETHER: ClassVar[int] = 12
    _TOWNS_NAMED_PER_PASS: ClassVar[int] = 10
    MAX_REQUESTED_COUNT: ClassVar[int] = 300
    MAX_OPEN_MAP_REQUESTED_COUNT: ClassVar[int] = 2000
    MAX_DEPARTMENTS: ClassVar[int] = 20

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

    def create(self, db: Session, user_id: int, request: SearchRequest) -> SiteCareSearch:
        """
        Queue a search for the background loop.

        Args:
            db: Active database session.
            user_id: The owner.
            request: What he asks for.

        Returns:
            The queued search.

        Raises:
            SiteCareError: A search of the owner is already running, or the open map is asked for no département.
        """
        if self._active_search(db, user_id) is not None:
            raise SiteCareError("Une recherche tourne déjà. Attendez qu’elle se termine pour en lancer une autre.")
        search: SiteCareSearch = (
            self._build_open_map_search(user_id, request)
            if request.source == SearchSource.OPEN_MAP
            else self._build_own_base_search(user_id, request)
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

    def stop(self, db: Session, user_id: int) -> SiteCareSearch | None:
        """
        Stop the owner's running search; the sites it already brought stay in the list.

        Args:
            db: Active database session.
            user_id: The owner.

        Returns:
            The stopped search, or his last one when none was running, or None when he never launched one.
        """
        search: SiteCareSearch | None = self._active_search(db, user_id)
        if search is None:
            return self.current(db, user_id)
        search.status = "completed"
        search.completed_at = naive_utc_now()
        search.note = SearchWording.STOPPED_BY_HAND_NOTE
        db.commit()
        return search

    async def run_next_batch(self) -> bool:
        """
        Work on the oldest unfinished search: read its next sites and store them, or fetch its next département.

        Returns:
            True when a search was worked on, False when none is waiting.
        """
        with SessionLocal() as db:
            search: SiteCareSearch | None = (
                db.execute(
                    select(SiteCareSearch)
                    .where(SiteCareSearch.status.in_(ACTIVE_SEARCH_STATUSES))
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
                plan: BatchPlan = self._next_batch(db, search)
                db.commit()
            except Exception as exc:
                db.rollback()
                self._fail(search_id, exc)
                return True
        try:
            if plan.department_to_collect is not None:
                await self._collect_department(search_id, plan.department_to_collect, plan.families)
            elif not plan.sites:
                self._complete(search_id)
            else:
                checked_sites: list[CheckedSite] = await self._read_batch(plan, settings)
                with SessionLocal() as db:
                    self._store_batch(db, search_id, checked_sites)
        except OpenMapUnavailableError as exc:
            self._fail(search_id, exc, note=f"{exc} Les sites déjà gardés sont dans la liste : relancez plus tard.")
        except Exception as exc:
            self._fail(search_id, exc)
        return True

    async def name_missing_towns(self) -> None:
        """
        Name the town of a few sites the open map placed without naming it.

        A search asks the list of communes while it reads its sites, but the list often fails to answer: what it
        missed is caught up here, between two searches, a few sites at a time.
        """
        if town_locator.is_resting:
            return
        with SessionLocal() as db:
            placed_sites: list[PlacedSite] = map_business_service.sites_placed_without_a_town(
                db, self._TOWNS_NAMED_PER_PASS
            )
        towns: list[tuple[PlacedSite, str | None]] = []
        for placed_site in placed_sites:
            town: str | None = await town_locator.town_at(placed_site.latitude, placed_site.longitude)
            if town_locator.is_resting:
                break
            towns.append((placed_site, town))
        if not towns:
            return
        with SessionLocal() as db:
            for placed_site, town in towns:
                map_business_service.store_town(db, placed_site, town)
            db.commit()

    def _build_own_base_search(self, user_id: int, request: SearchRequest) -> SiteCareSearch:
        """A search in the owner's base; every site read there enters the list."""
        return SiteCareSearch(
            user_id=user_id,
            source=SearchSource.OWN_BASE.value,
            trades=[TradeCatalog.resolve(trade).key for trade in request.trades if trade.strip()],
            country=request.country.upper()[:2],
            cities=[city.strip() for city in request.cities if city.strip()][:20],
            keep_rule=KeepRule.EVERY_SITE.value,
            requested_count=max(1, min(request.requested_count, self.MAX_REQUESTED_COUNT)),
        )

    def _build_open_map_search(self, user_id: int, request: SearchRequest) -> SiteCareSearch:
        """A search on the open map, in the French départements asked for."""
        departments: list[str] = list(
            dict.fromkeys(code.upper() for code in request.departments if code.upper() in FrenchDepartments.NAMES)
        )[: self.MAX_DEPARTMENTS]
        if not departments:
            raise SiteCareError("Choisissez au moins un département.")
        families: list[BusinessFamily] = list(dict.fromkeys(request.families)) or list(BusinessFamily)
        return SiteCareSearch(
            user_id=user_id,
            source=SearchSource.OPEN_MAP.value,
            country=FrenchDepartments.COUNTRY_CODE,
            departments=departments,
            families=[family.value for family in families],
            keep_rule=request.keep_rule.value,
            requested_count=max(1, min(request.requested_count, self.MAX_OPEN_MAP_REQUESTED_COUNT)),
        )

    def _next_batch(self, db: Session, search: SiteCareSearch) -> BatchPlan:
        """What the next pass of a search does: the sites it reads, or the département it fetches first."""
        if search.source != SearchSource.OPEN_MAP.value:
            return BatchPlan(
                sites=self._next_candidates(db, search),
                keep_rule=KeepRule.EVERY_SITE,
                sites_read_together=self._SITES_READ_TOGETHER,
            )
        sites: list[SiteToRead] = map_business_service.next_sites(db, search, self._OPEN_MAP_BATCH_SIZE)
        return BatchPlan(
            sites=sites,
            keep_rule=KeepRule(search.keep_rule),
            sites_read_together=self._OPEN_MAP_SITES_READ_TOGETHER,
            department_to_collect=None if sites else map_business_service.department_to_collect(search),
            families=[BusinessFamily(family) for family in search.families or []],
        )

    def _next_candidates(self, db: Session, search: SiteCareSearch) -> list[SiteToRead]:
        """
        The next businesses of the base that match a search, the search's cursor moved past everything looked at.

        A network's outlet, a page on someone else's platform and a host already in the module are passed over.
        """
        wanted: int = min(self._BATCH_SIZE, search.requested_count - search.imported_count)
        known_hosts: set[str] = set(
            db.execute(select(SiteCareSite.host).where(SiteCareSite.user_id == search.user_id)).scalars()
        )
        batch: list[SiteToRead] = []
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
                website: str = row.website or ""
                host: str = SiteAddress.bare_host(SiteAddress.host_of(website))
                if (
                    not host
                    or host in known_hosts
                    or not SiteAddress.is_own_site(website, host, row.name, row.trade, row.google_category)
                ):
                    continue
                known_hosts.add(host)
                batch.append(
                    SiteToRead(
                        business_name=row.name,
                        trade=TradeCatalog.resolve(row.trade).key,
                        city=row.city or row.searched_city,
                        country=row.country,
                        website=website,
                        host=host,
                        phone=row.phone,
                        email=row.email,
                        google_rating=row.google_rating,
                        google_reviews_count=row.google_reviews_count,
                        google_maps_url=row.google_maps_url,
                        candidate_id=row.id,
                    )
                )
                if len(batch) >= wanted:
                    break
        return batch

    async def _collect_department(self, search_id: int, department: str, families: list[BusinessFamily]) -> None:
        """Fetch a département's businesses from the open map and store those the owner does not know yet."""
        listed: list[ListedBusiness] = await open_map_directory.businesses_of(department, families)
        with SessionLocal() as db:
            search: SiteCareSearch | None = db.get(SiteCareSearch, search_id)
            if search is None or search.status not in ACTIVE_SEARCH_STATUSES:
                return
            added_count: int = map_business_service.store_new(db, search.user_id, department, listed)
            search.collected_departments = [*(search.collected_departments or []), department]
            db.commit()
            logger.info("[SiteCare] search %s: %s new sites listed in %s", search_id, added_count, department)

    async def _read_batch(self, plan: BatchPlan, settings: OwnerSettings) -> list[CheckedSite]:
        """Read the sites of a pass and decide which the search keeps, with no database connection held."""
        gate: asyncio.Semaphore = asyncio.Semaphore(plan.sites_read_together)
        async with SiteReader() as reader:
            checked_sites: list[CheckedSite] = list(
                await asyncio.gather(
                    *(self._check_site(reader, gate, site, settings, plan.keep_rule) for site in plan.sites)
                )
            )
        # One at a time: geo.api.gouv.fr drops requests sent together.
        return [await self._with_its_town(checked_site) for checked_site in checked_sites]

    async def _check_site(
        self,
        reader: SiteReader,
        gate: asyncio.Semaphore,
        site: SiteToRead,
        settings: OwnerSettings,
        keep_rule: KeepRule,
    ) -> CheckedSite:
        """Read one site, check it, and look on its contact pages for an address when a kept site has none."""
        async with gate:
            reading: SiteReading = await reader.read(site.website)
        check: SiteCheck = await site_service.check_of(
            reading,
            settings,
            google_listing_phone=site_service.google_listing_phone_of(site.phone, site.candidate_id),
        )
        is_kept: bool = self._is_kept(keep_rule, check.summary)
        contact_page_emails: list[str] = []
        if is_kept and self._lacks_an_email(site, reading):
            async with gate:
                contact_page_emails = await reader.read_emails_of_pages(reading.contact_page_urls)
        return CheckedSite(
            site=site,
            reading=reading,
            check=check,
            is_kept=is_kept,
            city=site.city,
            contact_page_emails=contact_page_emails,
        )

    @staticmethod
    async def _with_its_town(checked_site: CheckedSite) -> CheckedSite:
        """A kept business whose source gave no town, with the commune it is placed in; any other as it is."""
        business: SiteToRead = checked_site.site
        if checked_site.city or not checked_site.is_kept or business.latitude is None or business.longitude is None:
            return checked_site
        return replace(checked_site, city=await town_locator.town_at(business.latitude, business.longitude))

    @staticmethod
    def _lacks_an_email(site: SiteToRead, reading: SiteReading) -> bool:
        """Whether a business has no address yet though its site has contact or legal pages to look on."""
        has_an_email: bool = bool(site.email) or site_service.best_email(reading.emails, site.host) is not None
        return not has_an_email and bool(reading.contact_page_urls)

    @staticmethod
    def _is_kept(keep_rule: KeepRule, summary: SiteSummary) -> bool:
        """Whether a search keeps a site, from what its check says."""
        if keep_rule == KeepRule.EVERY_SITE:
            return True
        deserves_a_message: bool = summary.status == SiteStatus.TO_WRITE
        return deserves_a_message and (keep_rule == KeepRule.ANY_ISSUE or summary.has_security_issue)

    def _store_batch(self, db: Session, search_id: int, checked_sites: list[CheckedSite]) -> None:
        """
        Store the sites a pass keeps, and close the search once it has what was asked.

        A search stopped while its sites were read stores nothing; once the count asked for is reached, the sites
        left of the pass stay unread, for a later search. A site without an address takes the one its contact and
        legal pages show.
        """
        search: SiteCareSearch | None = db.get(SiteCareSearch, search_id)
        if search is None or search.status not in ACTIVE_SEARCH_STATUSES:
            return
        for checked_site in checked_sites:
            if search.imported_count >= search.requested_count:
                break
            search.checked_count += 1
            if checked_site.site.map_business_id is not None:
                map_business_service.mark_read(
                    db,
                    checked_site.site.map_business_id,
                    was_kept=checked_site.is_kept,
                    read_at=checked_site.reading.read_at,
                )
            if not checked_site.is_kept:
                continue
            site: SiteCareSite = self._new_site(search, checked_site)
            db.add(site)
            site_service.apply_check(db, site, checked_site.reading, checked_site.check)
            site_service.adopt_email(site, checked_site.contact_page_emails)
            search.imported_count += 1
        if search.imported_count >= search.requested_count:
            search.status = "completed"
            search.completed_at = naive_utc_now()
        db.commit()

    @staticmethod
    def _new_site(search: SiteCareSearch, checked_site: CheckedSite) -> SiteCareSite:
        """The site of a business a search keeps, before its first check is stored on it."""
        business: SiteToRead = checked_site.site
        return SiteCareSite(
            user_id=search.user_id,
            search_id=search.id,
            candidate_id=business.candidate_id,
            business_name=business.business_name[:255],
            trade=business.trade,
            city=checked_site.city,
            country=business.country,
            website=business.website[:500],
            host=business.host[:190],
            phone=business.phone,
            email=(business.email or "").strip().lower() or None,
            email_source="listing" if business.email else None,
            google_rating=business.google_rating,
            google_reviews_count=business.google_reviews_count,
            google_maps_url=business.google_maps_url,
            status="",
            page_slug=site_service.new_page_slug(business.business_name),
            search_text=site_service.search_text_of(business.business_name, checked_site.city, business.host),
        )

    @staticmethod
    def _complete(search_id: int) -> None:
        """Close a search its source has nothing left for, saying so when it kept less than asked."""
        with SessionLocal() as db:
            search: SiteCareSearch | None = db.get(SiteCareSearch, search_id)
            if search is None:
                return
            search.status = "completed"
            search.completed_at = naive_utc_now()
            search.note = SearchWording.short_of_sites_note(search)
            db.commit()

    @staticmethod
    def _fail(search_id: int, error: Exception, *, note: str = SearchWording.FAILED_NOTE) -> None:
        """Close a search that broke, keeping what it already brought in."""
        logger.exception("[SiteCare] search %s failed", search_id, exc_info=error)
        with SessionLocal() as db:
            search: SiteCareSearch | None = db.get(SiteCareSearch, search_id)
            if search is None:
                return
            search.status = "failed"
            search.completed_at = naive_utc_now()
            search.note = note[:400]
            db.commit()

    @staticmethod
    def _active_search(db: Session, user_id: int) -> SiteCareSearch | None:
        """The owner's search that is queued or running."""
        return db.execute(
            select(SiteCareSearch)
            .where(SiteCareSearch.user_id == user_id, SiteCareSearch.status.in_(ACTIVE_SEARCH_STATUSES))
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


search_service = SearchService()
