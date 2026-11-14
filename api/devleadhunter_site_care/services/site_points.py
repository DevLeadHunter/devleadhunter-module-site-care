"""
Turns what was read on a site into its twelve points: a state, a plain sentence, a kind of issue and a technology.

The sentences are the module's voice: the sheet, the list and the message all repeat them, so a fact is worded once.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from devleadhunter_site_care.catalog import (
    CERTIFICATE_COMING_UP_DAYS,
    HOSTED_BUILDERS,
    PHP_END_COMING_UP_DAYS,
    PHP_SECURITY_END,
    IssueKind,
    PointKey,
    PointState,
)
from devleadhunter_site_care.services.site_reader import SiteReading

_MONTHS: tuple[str, ...] = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)
_UNREACHABLE_FACT: str = "Le site ne répond plus : le contrôle n’a pas pu être fait."
_UNREADABLE_FACT: str = "Le site n’a pas pu être lu automatiquement : à regarder à la main."
_DOUBTFUL_ADDRESS_FACT: str = (
    "L’adresse affiche des jeux d’argent sans les cacher : le site n’est peut-être plus celui de l’entreprise."
)


class FrenchDates:
    """Dates the way a French letter writes them."""

    @staticmethod
    def day(moment: date) -> str:
        """A day as « 1er décembre » or « 29 novembre »."""
        return f"{'1er' if moment.day == 1 else moment.day} {_MONTHS[moment.month - 1]}"

    @staticmethod
    def full(moment: date) -> str:
        """A day with its year, as « 31 décembre 2026 »."""
        return f"{FrenchDates.day(moment)} {moment.year}"

    @staticmethod
    def month_year(moment: date) -> str:
        """A month with its year, as « novembre 2022 »."""
        return f"{_MONTHS[moment.month - 1]} {moment.year}"


@dataclass
class SitePoint:
    """
    One point as read on one site.

    Attributes:
        key: The point.
        state: What it says.
        fact: The full sentence of the sheet and the message.
        sentence: The short sentence of the list, under the kind tag (empty for a point that is fine).
        kind: The kind of issue, None for a point that is fine or unknown.
        tech: The technology to name next to the kind (« PHP 7.4 »), empty when there is none.
        data: What the message and the page need to word this point (a version, a date).
    """

    key: PointKey
    state: PointState
    fact: str
    sentence: str = ""
    kind: IssueKind | None = None
    tech: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        """The point as a JSON-ready dictionary."""
        return {
            "key": self.key.value,
            "state": self.state.value,
            "fact": self.fact,
            "sentence": self.sentence,
            "kind": self.kind.value if self.kind else None,
            "tech": self.tech,
            "data": self.data,
        }

    @classmethod
    def from_json(cls, stored: dict[str, Any]) -> SitePoint:
        """
        Read a stored point back.

        Args:
            stored: What :meth:`to_json` wrote.

        Returns:
            The point.
        """
        return cls(
            key=PointKey(stored["key"]),
            state=PointState(stored["state"]),
            fact=stored["fact"],
            sentence=stored.get("sentence") or "",
            kind=IssueKind(stored["kind"]) if stored.get("kind") else None,
            tech=stored.get("tech") or "",
            data=stored.get("data") or {},
        )


class SitePointReader:
    """Reads the twelve points out of a site reading."""

    def __init__(self, *, today: date, wordpress_branch: tuple[int, int], listing_phone: str | None) -> None:
        """
        Args:
            today: The day of the check, which dates are compared with.
            wordpress_branch: The current WordPress branch, as (major, minor).
            listing_phone: The number of the business's Google listing, to look up on the page.
        """
        self._today: date = today
        self._wordpress_branch: tuple[int, int] = wordpress_branch
        self._listing_phone: str | None = listing_phone

    def points_of(self, reading: SiteReading) -> list[SitePoint]:
        """
        The twelve points of a site.

        Args:
            reading: What was read.

        Returns:
            The points in the catalogue's order; all unknown, with the reason, when the home page was not read
            or its address is doubtful.
        """
        if not reading.was_read:
            fact: str = _UNREADABLE_FACT if reading.was_reached else _UNREACHABLE_FACT
            return [SitePoint(key, PointState.UNKNOWN, fact) for key in PointKey]
        if reading.address_doubt is not None:
            return [SitePoint(key, PointState.UNKNOWN, _DOUBTFUL_ADDRESS_FACT) for key in PointKey]
        return [
            self._https(reading),
            self._php(reading),
            self._cms(reading),
            self._hacked(reading),
            self._contact_mail(reading),
            self._spf(reading),
            self._dmarc(reading),
            self._google_phone(reading),
            self._tel_link(reading),
            self._year(reading),
            self._mobile(reading),
            self._search(reading),
        ]

    def _https(self, reading: SiteReading) -> SitePoint:
        if reading.https == "absent" or reading.https == "redirects_to_http":
            return SitePoint(
                PointKey.HTTPS,
                PointState.FIX,
                "Le site s’ouvre sans cadenas : le navigateur affiche « Non sécurisé ».",
                "Pas de cadenas : le navigateur affiche « Non sécurisé »",
                IssueKind.SECURITY,
                data={"variant": "absent"},
            )
        if reading.https == "invalid_certificate":
            return SitePoint(
                PointKey.HTTPS,
                PointState.FIX,
                "Le certificat de sécurité du site n’est pas valable : le navigateur affiche un avertissement "
                "avant d’ouvrir la page.",
                "Certificat invalide : avertissement avant d’entrer",
                IssueKind.SECURITY,
                data={"variant": "invalid"},
            )
        end: datetime | None = reading.certificate_end
        if end is not None:
            days_left: int = (end.date() - self._today).days
            if 0 <= days_left <= CERTIFICATE_COMING_UP_DAYS:
                return SitePoint(
                    PointKey.HTTPS,
                    PointState.WATCH,
                    f"Le certificat expire le {FrenchDates.day(end.date())}, dans {days_left} jours, et n’a pas "
                    "été renouvelé.",
                    f"Certificat à renouveler avant le {FrenchDates.day(end.date())}",
                    IssueKind.SECURITY,
                    data={"variant": "expiring", "end_date": FrenchDates.day(end.date()), "days": days_left},
                )
        return SitePoint(PointKey.HTTPS, PointState.OK, "Le site s’ouvre avec le cadenas.")

    def _php(self, reading: SiteReading) -> SitePoint:
        version_match: re.Match[str] | None = re.search(r"PHP/(\d+\.\d+)", reading.powered_by or "")
        if version_match is None:
            return SitePoint(PointKey.PHP, PointState.UNKNOWN, "La version de PHP ne se voit pas de l’extérieur.")
        version: str = version_match.group(1)
        tech: str = f"PHP {version}"
        end: date | None = PHP_SECURITY_END.get(version)
        if end is None:
            major: int = int(version.split(".")[0])
            if major < 8:
                return SitePoint(
                    PointKey.PHP,
                    PointState.FIX,
                    f"Le site tourne avec PHP {version}, qui ne reçoit plus de correctifs de sécurité depuis "
                    "des années.",
                    "Plus de correctif de sécurité depuis des années",
                    IssueKind.RISK,
                    tech,
                    {"version": version, "end_year": "des années", "end_month_year": "des années"},
                )
            return SitePoint(PointKey.PHP, PointState.OK, f"PHP {version}, une version suivie.", tech=tech)
        if end < self._today:
            return SitePoint(
                PointKey.PHP,
                PointState.FIX,
                f"Le site tourne avec PHP {version}, qui ne reçoit plus de correctifs de sécurité depuis "
                f"{FrenchDates.month_year(end)}.",
                f"Plus de correctif de sécurité depuis {end.year}",
                IssueKind.RISK,
                tech,
                {"version": version, "end_year": str(end.year), "end_month_year": FrenchDates.month_year(end)},
            )
        if (end - self._today).days <= PHP_END_COMING_UP_DAYS:
            return SitePoint(
                PointKey.PHP,
                PointState.WATCH,
                f"Le site tourne avec PHP {version}, dont les correctifs de sécurité s’arrêtent le "
                f"{FrenchDates.full(end)}.",
                f"Les correctifs de sécurité s’arrêtent le {FrenchDates.day(end)}",
                IssueKind.LATE,
                tech,
                {"version": version, "end_date": FrenchDates.full(end), "end_iso": end.isoformat()},
            )
        return SitePoint(PointKey.PHP, PointState.OK, f"PHP {version}, une version suivie.", tech=tech)

    def _cms(self, reading: SiteReading) -> SitePoint:
        generators: str = " | ".join(reading.generators)
        wordpress: re.Match[str] | None = re.search(r"WordPress (\d+)\.(\d+)", generators)
        if wordpress is not None:
            branch: tuple[int, int] = (int(wordpress.group(1)), int(wordpress.group(2)))
            name: str = f"WordPress {branch[0]}.{branch[1]}"
            current: str = f"{self._wordpress_branch[0]}.{self._wordpress_branch[1]}"
            if branch >= self._wordpress_branch:
                return SitePoint(PointKey.CMS, PointState.OK, f"{name}, la version actuelle.", tech=name)
            if branch[0] >= self._wordpress_branch[0] - 1:
                return SitePoint(
                    PointKey.CMS,
                    PointState.WATCH,
                    f"{name}, alors que la version actuelle est la {current}.",
                    f"La version actuelle est la {current}",
                    IssueKind.LATE,
                    name,
                    {"name": name, "current": current},
                )
            return SitePoint(
                PointKey.CMS,
                PointState.FIX,
                f"{name}, une version ancienne qui n’est plus suivie.",
                "Une version ancienne, qui n’est plus suivie",
                IssueKind.RISK,
                name,
                {"name": name, "current": current},
            )
        if reading.cms in HOSTED_BUILDERS:
            return SitePoint(
                PointKey.CMS, PointState.OK, f"Site fait avec {reading.cms}, qui se charge des mises à jour."
            )
        return SitePoint(PointKey.CMS, PointState.UNKNOWN, "Le logiciel du site ne se voit pas de l’extérieur.")

    @staticmethod
    def _hacked(reading: SiteReading) -> SitePoint:
        if reading.has_hidden_gambling_link:
            return SitePoint(
                PointKey.HACKED,
                PointState.FIX,
                "La page d’accueil contient des liens cachés vers des sites de casino : le site a très "
                "probablement été piraté.",
                "Liens cachés vers des sites de casino",
                IssueKind.HACK,
                data={"hosts": reading.gambling_links},
            )
        return SitePoint(PointKey.HACKED, PointState.OK, "Aucun lien suspect sur la page d’accueil.")

    @staticmethod
    def _contact_mail(reading: SiteReading) -> SitePoint:
        if any(receives is False for receives in reading.shown_mail_domains.values()):
            return SitePoint(
                PointKey.CONTACT_MAIL,
                PointState.FIX,
                "L’adresse e-mail affichée sur le site ne peut pas recevoir de messages : son nom de domaine "
                "n’a pas de messagerie.",
                "L’adresse affichée ne reçoit pas les messages",
                IssueKind.MAIL,
            )
        if reading.emails:
            return SitePoint(
                PointKey.CONTACT_MAIL, PointState.OK, "L’adresse affichée sur le site reçoit bien les messages."
            )
        return SitePoint(PointKey.CONTACT_MAIL, PointState.UNKNOWN, "Aucune adresse e-mail sur la page d’accueil.")

    @staticmethod
    def _spf(reading: SiteReading) -> SitePoint:
        if reading.has_mail_server is None or reading.has_spf is None:
            return SitePoint(PointKey.SPF, PointState.UNKNOWN, "Les réglages du nom de domaine n’ont pas répondu.")
        if not reading.has_mail_server:
            return SitePoint(PointKey.SPF, PointState.OK, "Le domaine n’envoie pas d’e-mails : rien à régler.")
        if reading.has_spf:
            return SitePoint(PointKey.SPF, PointState.OK, "Les e-mails du domaine sont reconnus par les messageries.")
        return SitePoint(
            PointKey.SPF,
            PointState.FIX,
            "Le domaine envoie des e-mails sans dire qui en a le droit : ils risquent de finir en indésirables.",
            "Ses e-mails risquent les indésirables",
            IssueKind.MAIL,
        )

    @staticmethod
    def _dmarc(reading: SiteReading) -> SitePoint:
        if reading.has_mail_server is None or reading.has_dmarc is None:
            return SitePoint(PointKey.DMARC, PointState.UNKNOWN, "Les réglages du nom de domaine n’ont pas répondu.")
        if not reading.has_mail_server:
            return SitePoint(PointKey.DMARC, PointState.OK, "Le domaine n’envoie pas d’e-mails : rien à régler.")
        if reading.has_dmarc:
            return SitePoint(PointKey.DMARC, PointState.OK, "Le nom de domaine est protégé contre l’usurpation.")
        return SitePoint(
            PointKey.DMARC,
            PointState.WATCH,
            "Rien n’empêche quelqu’un d’envoyer des e-mails au nom du domaine.",
            "Nom de domaine non protégé contre l’usurpation",
            IssueKind.MAIL,
        )

    def _google_phone(self, reading: SiteReading) -> SitePoint:
        listing_digits: str = re.sub(r"\D", "", self._listing_phone or "")
        if len(listing_digits) < 8 or not reading.shows_phone:
            return SitePoint(
                PointKey.GOOGLE_PHONE, PointState.UNKNOWN, "Pas de numéro à comparer avec la fiche Google."
            )
        # The last eight digits are the same whatever the prefix the number is written with (0, +33, 0033).
        if listing_digits[-8:] in reading.page_digits:
            return SitePoint(PointKey.GOOGLE_PHONE, PointState.OK, "Le numéro est le même que sur la fiche Google.")
        return SitePoint(
            PointKey.GOOGLE_PHONE,
            PointState.WATCH,
            "Le numéro de la fiche Google n’est pas celui de la page d’accueil.",
            "Numéro différent de celui de la fiche Google",
            IssueKind.CONTACT,
        )

    @staticmethod
    def _tel_link(reading: SiteReading) -> SitePoint:
        if reading.has_tel_link:
            return SitePoint(PointKey.TEL_LINK, PointState.OK, "Sur téléphone, un appui sur le numéro lance l’appel.")
        if reading.shows_phone:
            return SitePoint(
                PointKey.TEL_LINK,
                PointState.WATCH,
                "Sur téléphone, il faut recopier le numéro pour appeler.",
                "Numéro à recopier pour appeler",
                IssueKind.MOBILE,
                data={"variant": "not_clickable"},
            )
        return SitePoint(
            PointKey.TEL_LINK,
            PointState.WATCH,
            "Aucun numéro de téléphone sur la page d’accueil.",
            "Aucun numéro sur la page d’accueil",
            IssueKind.CONTACT,
            data={"variant": "no_number"},
        )

    def _year(self, reading: SiteReading) -> SitePoint:
        if not reading.copyright_years:
            return SitePoint(PointKey.YEAR, PointState.UNKNOWN, "Pas d’année en bas de page.")
        year: int = max(reading.copyright_years)
        if year >= self._today.year - 1:
            return SitePoint(PointKey.YEAR, PointState.OK, "L’année du bas de page est à jour.")
        return SitePoint(
            PointKey.YEAR,
            PointState.WATCH,
            f"Le bas de page affiche « © {year} » : le site paraît à l’abandon.",
            f"« © {year} » en bas de page",
            IssueKind.DATED,
            data={"year": year},
        )

    @staticmethod
    def _mobile(reading: SiteReading) -> SitePoint:
        if reading.has_viewport:
            return SitePoint(PointKey.MOBILE, PointState.OK, "La page s’adapte à l’écran d’un téléphone.")
        return SitePoint(
            PointKey.MOBILE,
            PointState.FIX,
            "La page n’est pas prévue pour les téléphones : elle s’y affiche en tout petit.",
            "Page illisible sur un téléphone",
            IssueKind.MOBILE,
        )

    @staticmethod
    def _search(reading: SiteReading) -> SitePoint:
        if reading.has_description and reading.has_structured_data:
            return SitePoint(PointKey.SEARCH, PointState.OK, "Titre, description et fiche d’entreprise sont en place.")
        if not reading.has_description and not reading.has_structured_data:
            fact, variant = "Il manque la description et la fiche d’entreprise lues par Google et les IA.", "both"
        elif not reading.has_description:
            fact, variant = "Il manque la description que Google affiche sous le titre.", "description"
        else:
            fact, variant = "Il manque la fiche d’entreprise lue par Google et les IA.", "structured"
        return SitePoint(
            PointKey.SEARCH,
            PointState.WATCH,
            fact,
            "Présentation incomplète",
            IssueKind.GOOGLE,
            data={"variant": variant},
        )
