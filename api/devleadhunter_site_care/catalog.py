"""What the module knows whatever the site: the twelve points, the kinds of issue, the corrections and their prices."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class PointKey(StrEnum):
    """One of the twelve things looked at on a site, in the order a sheet lists them."""

    HTTPS = "https"
    PHP = "php"
    CMS = "cms"
    HACKED = "hacked"
    CONTACT_MAIL = "contact_mail"
    SPF = "spf"
    DMARC = "dmarc"
    GOOGLE_PHONE = "google_phone"
    TEL_LINK = "tel_link"
    YEAR = "year"
    MOBILE = "mobile"
    SEARCH = "search"


class PointState(StrEnum):
    """What a point says: worth a fix, worth an eye, fine, or not readable from outside."""

    FIX = "fix"
    WATCH = "watch"
    OK = "ok"
    UNKNOWN = "unknown"


class IssueKind(StrEnum):
    """The kind of issue a point is, as the list names it at a glance."""

    HACK = "hack"
    SECURITY = "security"
    RISK = "risk"
    LATE = "late"
    MAIL = "mail"
    MOBILE = "mobile"
    CONTACT = "contact"
    DATED = "dated"
    GOOGLE = "google"
    OK = "ok"
    REVIEW = "review"


class CorrectionKey(StrEnum):
    """A fixed-price correction the module offers."""

    CLEANUP = "cleanup"
    PHP = "php"
    CMS = "cms"
    HTTPS = "https"
    MAIL = "mail"
    SEARCH = "search"
    TOUCHUP = "touchup"
    MOBILE = "mobile"


class SiteStatus(StrEnum):
    """Where a site stands after its check."""

    TO_WRITE = "to_write"
    NOTHING = "nothing"
    UNREACHABLE = "unreachable"
    UNREADABLE = "unreadable"


class SiteTab(StrEnum):
    """The tab of « Mes prospects » a site falls under."""

    TO_WRITE = "to_write"
    WRITTEN = "written"
    NO_EMAIL = "no_email"
    NOTHING = "nothing"
    REVIEW = "review"
    ALL = "all"


class WritingTrigger(StrEnum):
    """When a site deserves a message."""

    FIX = "fix"
    WATCH = "watch"


@dataclass(frozen=True)
class PointDefinition:
    """
    A point, whatever the site.

    Attributes:
        key: The point.
        family_label: The family it is listed under in the settings.
        label: Its name in the settings.
        good_words: How the sheet names it among the points that are fine (« le cadenas »).
        correction: The correction that fixes it.
    """

    key: PointKey
    family_label: str
    label: str
    good_words: str
    correction: CorrectionKey


@dataclass(frozen=True)
class CorrectionDefinition:
    """
    A correction and its default price.

    Attributes:
        key: The correction.
        label: Its name in the settings and on a sheet.
        default_price_cents: Its price, None when it is quoted after a look at the site.
        is_quoted: True when the correction never has a fixed price.
    """

    key: CorrectionKey
    label: str
    default_price_cents: int | None
    is_quoted: bool = False


POINTS: tuple[PointDefinition, ...] = (
    PointDefinition(PointKey.HTTPS, "Sécurité", "Cadenas de sécurité (https)", "le cadenas", CorrectionKey.HTTPS),
    PointDefinition(PointKey.PHP, "Sécurité", "Moteur du site (PHP)", "le moteur du site", CorrectionKey.PHP),
    PointDefinition(PointKey.CMS, "Sécurité", "Logiciel du site", "le logiciel du site", CorrectionKey.CMS),
    PointDefinition(PointKey.HACKED, "Sécurité", "Piratage", "aucun piratage", CorrectionKey.CLEANUP),
    PointDefinition(
        PointKey.CONTACT_MAIL, "E-mails", "Adresse e-mail affichée", "l’adresse e-mail", CorrectionKey.MAIL
    ),
    PointDefinition(PointKey.SPF, "E-mails", "Expéditeur reconnu", "l’expéditeur des e-mails", CorrectionKey.MAIL),
    PointDefinition(
        PointKey.DMARC, "E-mails", "Protection du nom de domaine", "la protection du nom", CorrectionKey.MAIL
    ),
    PointDefinition(
        PointKey.GOOGLE_PHONE,
        "Coordonnées",
        "Numéro de la fiche Google",
        "le numéro de la fiche Google",
        CorrectionKey.TOUCHUP,
    ),
    PointDefinition(PointKey.TEL_LINK, "Coordonnées", "Numéro cliquable", "le numéro cliquable", CorrectionKey.TOUCHUP),
    PointDefinition(
        PointKey.YEAR, "Coordonnées", "Année en bas de page", "l’année en bas de page", CorrectionKey.TOUCHUP
    ),
    PointDefinition(
        PointKey.MOBILE, "Visibilité", "Lecture sur téléphone", "la lecture sur téléphone", CorrectionKey.MOBILE
    ),
    PointDefinition(
        PointKey.SEARCH, "Visibilité", "Présentation dans Google", "la présentation dans Google", CorrectionKey.SEARCH
    ),
)
POINT_BY_KEY: dict[PointKey, PointDefinition] = {point.key: point for point in POINTS}
# « "php" in PointKey » raises on Python 3.11, the production interpreter: compare with the values instead.
POINT_KEY_VALUES: frozenset[str] = frozenset(key.value for key in PointKey)

CORRECTIONS: tuple[CorrectionDefinition, ...] = (
    CorrectionDefinition(CorrectionKey.CLEANUP, "Nettoyage du site après piratage", 39000),
    CorrectionDefinition(CorrectionKey.PHP, "Passage à une version de PHP suivie", 19000),
    CorrectionDefinition(CorrectionKey.CMS, "Mise à jour du site et de ses extensions", 19000),
    CorrectionDefinition(CorrectionKey.HTTPS, "Mise en place du cadenas (https)", 9000),
    CorrectionDefinition(CorrectionKey.MAIL, "Réglage des e-mails du domaine", 9000),
    CorrectionDefinition(CorrectionKey.SEARCH, "Présentation dans Google", 9000),
    CorrectionDefinition(CorrectionKey.TOUCHUP, "Petites retouches : numéro, année", 6000),
    CorrectionDefinition(CorrectionKey.MOBILE, "Adaptation au téléphone", None, is_quoted=True),
)
CORRECTION_BY_KEY: dict[CorrectionKey, CorrectionDefinition] = {
    correction.key: correction for correction in CORRECTIONS
}
CORRECTION_KEY_VALUES: frozenset[str] = frozenset(key.value for key in CorrectionKey)
DEFAULT_MONTHLY_PRICE_CENTS: int = 10000

KIND_LABELS: dict[IssueKind, str] = {
    IssueKind.HACK: "Site piraté",
    IssueKind.SECURITY: "Sécurité",
    IssueKind.RISK: "Version à risque",
    IssueKind.LATE: "Mise à jour en retard",
    IssueKind.MAIL: "E-mails",
    IssueKind.MOBILE: "Sur téléphone",
    IssueKind.CONTACT: "Coordonnées",
    IssueKind.DATED: "Site daté",
    IssueKind.GOOGLE: "Dans Google",
    IssueKind.OK: "Rien à signaler",
    IssueKind.REVIEW: "À revoir",
}
# How « Aussi : … » names the other issues of a site.
KIND_WORDS: dict[IssueKind, str] = {
    IssueKind.HACK: "piratage",
    IssueKind.SECURITY: "sécurité",
    IssueKind.RISK: "version à risque",
    IssueKind.LATE: "mise à jour en retard",
    IssueKind.MAIL: "e-mails",
    IssueKind.MOBILE: "affichage sur téléphone",
    IssueKind.CONTACT: "coordonnées",
    IssueKind.DATED: "site daté",
    IssueKind.GOOGLE: "présentation dans Google",
}

# The point that leads a sheet and its message: the most pressing fix first, then the most pressing watch.
FIX_LEAD_ORDER: tuple[PointKey, ...] = (
    PointKey.HACKED,
    PointKey.HTTPS,
    PointKey.PHP,
    PointKey.CMS,
    PointKey.SPF,
    PointKey.CONTACT_MAIL,
    PointKey.MOBILE,
)
WATCH_LEAD_ORDER: tuple[PointKey, ...] = (
    PointKey.PHP,
    PointKey.HTTPS,
    PointKey.CMS,
    PointKey.DMARC,
    PointKey.GOOGLE_PHONE,
    PointKey.YEAR,
    PointKey.TEL_LINK,
    PointKey.SEARCH,
)
# Corrections are offered in this order, the most pressing first.
CORRECTION_ORDER: tuple[CorrectionKey, ...] = (
    CorrectionKey.CLEANUP,
    CorrectionKey.HTTPS,
    CorrectionKey.PHP,
    CorrectionKey.CMS,
    CorrectionKey.MAIL,
    CorrectionKey.MOBILE,
    CorrectionKey.SEARCH,
    CorrectionKey.TOUCHUP,
)
# With the « watch » trigger, this many points to watch are enough to write.
WATCH_POINTS_WORTH_A_MESSAGE: int = 3

# Last day of security fixes of each PHP branch (php.net, « Supported Versions »).
PHP_SECURITY_END: dict[str, date] = {
    "5.6": date(2018, 12, 31),
    "7.0": date(2019, 1, 10),
    "7.1": date(2019, 12, 1),
    "7.2": date(2020, 11, 30),
    "7.3": date(2021, 12, 6),
    "7.4": date(2022, 11, 28),
    "8.0": date(2023, 11, 26),
    "8.1": date(2025, 12, 31),
    "8.2": date(2026, 12, 31),
    "8.3": date(2027, 12, 31),
    "8.4": date(2028, 12, 31),
    "8.5": date(2029, 12, 31),
}
# A PHP branch whose fixes stop within this many days is a date coming up.
PHP_END_COMING_UP_DAYS: int = 120
# A certificate that expires within this many days was not renewed in time (the renewal runs a month ahead).
CERTIFICATE_COMING_UP_DAYS: int = 20
# Fallback when wordpress.org does not answer: the branch current in November 2026.
WORDPRESS_FALLBACK_BRANCH: tuple[int, int] = (7, 1)

# Builders that update the site themselves: nothing to maintain for their client.
HOSTED_BUILDERS: frozenset[str] = frozenset(
    {
        "Wix",
        "Squarespace",
        "Solocal",
        "Local.fr",
        "Duda",
        "Webflow",
        "Webador",
        "Odoo",
        "Linkeo",
        "Jimdo",
        "Webnode",
        "GoDaddy",
        "IONOS",
        "Shopify",
        "Simplébo",
        "e-monsite",
        "Hostinger",
    }
)
# Hosts that are a page on someone else's platform, never a business's own site.
NOT_AN_OWN_SITE_HOSTS: tuple[str, ...] = (
    "facebook.",
    "instagram.",
    "linkedin.",
    "google.",
    "pagesjaunes.",
    "yelp.",
    "linktr.ee",
    "wa.me",
    "tripadvisor.",
    "youtube.",
    "tiktok.",
)
