"""
The open map: the businesses OpenStreetMap lists with a website, one French département at a time.

OpenStreetMap is asked through Overpass, its public query server, for the few fields the module keeps (name, trade,
town, phone, email, website). Its data is under the ODbL licence: the dashboard credits its contributors.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import time
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar
from urllib.parse import ParseResult, urlparse

import httpx

from devleadhunter_site_care.catalog import BusinessFamily
from devleadhunter_site_care.french_departments import FrenchDepartments
from devleadhunter_site_care.services.open_map_trades import OpenMapTrades
from devleadhunter_site_care.services.site_reader import HomePageFacts, SiteAddress

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ListedBusiness:
    """
    A business as the open map lists it.

    Attributes:
        map_reference: Its object on the map (« node/123 »).
        business_name: The business.
        family: Its family of businesses.
        trade_label: Its trade, in French.
        website: Its site's address, with its scheme.
        host: The site's host without « www. ».
        city: Its town, when the map gives it.
        phone: Its phone number, when the map gives it.
        email: Its email address, when the map gives it.
        latitude: Where it is.
        longitude: Where it is.
    """

    map_reference: str
    business_name: str
    family: BusinessFamily
    trade_label: str
    website: str
    host: str
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class OpenMapUnavailableError(RuntimeError):
    """The open map did not answer after several tries; the search ends and says why."""


class OpenMapAnswer:
    """Reads the businesses out of the open map's answer, a table with one line per object of the map."""

    COLUMNS: ClassVar[tuple[str, ...]] = (
        "::type",
        "::id",
        "::lat",
        "::lon",
        "name",
        "website",
        "contact:website",
        "phone",
        "contact:phone",
        "email",
        "contact:email",
        "addr:city",
        "brand",
        "brand:wikidata",
        "craft",
        "shop",
        "office",
        "amenity",
        "tourism",
    )
    _BUSINESSES_ON_ONE_SITE_THAT_MAKE_A_NETWORK: ClassVar[int] = 3
    _HOME_PAGE_PATHS: ClassVar[frozenset[str]] = frozenset(
        {"", "fr", "en", "home", "accueil", "index.html", "index.php"}
    )

    @classmethod
    def businesses_of(cls, answer: str, families: Sequence[BusinessFamily]) -> list[ListedBusiness]:
        """
        The businesses of an answer that have a site of their own.

        Args:
            answer: The open map's answer: tab-separated lines under a header, in the order of :attr:`COLUMNS`.
            families: The families asked for.

        Returns:
            One business per site; a branded outlet, a page inside someone else's site and a site shared by
            several businesses (a network's) are left out.
        """
        listed: list[ListedBusiness] = []
        lines: Iterator[list[str]] = csv.reader(io.StringIO(answer), delimiter="\t", quoting=csv.QUOTE_NONE)
        for line_number, cells in enumerate(lines):
            if line_number == 0 or len(cells) != len(cls.COLUMNS):
                continue
            business: ListedBusiness | None = cls._business_of(dict(zip(cls.COLUMNS, cells, strict=True)), families)
            if business is not None:
                listed.append(business)
        businesses_per_host: Counter[str] = Counter(business.host for business in listed)
        own_sites: dict[str, ListedBusiness] = {}
        for business in listed:
            if businesses_per_host[business.host] < cls._BUSINESSES_ON_ONE_SITE_THAT_MAKE_A_NETWORK:
                own_sites.setdefault(business.host, business)
        return list(own_sites.values())

    @classmethod
    def _business_of(cls, row: dict[str, str], families: Sequence[BusinessFamily]) -> ListedBusiness | None:
        """The business of one line, None when it is no independent business with a site of its own."""
        name: str = row["name"].strip()
        trade: tuple[BusinessFamily, str] | None = OpenMapTrades.trade_of(
            craft=cls._first_of(row["craft"]),
            shop=cls._first_of(row["shop"]),
            office=cls._first_of(row["office"]),
            amenity=cls._first_of(row["amenity"]),
            tourism=cls._first_of(row["tourism"]),
        )
        if not name or trade is None or row["brand"] or row["brand:wikidata"]:
            return None
        family, trade_label = trade
        website: str | None = cls._own_site_address(row["website"] or row["contact:website"])
        if family not in families or website is None:
            return None
        email: str = cls._first_of(row["email"] or row["contact:email"]).lower()
        return ListedBusiness(
            map_reference=f"{row['::type']}/{row['::id']}",
            business_name=name,
            family=family,
            trade_label=trade_label,
            website=website,
            host=SiteAddress.bare_host(SiteAddress.host_of(website)),
            city=row["addr:city"].strip() or None,
            phone=cls._first_of(row["phone"] or row["contact:phone"])[:50] or None,
            email=email if HomePageFacts.is_email_address(email) else None,
            latitude=cls._coordinate_of(row["::lat"]),
            longitude=cls._coordinate_of(row["::lon"]),
        )

    @classmethod
    def _own_site_address(cls, written: str) -> str | None:
        """
        The address of a business's site as the map writes it, with its scheme.

        Returns:
            None when the address is unreadable or points inside a site (« …/magasins/rennes »): such a page is an
            outlet's or a directory's, and the site belongs to someone else.
        """
        address: str = cls._first_of(written)
        if not address or " " in address:
            return None
        website: str = address if "://" in address else f"https://{address}"
        parsed: ParseResult = urlparse(website)
        if "." not in parsed.netloc or parsed.path.strip("/").lower() not in cls._HOME_PAGE_PATHS:
            return None
        return website[:500]

    @staticmethod
    def _first_of(written: str) -> str:
        """The first value of a field the map writes several values in (« a;b »)."""
        return written.split(";")[0].strip()

    @staticmethod
    def _coordinate_of(written: str) -> float | None:
        """A latitude or a longitude, None when the map gives none."""
        try:
            return float(written)
        except ValueError:
            return None


class OpenMapDirectory:
    """Asks the open map for the businesses of a French département that have a website."""

    _SERVER_URL: ClassVar[str] = "https://overpass-api.de/api/interpreter"
    _REQUEST_HEADERS: ClassVar[dict[str, str]] = {"User-Agent": "DevLeadHunter/1.0 (site care search)"}
    _QUERY_TIMEOUT_SECONDS: ClassVar[int] = 240
    _ATTEMPTS: ClassVar[int] = 3
    _SECONDS_BEFORE_ASKING_AGAIN: ClassVar[float] = 20.0
    _FAMILY_FILTERS: ClassVar[dict[BusinessFamily, str]] = {
        BusinessFamily.CRAFT: '["craft"]',
        BusinessFamily.SHOP: '["shop"]',
        BusinessFamily.OFFICE: '["office"]',
        BusinessFamily.FOOD: f'["amenity"~"^({"|".join(OpenMapTrades.FOOD_PLACE_LABELS)})$"]',
        BusinessFamily.LODGING: f'["tourism"~"^({"|".join(OpenMapTrades.LODGING_LABELS)})$"]',
    }
    _WEBSITE_TAGS: ClassVar[tuple[str, ...]] = ("website", "contact:website")

    async def businesses_of(self, department: str, families: Sequence[BusinessFamily]) -> list[ListedBusiness]:
        """
        The businesses of a département that have a site of their own.

        Args:
            department: The département's code (« 35 »).
            families: The families asked for.

        Returns:
            One business per site.

        Raises:
            OpenMapUnavailableError: The open map did not answer after several tries.
        """
        return OpenMapAnswer.businesses_of(await self._answer_to(self.query_of(department, families)), families)

    @classmethod
    def query_of(cls, department: str, families: Sequence[BusinessFamily]) -> str:
        """
        The question asked to the open map for a département.

        Args:
            department: The département's code.
            families: The families asked for.

        Returns:
            An Overpass query answering one tab-separated line per object, in the order of the answer's columns.
        """
        columns: str = ",".join(
            column if column.startswith("::") else f'"{column}"' for column in OpenMapAnswer.COLUMNS
        )
        selections: str = "".join(
            f'nwr{cls._FAMILY_FILTERS[family]}["{website_tag}"](area.zone);'
            for family in families
            for website_tag in cls._WEBSITE_TAGS
        )
        return (
            f'[out:csv({columns};true;"\\t")][timeout:{cls._QUERY_TIMEOUT_SECONDS}];'
            'area["boundary"="administrative"]["admin_level"="6"]'
            f'["ref:INSEE"~"^({"|".join(FrenchDepartments.open_map_codes_of(department))})$"]->.zone;'
            f"({selections});out center;"
        )

    async def _answer_to(self, query: str) -> str:
        """Send a query to the open map, asking again when its server is busy."""
        timeout: httpx.Timeout = httpx.Timeout(self._QUERY_TIMEOUT_SECONDS + 30.0, connect=15.0)
        failure: str = ""
        async with httpx.AsyncClient(timeout=timeout, headers=self._REQUEST_HEADERS) as client:
            for attempt in range(self._ATTEMPTS):
                if attempt:
                    await asyncio.sleep(self._SECONDS_BEFORE_ASKING_AGAIN)
                try:
                    response: httpx.Response = await client.post(self._SERVER_URL, data={"data": query})
                except httpx.HTTPError as exc:
                    failure = type(exc).__name__
                    continue
                if response.status_code == httpx.codes.OK:
                    return response.text
                failure = f"HTTP {response.status_code}"
        raise OpenMapUnavailableError(f"OpenStreetMap ne répond pas ({failure}).")


class TownLocator:
    """Names the French commune a point is in, from the official list of communes (geo.api.gouv.fr)."""

    _COMMUNES_URL: ClassVar[str] = "https://geo.api.gouv.fr/communes"
    _TIMEOUT_SECONDS: ClassVar[float] = 2.0
    _ATTEMPTS: ClassVar[int] = 2
    _REST_SECONDS_AFTER_NO_ANSWER: ClassVar[float] = 120.0

    def __init__(self) -> None:
        self._resting_until: float = 0.0

    @property
    def is_resting(self) -> bool:
        """Whether the list of communes is left alone for a while, after it failed to answer."""
        return time.monotonic() < self._resting_until

    async def town_at(self, latitude: float, longitude: float) -> str | None:
        """
        The commune a point is in.

        Args:
            latitude: The point's latitude.
            longitude: The point's longitude.

        Returns:
            The commune's name; None when the point is in no commune, and while the list rests or fails to
            answer (:attr:`is_resting` then tells the two apart).
        """
        if self.is_resting:
            return None
        failure: str = ""
        for _ in range(self._ATTEMPTS):
            try:
                # A new connection each time: the one that got no answer would be asked again otherwise.
                async with httpx.AsyncClient(timeout=self._TIMEOUT_SECONDS) as client:
                    response: httpx.Response = await client.get(
                        self._COMMUNES_URL,
                        params={"lat": latitude, "lon": longitude, "fields": "nom", "format": "json"},
                    )
                    response.raise_for_status()
                    communes: list[dict[str, Any]] = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                failure = type(exc).__name__
                continue
            return str(communes[0]["nom"])[:120] if communes and communes[0].get("nom") else None
        self._resting_until = time.monotonic() + self._REST_SECONDS_AFTER_NO_ANSWER
        logger.warning("[SiteCare] the list of communes does not answer (%s): left alone for a while", failure)
        return None


open_map_directory = OpenMapDirectory()
town_locator = TownLocator()
