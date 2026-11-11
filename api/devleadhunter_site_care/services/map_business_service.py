"""The businesses of the open map an owner knows: a département's stored once, then handed over batch by batch."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from services.prospect_search.trade_catalog import TradeCatalog, TradeProfile

from devleadhunter_site_care.french_departments import FrenchDepartments
from devleadhunter_site_care.models.map_business import SiteCareMapBusiness
from devleadhunter_site_care.models.search import SiteCareSearch
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.services.open_map import ListedBusiness
from devleadhunter_site_care.services.site_reader import SiteAddress
from devleadhunter_site_care.services.site_service import site_service
from devleadhunter_site_care.services.site_to_read import SiteToRead


@dataclass(frozen=True)
class PlacedSite:
    """
    A site whose business the open map placed without naming its town.

    Attributes:
        site_id: The site.
        map_business_id: Its business on the open map.
        latitude: Where the business is.
        longitude: Where the business is.
    """

    site_id: int
    map_business_id: int
    latitude: float
    longitude: float


class MapBusinessService:
    """
    Keeps what the open map lists, and remembers which sites were read.

    A site read once is never read again by a later search, whether it was kept or not: the search moves on to
    the businesses nobody looked at yet.
    """

    _HOSTS_COMPARED_TOGETHER: ClassVar[int] = 500

    @staticmethod
    def department_to_collect(search: SiteCareSearch) -> str | None:
        """
        The next département of a search whose businesses were not fetched from the open map yet.

        Args:
            search: The search.

        Returns:
            Its code, None once every département asked for was fetched.
        """
        collected: set[str] = set(search.collected_departments or [])
        return next((code for code in search.departments or [] if code not in collected), None)

    def store_new(self, db: Session, user_id: int, department: str, listed: Sequence[ListedBusiness]) -> int:
        """
        Store the businesses of a département the owner does not know yet (the caller commits).

        Args:
            db: Active database session.
            user_id: The owner.
            department: The département the businesses were listed in.
            listed: What the open map lists there.

        Returns:
            How many businesses were added; a site already listed, already in the module or not the business's
            own is left out.
        """
        own: list[ListedBusiness] = [
            business
            for business in listed
            if SiteAddress.is_own_site(business.website, business.host, business.business_name, business.trade_label)
        ]
        known_hosts: set[str] = self._known_hosts(db, user_id, [business.host for business in own])
        added_count: int = 0
        for business in own:
            if business.host in known_hosts:
                continue
            known_hosts.add(business.host)
            db.add(
                SiteCareMapBusiness(
                    user_id=user_id,
                    department=department,
                    family=business.family.value,
                    map_reference=business.map_reference[:32],
                    business_name=business.business_name[:255],
                    trade=self.stored_trade_of(business.trade_label)[:80],
                    city=(business.city or "")[:120] or None,
                    phone=business.phone,
                    email=business.email,
                    website=business.website,
                    host=business.host[:190],
                    latitude=business.latitude,
                    longitude=business.longitude,
                )
            )
            added_count += 1
        return added_count

    def next_sites(self, db: Session, search: SiteCareSearch, wanted_count: int) -> list[SiteToRead]:
        """
        The next businesses of a search whose site was never read (the caller commits).

        Args:
            db: Active database session.
            search: The search.
            wanted_count: How many sites the batch reads.

        Returns:
            The businesses, oldest listed first; one whose site entered the module another way is passed over.
        """
        sites: list[SiteToRead] = []
        last_looked_at_id: int = 0
        while len(sites) < wanted_count:
            rows: list[SiteCareMapBusiness] = list(
                db.execute(
                    select(SiteCareMapBusiness)
                    .where(
                        SiteCareMapBusiness.user_id == search.user_id,
                        SiteCareMapBusiness.department.in_(search.departments or []),
                        SiteCareMapBusiness.family.in_(search.families or []),
                        SiteCareMapBusiness.read_at.is_(None),
                        SiteCareMapBusiness.id > last_looked_at_id,
                    )
                    .order_by(SiteCareMapBusiness.id)
                    .limit(wanted_count - len(sites))
                ).scalars()
            )
            if not rows:
                break
            last_looked_at_id = rows[-1].id
            hosts_in_module: set[str] = self._hosts_in_module(db, search.user_id, [row.host for row in rows])
            for row in rows:
                if row.host in hosts_in_module:
                    row.read_at, row.was_kept = naive_utc_now(), False
                    continue
                sites.append(
                    SiteToRead(
                        business_name=row.business_name,
                        trade=row.trade,
                        city=row.city,
                        country=FrenchDepartments.COUNTRY_CODE,
                        website=row.website,
                        host=row.host,
                        phone=row.phone,
                        email=row.email,
                        map_business_id=row.id,
                        latitude=row.latitude,
                        longitude=row.longitude,
                    )
                )
        return sites

    @staticmethod
    def mark_read(db: Session, map_business_id: int, *, was_kept: bool, read_at: datetime) -> None:
        """
        Note that a business's site was read, so no later search reads it again (the caller commits).

        Args:
            db: Active database session.
            map_business_id: The business.
            was_kept: Whether the search kept the site.
            read_at: When the site was read.
        """
        row: SiteCareMapBusiness | None = db.get(SiteCareMapBusiness, map_business_id)
        if row is not None:
            row.read_at, row.was_kept = read_at, was_kept

    @staticmethod
    def sites_placed_without_a_town(db: Session, site_count: int) -> list[PlacedSite]:
        """
        Some of the sites the open map placed on the map without naming their town.

        Args:
            db: Active database session.
            site_count: How many sites to return at most.

        Returns:
            The sites, oldest first, each with the point of its business.
        """
        rows = db.execute(
            select(SiteCareSite.id, SiteCareMapBusiness.id, SiteCareMapBusiness.latitude, SiteCareMapBusiness.longitude)
            .join(
                SiteCareMapBusiness,
                and_(
                    SiteCareMapBusiness.user_id == SiteCareSite.user_id,
                    SiteCareMapBusiness.host == SiteCareSite.host,
                ),
            )
            .where(
                SiteCareSite.city.is_(None),
                SiteCareSite.archived_at.is_(None),
                SiteCareMapBusiness.latitude.is_not(None),
                SiteCareMapBusiness.longitude.is_not(None),
            )
            .order_by(SiteCareSite.id)
            .limit(site_count)
        ).all()
        return [PlacedSite(*row) for row in rows]

    @staticmethod
    def store_town(db: Session, placed_site: PlacedSite, town: str | None) -> None:
        """
        Store the town the list of communes gives for a placed site (the caller commits).

        Args:
            db: Active database session.
            placed_site: The site and the point of its business.
            town: The commune the point is in; None when it is in none, and the point is then forgotten so it
                is never asked again.
        """
        if town is None:
            map_business: SiteCareMapBusiness | None = db.get(SiteCareMapBusiness, placed_site.map_business_id)
            if map_business is not None:
                map_business.latitude, map_business.longitude = None, None
            return
        site: SiteCareSite | None = db.get(SiteCareSite, placed_site.site_id)
        if site is not None and site.city is None:
            site.city = town
            site.search_text = site_service.search_text_of(site.business_name, town, site.host)

    @staticmethod
    def stored_trade_of(trade_label: str) -> str:
        """
        The trade a site stores for a trade of the open map.

        Args:
            trade_label: The trade, in French.

        Returns:
            The core's trade key when the core knows the trade (a plumber of the map and one of a core search
            then share a filter), else the French name itself.
        """
        profile: TradeProfile = TradeCatalog.resolve(trade_label)
        return trade_label if profile.is_generic else profile.key

    def _known_hosts(self, db: Session, user_id: int, hosts: list[str]) -> set[str]:
        """Among some hosts, those the owner already has: listed by the open map or in the module."""
        known: set[str] = set()
        for start in range(0, len(hosts), self._HOSTS_COMPARED_TOGETHER):
            compared: list[str] = hosts[start : start + self._HOSTS_COMPARED_TOGETHER]
            known.update(
                db.execute(
                    select(SiteCareMapBusiness.host).where(
                        SiteCareMapBusiness.user_id == user_id, SiteCareMapBusiness.host.in_(compared)
                    )
                ).scalars()
            )
            known.update(self._hosts_in_module(db, user_id, compared))
        return known

    @staticmethod
    def _hosts_in_module(db: Session, user_id: int, hosts: list[str]) -> set[str]:
        """Among some hosts, those of the owner's sites."""
        return set(
            db.execute(
                select(SiteCareSite.host).where(SiteCareSite.user_id == user_id, SiteCareSite.host.in_(hosts))
            ).scalars()
        )


map_business_service = MapBusinessService()
