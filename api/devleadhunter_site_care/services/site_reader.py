"""
Reads a business website the way a visitor does: one request for its home page, and the public DNS of its domain.

Nothing is submitted, no hidden path is requested, no login is tried. What is read is kept as plain facts
(:class:`SiteReading`); the twelve points they add up to are decided elsewhere
(:mod:`devleadhunter_site_care.services.site_points`).
"""

from __future__ import annotations

import asyncio
import logging
import re
import ssl
from dataclasses import asdict, dataclass, field
from datetime import datetime
from types import TracebackType
from typing import Any, ClassVar
from urllib.parse import urljoin, urlparse

import dns.asyncresolver
import dns.exception
import dns.resolver
import httpx

from core.clock import naive_utc_now
from services.prospect_search.trade_catalog import TradeCatalog, TradeProfile
from services.public_url_guard import PublicOnlyAsyncTransport
from services.website_liveness_service import WebsiteLivenessService

from devleadhunter_site_care.catalog import NOT_AN_OWN_SITE_HOSTS, AddressDoubt

logger = logging.getLogger(__name__)

_CERTIFICATE_DATE_FORMAT: str = "%b %d %H:%M:%S %Y %Z"
_STORED_DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S"


@dataclass
class SiteReading:
    """
    What one read of a site's home page and DNS showed.

    Attributes:
        host: The site's host, as typed in its address.
        read_at: When it was read (naive UTC).
        error: Why the site could not be reached at all, None when a page came back.
        timed_out: Whether the site was too slow to answer, which says nothing about its being online.
        status_code: HTTP status of the home page.
        https: ``ok``, ``absent`` (the site only answers in http), ``invalid_certificate`` or ``redirects_to_http``.
        certificate_end: When the certificate expires (naive UTC).
        powered_by: The ``X-Powered-By`` header, where a server names its PHP version.
        generators: The ``generator`` meta tags.
        cms: The software or builder recognised on the page.
        has_viewport: Whether the page declares a mobile viewport.
        has_description: Whether the page has a meta description.
        has_structured_data: Whether the page carries JSON-LD.
        has_tel_link: Whether a phone number is a ``tel:`` link.
        shows_phone: Whether a phone number is written on the page.
        page_digits: Every digit of the visible text and the ``tel:`` links, to look a known number up in.
        emails: The email addresses shown on the page.
        copyright_years: The years written next to a copyright mark.
        gambling_links: The outside gambling sites the page links to.
        has_hidden_gambling_link: Whether one of those links is hidden from the visitor, the mark of a hacked page.
        has_gambling_title: Whether the page's own title sells gambling.
        host_on_another_domain: The host the home page was finally served from, when it is on another domain.
        has_mail_server: Whether the domain receives mail (MX); None when the lookup failed.
        has_spf: Whether the domain declares its senders; None when the lookup failed.
        has_dmarc: Whether the domain has a DMARC rule; None when the lookup failed.
        shown_mail_domains: For each domain of a shown address, whether it receives mail (None: lookup failed).
        contact_page_urls: Links of the home page to its contact and legal pages.
    """

    host: str
    read_at: datetime
    error: str | None = None
    timed_out: bool = False
    status_code: int | None = None
    https: str | None = None
    certificate_end: datetime | None = None
    powered_by: str | None = None
    generators: list[str] = field(default_factory=list)
    cms: str | None = None
    has_viewport: bool = False
    has_description: bool = False
    has_structured_data: bool = False
    has_tel_link: bool = False
    shows_phone: bool = False
    page_digits: str = ""
    emails: list[str] = field(default_factory=list)
    copyright_years: list[int] = field(default_factory=list)
    gambling_links: list[str] = field(default_factory=list)
    has_hidden_gambling_link: bool = False
    has_gambling_title: bool = False
    host_on_another_domain: str | None = None
    has_mail_server: bool | None = None
    has_spf: bool | None = None
    has_dmarc: bool | None = None
    shown_mail_domains: dict[str, bool | None] = field(default_factory=dict)
    contact_page_urls: list[str] = field(default_factory=list)

    @property
    def was_reached(self) -> bool:
        """Whether the site is there: a page came back, or it was only too slow to answer in time."""
        return self.timed_out or (self.error is None and self.status_code is not None)

    @property
    def was_read(self) -> bool:
        """Whether the home page itself was read (a refusal or an error page is not the home page)."""
        return self.error is None and self.status_code is not None and 200 <= self.status_code < 300

    @property
    def address_doubt(self) -> AddressDoubt | None:
        """Why the address may no longer be the business's own, None when nothing says so."""
        if not self.was_read:
            return None
        if self.host_on_another_domain is not None and (self.gambling_links or self.has_gambling_title):
            return AddressDoubt.LEADS_TO_GAMBLING_SITE
        if self.has_gambling_title:
            return AddressDoubt.TITLE_SELLS_GAMBLING
        if self.gambling_links and not self.has_hidden_gambling_link:
            return AddressDoubt.VISIBLE_GAMBLING_LINK
        return None

    def to_json(self) -> dict[str, Any]:
        """The reading as a JSON-ready dictionary."""
        stored: dict[str, Any] = asdict(self)
        stored["read_at"] = self.read_at.strftime(_STORED_DATE_FORMAT)
        stored["certificate_end"] = self.certificate_end.strftime(_STORED_DATE_FORMAT) if self.certificate_end else None
        # The digits only serve the comparison made right after the read.
        stored.pop("page_digits")
        return stored

    @classmethod
    def from_json(cls, stored: dict[str, Any]) -> SiteReading:
        """
        Read a stored reading back.

        Args:
            stored: What :meth:`to_json` wrote.

        Returns:
            The reading, without the page's digits.
        """
        values: dict[str, Any] = {key: value for key, value in stored.items() if key in cls.__dataclass_fields__}
        values["read_at"] = datetime.strptime(stored["read_at"], _STORED_DATE_FORMAT)
        certificate_end: str | None = stored.get("certificate_end")
        values["certificate_end"] = datetime.strptime(certificate_end, _STORED_DATE_FORMAT) if certificate_end else None
        return cls(**values)


class SiteAddress:
    """Reads the parts of a website address."""

    @staticmethod
    def host_of(website: str) -> str:
        """
        The host of a website address.

        Args:
            website: The address, with or without its scheme.

        Returns:
            The host in lower case, empty when the address has none.
        """
        return urlparse(website if "//" in website else f"https://{website}").netloc.lower().split("@")[-1]

    @staticmethod
    def bare_host(host: str) -> str:
        """The host without « www. », as a visitor names the site."""
        return host.removeprefix("www.")

    @staticmethod
    def mail_domain_of(host: str) -> str:
        """
        The domain a business on this host sends its mail from.

        Args:
            host: The site's host.

        Returns:
            The last two labels of the host.
        """
        labels: list[str] = SiteAddress.bare_host(host).split(".")
        return ".".join(labels[-2:]) if len(labels) > 2 else ".".join(labels)

    @staticmethod
    def host_on_another_domain(host: str, page_url: str) -> str | None:
        """
        The host a page was served from, when the site's address led to another domain.

        Args:
            host: The site's host.
            page_url: The address the page finally came from, once the redirects were followed.

        Returns:
            That host without « www. », None when the page stayed on the site's own domain.
        """
        page_host: str = SiteAddress.bare_host(SiteAddress.host_of(page_url))
        is_same_domain: bool = SiteAddress.mail_domain_of(page_host) == SiteAddress.mail_domain_of(host)
        return None if is_same_domain or not page_host else page_host

    @staticmethod
    def is_own_site(
        website: str, host: str, business_name: str, typed_trade: str, google_category: str | None = None
    ) -> bool:
        """
        Whether an address is the business's own site.

        Args:
            website: The site's address.
            host: Its host without « www. ».
            business_name: The business.
            typed_trade: Its trade, as the source names it.
            google_category: The category of its Google listing, when it has one.

        Returns:
            False for a page on someone else's platform, a directory's mini-site or a network's outlet.
        """
        if any(marker in host for marker in NOT_AN_OWN_SITE_HOSTS):
            return False
        if WebsiteLivenessService.is_placeholder_host(WebsiteLivenessService.normalize_url(website)):
            return False
        profile: TradeProfile = TradeCatalog.resolve(typed_trade)
        return (
            profile.brand_of_site(website) is None and profile.brand_outlet_of(business_name, google_category) is None
        )


class HomePageFacts:
    """Reads the facts of a home page out of its HTML."""

    PUBLIC_MAILBOX_DOMAINS: ClassVar[frozenset[str]] = frozenset(
        {
            "gmail.com",
            "orange.fr",
            "wanadoo.fr",
            "hotmail.fr",
            "hotmail.com",
            "outlook.fr",
            "outlook.com",
            "yahoo.fr",
            "yahoo.com",
            "free.fr",
            "sfr.fr",
            "laposte.net",
            "live.fr",
            "icloud.com",
            "bbox.fr",
            "neuf.fr",
            "aol.com",
            "gmx.fr",
            "gmx.ch",
            "bluewin.ch",
            "numericable.fr",
            "msn.com",
            "me.com",
            "skynet.be",
            "videotron.ca",
        }
    )
    # Technical marks only (a path, a script host, a generator): a page that merely talks about a tool is not built with it.
    CMS_MARKERS: ClassVar[tuple[tuple[str, tuple[str, ...]], ...]] = (
        ("WordPress", ("wp-content/", "wp-includes/")),
        ("Joomla", ("/media/jui/", "/media/system/js/", 'content="joomla!')),
        ("Wix", ("static.wixstatic.com", "static.parastorage.com")),
        ("Jimdo", ("jimdofree.com", "jimstatic.com", "jimdosite.com")),
        ("Squarespace", ("static1.squarespace.com", "squarespace-cdn.com")),
        ("Webflow", ("data-wf-site", "assets.website-files.com")),
        ("PrestaShop", ("var prestashop", 'content="prestashop')),
        ("Drupal", ("drupal-settings-json", "/sites/default/files/")),
        ("Shopify", ("cdn.shopify.com",)),
        ("Solocal", ("site-privilege.pagesjaunes", "solocal.com/")),
        ("Local.fr", ("cdn.local.fr", "static.local.fr")),
        ("Simplébo", ("simplebo.net", "simplebo.fr")),
        ("e-monsite", ("e-monsite.com",)),
        ("Webador", ("webador.com", "jouwweb")),
        ("Odoo", ("/web/assets/", 'content="odoo')),
        ("Duda", ("dudaone.com", "multiscreensite.com")),
        ("Linkeo", ("linkeo.com",)),
        ("Webnode", ("webnode.page", "webnode.com")),
        ("GoDaddy", ("img1.wsimg.com",)),
        ("IONOS", ("website-start.de", "ionos-website")),
        ("Hostinger", ('content="hostinger', "zyrosite.com")),
    )
    # Words no honest local business uses; « casino » alone is left out on purpose (a supermarket, a town's casino).
    GAMBLING_PATTERNS: ClassVar[tuple[re.Pattern[str], ...]] = tuple(
        re.compile(pattern, re.IGNORECASE)
        for pattern in (
            r"\bbahis\b",
            r"\btogel\b",
            r"\bslot\s*gacor\b",
            r"\bslot\s+online\b",
            r"\bsitus\s+(?:slot|judi|togel|toto)\b",
            r"\bbandar\s+(?:slot|togel|toto)\b",
            r"\bjudi\s+(?:online|slot|bola)\b",
            r"\bdeneme\s+bonusu\b",
            r"\bsbobet\b",
            r"\bcasino\s+(?:online|en\s+ligne|siteleri)\b",
            r"\bonline\s+casino\b",
            r"\bmachines?\s+à\s+sous\s+en\s+ligne\b",
            r"\bpoker\s+online\b",
            r"\bbonus\s+veren\b",
        )
    )
    _OUTSIDE_LINK: ClassVar[re.Pattern[str]] = re.compile(
        r'<a[^>]+href=["\'](?P<href>https?://[^"\']+)["\'][^>]*>(?P<label>[^<]{0,120})', re.IGNORECASE
    )
    _STYLED_TAG: ClassVar[re.Pattern[str]] = re.compile(
        r"<(?P<tag>[a-z][a-z0-9]*)\b[^>]*?(?<![\w-])style\s*=\s*"
        r"(?P<quote>[\"'])(?P<style>(?:(?!(?P=quote)).)*)(?P=quote)[^>]*>",
        re.IGNORECASE,
    )
    _HIDING_STYLE: ClassVar[re.Pattern[str]] = re.compile(
        r"(?<![\w-])(?:display\s*:\s*none|visibility\s*:\s*hidden"
        r"|(?:left|top|right|bottom|text-indent|margin-left|margin-top)\s*:\s*-\d{3,}"
        r"|(?:width|height|max-width|max-height|font-size|opacity)\s*:\s*0(?![.\d]))",
        re.IGNORECASE,
    )
    _TAGS_WITHOUT_CONTENT: ClassVar[frozenset[str]] = frozenset(
        {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
    )
    _EMAIL_ADDRESS: ClassVar[str] = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
    _IGNORED_EMAIL_MARKS: ClassVar[tuple[str, ...]] = ("sentry", "wixpress", "example", "domaine.", "votre-", "nom@")
    _IMAGE_SUFFIXES: ClassVar[tuple[str, ...]] = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")
    _CONTACT_LINK_WORDS: ClassVar[tuple[str, ...]] = ("contact", "mentions", "legal", "impressum")

    @classmethod
    def read_into(cls, reading: SiteReading, html: str, page_url: str) -> None:
        """
        Fill a reading with what the home page shows.

        Args:
            reading: The reading being built.
            html: The page's HTML.
            page_url: The address the page was served from, to resolve its links.
        """
        lowered: str = html.lower()
        visible: str = cls.visible_text(html)
        tel_links: list[str] = re.findall(r'href=["\']tel:([^"\']+)', html, flags=re.IGNORECASE)
        reading.generators = sorted(set(cls._generators(html)))[:6]
        reading.cms = next(
            (name for name, markers in cls.CMS_MARKERS if any(marker in lowered for marker in markers)), None
        )
        reading.has_viewport = bool(re.search(r'name=["\']viewport["\']', lowered))
        reading.has_description = bool(
            re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']\s*[^"\'\s]', html, flags=re.IGNORECASE)
            or re.search(
                r'<meta[^>]+content=["\']\s*[^"\'\s][^>]+name=["\']description["\']', html, flags=re.IGNORECASE
            )
        )
        reading.has_structured_data = "application/ld+json" in lowered
        reading.has_tel_link = bool(tel_links)
        reading.shows_phone = bool(tel_links) or bool(
            re.search(r"(?:\+|00)?\d(?:[\s.\-]?\d){8,13}", visible) and cls._has_phone_like_number(visible)
        )
        reading.page_digits = re.sub(r"\D", "", visible + " " + " ".join(tel_links))
        reading.emails = cls.emails_of(html, visible)
        reading.copyright_years = sorted(
            {
                int(year)
                for year in re.findall(r"(?:©|&copy;|copyright)[^<]{0,40}?(20\d{2})(?!\d)", html, flags=re.IGNORECASE)
            }
        )
        reading.gambling_links = cls.outside_gambling_links(html, reading.host)
        reading.has_hidden_gambling_link = cls.has_hidden_gambling_link(html, reading.host)
        reading.has_gambling_title = cls.is_gambling_text(cls.title_of(html))
        reading.host_on_another_domain = SiteAddress.host_on_another_domain(reading.host, page_url)
        reading.contact_page_urls = cls.contact_page_urls(html, page_url, reading.host)

    @staticmethod
    def visible_text(html: str) -> str:
        """
        The text a visitor reads on a page.

        Args:
            html: The page's HTML.

        Returns:
            The text, without scripts, styles and tags.
        """
        without_code: str = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", without_code))

    @classmethod
    def emails_of(cls, html: str, visible: str) -> list[str]:
        """
        The email addresses a page shows, in its text or its ``mailto:`` links.

        Args:
            html: The page's HTML.
            visible: Its visible text.

        Returns:
            The addresses in lower case, without the technical ones.
        """
        mailto: list[str] = re.findall(r'href=["\']mailto:([^"\'?]+)', html, flags=re.IGNORECASE)
        found: set[str] = {
            match.lower().strip(".") for match in re.findall(cls._EMAIL_ADDRESS, visible + " " + " ".join(mailto))
        }
        return sorted(
            email
            for email in found
            if not email.endswith(cls._IMAGE_SUFFIXES) and not any(mark in email for mark in cls._IGNORED_EMAIL_MARKS)
        )[:6]

    @classmethod
    def is_email_address(cls, text: str) -> bool:
        """
        Whether a text is one email address and nothing else.

        Args:
            text: What was typed, or what a source gives as an address.

        Returns:
            True for a single well-formed address.
        """
        return re.fullmatch(cls._EMAIL_ADDRESS, text) is not None

    @classmethod
    def outside_gambling_links(cls, html: str, host: str) -> list[str]:
        """
        The links of a page to outside gambling sites.

        Args:
            html: The page's HTML.
            host: The site's own host, whose links never count.

        Returns:
            The hosts linked, at most five.
        """
        return sorted({linked_host for _, linked_host in cls._outside_gambling_links(html, host)})[:5]

    @classmethod
    def has_hidden_gambling_link(cls, html: str, host: str) -> bool:
        """
        Whether a page hides a link to an outside gambling site from its visitor.

        Args:
            html: The page's HTML.
            host: The site's own host, whose links never count.

        Returns:
            True when such a link sits in a block its own style hides.
        """
        link_positions: list[int] = [position for position, _ in cls._outside_gambling_links(html, host)]
        if not link_positions:
            return False
        hidden_blocks: list[tuple[int, int]] = cls._hidden_blocks(html)
        return any(start <= position < end for position in link_positions for start, end in hidden_blocks)

    @classmethod
    def is_gambling_text(cls, text: str) -> bool:
        """
        Whether a text sells gambling.

        Args:
            text: A link with its label, or a page's title.

        Returns:
            True when it carries one of the words no honest local business uses.
        """
        return any(pattern.search(text.replace("-", " ")) for pattern in cls.GAMBLING_PATTERNS)

    @staticmethod
    def title_of(html: str) -> str:
        """
        The title of a page.

        Args:
            html: The page's HTML.

        Returns:
            The text of its ``<title>``, empty when it has none.
        """
        title: re.Match[str] | None = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        return re.sub(r"\s+", " ", title.group(1)).strip() if title else ""

    @classmethod
    def _outside_gambling_links(cls, html: str, host: str) -> list[tuple[int, str]]:
        """Where each link to an outside gambling site starts in the page, with the host it leads to."""
        own_domain: str = SiteAddress.mail_domain_of(host)
        links: list[tuple[int, str]] = []
        for link in cls._OUTSIDE_LINK.finditer(html):
            href: str = link.group("href")
            linked_host: str = SiteAddress.bare_host(SiteAddress.host_of(href))
            if not linked_host or linked_host == own_domain or linked_host.endswith(f".{own_domain}"):
                continue
            if cls.is_gambling_text(f"{href} {link.group('label')}"):
                links.append((link.start(), linked_host))
        return links

    @classmethod
    def _hidden_blocks(cls, html: str) -> list[tuple[int, int]]:
        """Where each block hidden by its own style starts and ends in the page."""
        blocks: list[tuple[int, int]] = []
        for opening in cls._STYLED_TAG.finditer(html):
            tag: str = opening.group("tag").lower()
            if tag in cls._TAGS_WITHOUT_CONTENT or not cls._HIDING_STYLE.search(opening.group("style")):
                continue
            blocks.append((opening.start(), cls._end_of_element(html, tag, opening.end())))
        return blocks

    @staticmethod
    def _end_of_element(html: str, tag: str, content_start: int) -> int:
        """Where an element closes, skipping the same tag nested inside it; the page's end when it never closes."""
        depth: int = 1
        same_tag: re.Pattern[str] = re.compile(rf"<(?P<closing>/?){re.escape(tag)}\b", re.IGNORECASE)
        for edge in same_tag.finditer(html, content_start):
            is_closing_tag: bool = bool(edge.group("closing"))
            depth += -1 if is_closing_tag else 1
            if depth == 0:
                return edge.start()
        return len(html)

    @classmethod
    def contact_page_urls(cls, html: str, page_url: str, host: str) -> list[str]:
        """
        The links of a home page to its own contact and legal pages, where an email address is usually written.

        Args:
            html: The page's HTML.
            page_url: The address the page was served from.
            host: The site's host: a link leaving it is ignored.

        Returns:
            At most three addresses, contact pages first.
        """
        own_host: str = SiteAddress.bare_host(host)
        found: list[str] = []
        for href in re.findall(r'<a[^>]+href=["\']([^"\'#]+)["\']', html, flags=re.IGNORECASE):
            if href.lower().startswith(("mailto:", "tel:", "javascript:")):
                continue
            if not any(word in href.lower() for word in cls._CONTACT_LINK_WORDS):
                continue
            absolute: str = urljoin(page_url, href)
            if SiteAddress.bare_host(SiteAddress.host_of(absolute)) != own_host or absolute in found:
                continue
            found.append(absolute)
        return sorted(found, key=lambda url: "contact" not in url.lower())[:3]

    @staticmethod
    def _generators(html: str) -> list[str]:
        """The contents of the page's ``generator`` meta tags, whichever attribute comes first."""
        return re.findall(
            r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', html, flags=re.IGNORECASE
        ) + re.findall(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']generator["\']', html, flags=re.IGNORECASE)

    @staticmethod
    def _has_phone_like_number(visible: str) -> bool:
        """Whether the text holds a number written like a phone number, with its usual international or 0 prefix."""
        return bool(re.search(r"(?:\+\d{2,3}|00\d{2,3}|\b0)\s?[1-9](?:[\s.\-]?\d{2,3}){3,4}\b", visible))


class SiteReader:
    """
    Reads sites one after another over shared connections, on the public internet only.

    Use as an async context manager; :meth:`read` never raises for a site that misbehaves.
    """

    REQUEST_HEADERS: ClassVar[dict[str, str]] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }
    _MAX_PAGE_BYTES: ClassVar[int] = 700_000
    _TIMEOUT: ClassVar[httpx.Timeout] = httpx.Timeout(20.0, connect=10.0)

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._unverified_client: httpx.AsyncClient | None = None
        self._resolver: dns.asyncresolver.Resolver = dns.asyncresolver.Resolver()
        self._resolver.timeout = 5
        self._resolver.lifetime = 8

    async def __aenter__(self) -> SiteReader:
        """Open the connections: one client that checks certificates, one that reads a page behind a bad one."""
        self._client = self._new_client(verify=True)
        self._unverified_client = self._new_client(verify=False)
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        """Close the connections."""
        for client in (self._client, self._unverified_client):
            if client is not None:
                await client.aclose()
        self._client = self._unverified_client = None

    async def read(self, website: str) -> SiteReading:
        """
        Read a site's home page and the DNS of its domain.

        Args:
            website: The site's address.

        Returns:
            What was read; its ``error`` says why when nothing answered.
        """
        host: str = SiteAddress.host_of(website)
        reading: SiteReading = SiteReading(host=host, read_at=naive_utc_now())
        if not host:
            reading.error = "Adresse de site illisible"
            return reading
        try:
            await self._read_home_page(reading)
        except Exception as exc:  # one odd site never stops the others
            logger.warning("[SiteCare] %s could not be read: %s", host, exc)
            reading.error = f"{type(exc).__name__}: {exc}"[:200]
        try:
            await self._read_dns(reading)
        except Exception as exc:
            logger.warning("[SiteCare] DNS of %s could not be read: %s", host, exc)
        return reading

    async def read_emails_of_pages(self, urls: list[str]) -> list[str]:
        """
        Read a few pages of a site and return the email addresses they show.

        Args:
            urls: The pages to read (the site's own contact and legal pages).

        Returns:
            The addresses found, in lower case.
        """
        found: set[str] = set()
        for url in urls:
            try:
                _, html, _ = await self._fetch(self._client_or_raise(verify=True), url)
            except httpx.HTTPError:
                continue
            found.update(HomePageFacts.emails_of(html, HomePageFacts.visible_text(html)))
        return sorted(found)

    async def _read_home_page(self, reading: SiteReading) -> None:
        """Fetch the home page in https, falling back to what a browser would still show, and read its facts."""
        host: str = reading.host
        response: httpx.Response | None = None
        html: str = ""
        try:
            response, html, reading.certificate_end = await self._fetch(
                self._client_or_raise(verify=True), f"https://{host}/"
            )
            reading.https = "ok"
        except httpx.ConnectError as exc:
            if self._is_certificate_error(exc):
                reading.https = "invalid_certificate"
                try:
                    response, html, _ = await self._fetch(self._client_or_raise(verify=False), f"https://{host}/")
                except httpx.HTTPError as second:
                    reading.error = f"{type(second).__name__}: {second}"[:200]
            else:
                try:
                    response, html, _ = await self._fetch(self._client_or_raise(verify=True), f"http://{host}/")
                    reading.https = "absent"
                except httpx.HTTPError as second:
                    reading.error = f"{type(second).__name__}: {second}"[:200]
        except httpx.HTTPError as exc:
            reading.error = f"{type(exc).__name__}: {exc}"[:200]
        reading.timed_out = response is None and "Timeout" in (reading.error or "")
        if response is None:
            return
        if reading.https == "ok" and str(response.url).startswith("http://"):
            reading.https = "redirects_to_http"
        reading.status_code = response.status_code
        reading.powered_by = response.headers.get("x-powered-by")
        if reading.was_read:
            HomePageFacts.read_into(reading, html, str(response.url))

    async def _fetch(self, client: httpx.AsyncClient, url: str) -> tuple[httpx.Response, str, datetime | None]:
        """
        Read one page, stopping once it is larger than any home page.

        Returns:
            The response, the page's text and the end date of the certificate it was served with.
        """
        async with client.stream("GET", url) as response:
            certificate_end: datetime | None = self._certificate_end_of(response)
            body: bytes = b""
            async for chunk in response.aiter_bytes():
                body += chunk
                if len(body) > self._MAX_PAGE_BYTES:
                    break
            return response, body.decode(response.encoding or "utf-8", "replace"), certificate_end

    async def _read_dns(self, reading: SiteReading) -> None:
        """Read the mail records of the site's domain and of the domains of the addresses it shows."""
        domain: str = SiteAddress.mail_domain_of(reading.host)
        mail_servers, text_records, dmarc_records = await asyncio.gather(
            self._records(domain, "MX"), self._records(domain, "TXT"), self._records(f"_dmarc.{domain}", "TXT")
        )
        reading.has_mail_server = None if mail_servers is None else bool(mail_servers)
        reading.has_spf = (
            None if text_records is None else any(record.lower().startswith("v=spf1") for record in text_records)
        )
        reading.has_dmarc = (
            None if dmarc_records is None else any(record.lower().startswith("v=dmarc1") for record in dmarc_records)
        )
        shown_domains: list[str] = sorted(
            {
                email.split("@")[1]
                for email in reading.emails
                if email.split("@")[1] not in HomePageFacts.PUBLIC_MAILBOX_DOMAINS
            }
        )[:3]
        for shown_domain in shown_domains:
            if shown_domain == domain:
                reading.shown_mail_domains[shown_domain] = reading.has_mail_server
                continue
            records: list[str] | None = await self._records(shown_domain, "MX")
            reading.shown_mail_domains[shown_domain] = None if records is None else bool(records)

    async def _records(self, name: str, record_type: str) -> list[str] | None:
        """The records of a name: an empty list when it has none, None when the lookup failed."""
        try:
            answer = await self._resolver.resolve(name, record_type)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return []
        except (dns.exception.DNSException, OSError):
            return None
        if record_type == "TXT":
            return [b"".join(record.strings).decode("utf-8", "replace") for record in answer]
        return [record.to_text() for record in answer]

    def _client_or_raise(self, *, verify: bool) -> httpx.AsyncClient:
        """The open client of the asked kind."""
        client: httpx.AsyncClient | None = self._client if verify else self._unverified_client
        if client is None:
            raise RuntimeError("SiteReader is used outside its context manager")
        return client

    def _new_client(self, *, verify: bool) -> httpx.AsyncClient:
        """A client that follows redirects and only ever connects to public addresses."""
        return httpx.AsyncClient(
            headers=self.REQUEST_HEADERS,
            follow_redirects=True,
            timeout=self._TIMEOUT,
            transport=PublicOnlyAsyncTransport(httpx.AsyncHTTPTransport(verify=verify)),
        )

    @staticmethod
    def _is_certificate_error(error: httpx.ConnectError) -> bool:
        """Whether a connection failed on the site's certificate, which a browser shows as a warning."""
        cause: BaseException | None = error.__cause__
        while cause is not None:
            if isinstance(cause, ssl.SSLCertVerificationError):
                return True
            cause = cause.__cause__
        return "CERTIFICATE_VERIFY_FAILED" in str(error)

    @staticmethod
    def _certificate_end_of(response: httpx.Response) -> datetime | None:
        """The end date of the certificate a response was served with, when the connection exposes it."""
        stream: Any = response.extensions.get("network_stream")
        ssl_object: Any = stream.get_extra_info("ssl_object") if stream is not None else None
        if ssl_object is None:
            return None
        not_after: str | None = (ssl_object.getpeercert() or {}).get("notAfter")
        if not not_after:
            return None
        try:
            return datetime.strptime(not_after, _CERTIFICATE_DATE_FORMAT)
        except ValueError:
            return None
