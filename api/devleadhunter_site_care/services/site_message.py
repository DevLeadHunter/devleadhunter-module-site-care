"""
Writes what leaves the module for a business owner: the first message, the page prepared for him, a client's report.

Everything is built from the site's stored check and the owner's settings; nothing here reads the network or the database.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote

from devleadhunter_site_care.catalog import CORRECTION_BY_KEY, POINT_BY_KEY, CorrectionKey
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings, Presenter
from devleadhunter_site_care.services.site_points import FrenchDates, SitePoint
from devleadhunter_site_care.services.site_summary import SiteSummary
from devleadhunter_site_care.services.site_wording import LeadWording, LeadWordings

_OFFER_NOTE_FIXED: str = "Une seule fois. Vous payez après la correction."
_OFFER_NOTE_QUOTED: str = "Je vous donne le prix avant de commencer. Vous payez après la correction."
_URL_PATTERN: re.Pattern[str] = re.compile(r"https?://[^\s<]+")
# What reassures an owner before a correction: on his site itself, or on the settings of his domain name.
_SITE_REASSURANCES: tuple[str, ...] = (
    "Je fais d’abord une sauvegarde complète.",
    "Je travaille sur une copie, pas sur votre site.",
    "Votre site garde la même présentation.",
)
_DOMAIN_REASSURANCES: tuple[str, ...] = (
    "Je ne touche pas à votre site.",
    "Vos e-mails continuent d’arriver pendant le réglage.",
    "Je vous explique ce que j’ai changé.",
)


class Money:
    """Prices the way the module writes them."""

    @staticmethod
    def euros(price_cents: int) -> str:
        """A price as « 190 € », cents shown only when there are some."""
        euros, cents = divmod(price_cents, 100)
        return f"{euros},{cents:02d} €" if cents else f"{euros} €"

    @staticmethod
    def label(price_cents: int | None) -> str:
        """A price, or « Sur devis » for a quoted correction."""
        return "Sur devis" if price_cents is None else Money.euros(price_cents)


@dataclass
class OutgoingMessage:
    """
    A message ready to be shown or sent.

    Attributes:
        subject: Its subject.
        paragraphs: Its paragraphs, in order, without the signature the core appends.
    """

    subject: str
    paragraphs: list[str] = field(default_factory=list)

    @property
    def body_html(self) -> str:
        """The paragraphs as the HTML body of an email, addresses turned into links."""
        return "".join(f"<p>{self._paragraph_html(paragraph)}</p>" for paragraph in self.paragraphs)

    @staticmethod
    def _paragraph_html(paragraph: str) -> str:
        """One paragraph escaped, its line breaks kept and its web addresses clickable."""
        escaped: str = html.escape(paragraph, quote=False)
        linked: str = _URL_PATTERN.sub(lambda match: f'<a href="{match.group(0)}">{match.group(0)}</a>', escaped)
        return linked.replace("\n", "<br>")


@dataclass
class SiteSubject:
    """
    The site a message or a page is about.

    Attributes:
        business_name: The business.
        domain: The site's address without « www. ».
        page_url: The address of the page prepared for the owner.
    """

    business_name: str
    domain: str
    page_url: str


class SiteMessageWriter:
    """Writes the messages and the page of one site."""

    def __init__(self, subject: SiteSubject, summary: SiteSummary, settings: OwnerSettings) -> None:
        """
        Args:
            subject: The site written about.
            summary: Its check, summed up.
            settings: The owner's prices and presentation.
        """
        self._subject: SiteSubject = subject
        self._summary: SiteSummary = summary
        self._settings: OwnerSettings = settings

    def first_message(self, *, with_page_link: bool) -> OutgoingMessage | None:
        """
        The first message to the business.

        Args:
            with_page_link: Whether the message sends the owner to the page prepared for him.

        Returns:
            The message, or None when no point leads the site.
        """
        lead: SitePoint | None = self._summary.lead
        if lead is None:
            return None
        wording: LeadWording = LeadWordings.of(lead, self._subject.domain)
        good_count: int = len(self._summary.good_words)
        looked_count: int = (
            good_count + len(self._summary.hidden_words) + len(self._summary.fixes) + len(self._summary.watches)
        )
        rest: str = (
            "J’ai regardé le reste de votre site, comme un visiteur. Tout est noté sur cette page : "
            f"{self._subject.page_url}"
            if with_page_link
            else "J’ai regardé le reste de votre site, comme un visiteur : "
            f"{good_count} points sur {looked_count} sont bons."
        )
        return OutgoingMessage(
            subject=wording.subject,
            paragraphs=[
                "Bonjour,",
                f"{self._introduction()} En regardant le site {self._of_business()}, j’ai vu que "
                f"{self._lower_first(lead.fact)}",
                f"Vous pouvez le vérifier vous-même : {self._lower_first(wording.proof_sentence)}",
                rest,
                f"{self._price_sentence(lead)} Si cela ne vous intéresse pas, dites-le-moi et je ne vous recontacte "
                "plus.",
                "Bonne journée,",
            ],
        )

    def monthly_report(self, checked_at: datetime) -> OutgoingMessage:
        """
        The monthly report of a client under care.

        Args:
            checked_at: When the site was last checked.

        Returns:
            The report: what was looked at, and what was found.
        """
        issues: list[SitePoint] = self._summary.fixes + self._summary.watches
        paragraphs: list[str] = [
            "Bonjour,",
            f"Voici le rapport du mois pour votre site {self._subject.domain}. Je l’ai regardé le "
            f"{FrenchDates.full(checked_at.date())}.",
        ]
        if issues:
            paragraphs.append("Ce que j’ai relevé :\n" + "\n".join(f"- {point.fact}" for point in issues))
            paragraphs.append("Je m’en occupe et je vous tiens au courant.")
        else:
            paragraphs.append(f"Tout est en ordre : {self._good_sentence()}")
        paragraphs.append("Bonne journée,")
        return OutgoingMessage(subject=f"Le rapport du mois pour {self._subject.domain}", paragraphs=paragraphs)

    def page(self, *, reply_address: str | None) -> dict[str, object] | None:
        """
        The page prepared for the owner, as the public route returns it.

        Args:
            reply_address: Where « Me répondre » writes to, None when no address is known yet.

        Returns:
            The page's content, or None when no point leads the site.
        """
        lead: SitePoint | None = self._summary.lead
        if lead is None:
            return None
        wording: LeadWording = LeadWordings.of(lead, self._subject.domain)
        presenter: Presenter = self._settings.presenter
        price_cents: int | None = self._lead_price_cents(lead)
        other_fixes: list[SitePoint] = [point for point in self._summary.fixes if point is not lead]
        other_watches: list[SitePoint] = [point for point in self._summary.watches if point is not lead]
        return {
            "business_name": self._subject.business_name,
            "domain": self._subject.domain,
            "title": {"start": wording.title[0], "mark": wording.title[1], "end": wording.title[2]},
            "intro": (
                f"Bonjour, {self._lower_first(self._introduction())} J’ai regardé votre site "
                f"{self._subject.domain} comme le ferait un visiteur, sans rien y toucher."
            ),
            "seen": {"label": wording.seen_label, "lead": wording.seen_lead, "rest": wording.seen_rest},
            "changes": list(wording.changes),
            "proof_steps": list(wording.proof_steps),
            "offer": {
                "label": wording.offer_label,
                "price_label": Money.label(price_cents),
                "note": _OFFER_NOTE_QUOTED if price_cents is None else _OFFER_NOTE_FIXED,
                "tag_label": None if price_cents is None else "Prix fixe",
                "reassurances": list(
                    _DOMAIN_REASSURANCES
                    if POINT_BY_KEY[lead.key].correction == CorrectionKey.MAIL
                    else _SITE_REASSURANCES
                ),
            },
            "goods": [self._good_fact(point) for point in self._good_points()],
            "other_fixes": [point.fact for point in other_fixes],
            "watches": [point.fact for point in other_watches],
            "other_points_count": len(self._good_points()) + len(other_fixes) + len(other_watches),
            "presenter": {
                "name": presenter.name,
                "tagline": " ".join(part for part in (self._role_sentence(), presenter.tagline) if part),
                "site_url": presenter.site_url,
                "site_label": re.sub(r"^https?://(www\.)?", "", presenter.site_url).rstrip("/"),
                "photo_url": presenter.photo_url,
            },
            "reply_mailto": self._mailto(reply_address, f"Re: {wording.subject}", ""),
            "forward_mailto": self._mailto(
                reply_address,
                f"Re: {wording.subject}",
                "Bonjour,\n\nCe n’est pas moi qui gère le site. La personne à contacter est : ",
            ),
        }

    def _introduction(self) -> str:
        """« Je suis {name}, {role}. », from what the owner typed about himself."""
        presenter: Presenter = self._settings.presenter
        if presenter.name and presenter.role:
            return f"Je suis {presenter.name}, {presenter.role.rstrip('.')}."
        return f"Je suis {presenter.name}." if presenter.name else "Je m’occupe de sites internet."

    def _role_sentence(self) -> str:
        """The presenter's role as a sentence of the page (« Développeur web à Rennes. »)."""
        role: str = self._settings.presenter.role.strip().rstrip(".")
        return f"{role[0].upper()}{role[1:]}." if role else ""

    def _of_business(self) -> str:
        """The business's name after « le site » : « de Jardins Guillot », « d’Élagage Renaud », « des Jardins du Lac »."""
        name: str = self._subject.business_name
        if name.startswith("Les "):
            return f"des {name[4:]}"
        if name.startswith("Le "):
            return f"du {name[3:]}"
        return f"d’{name}" if re.match(r"[AEIOUYÉÈÊÀÂÎÔÛHaeiouyéèêàâîôûh]", name) else f"de {name}"

    def _lead_price_cents(self, lead: SitePoint) -> int | None:
        """The price of the correction that fixes the leading point."""
        correction: CorrectionKey = POINT_BY_KEY[lead.key].correction
        return None if CORRECTION_BY_KEY[correction].is_quoted else self._settings.prices.get(correction)

    def _price_sentence(self, lead: SitePoint) -> str:
        """What the correction costs, said before anything starts."""
        price_cents: int | None = self._lead_price_cents(lead)
        if price_cents is None:
            return "Je vous donne le prix de la correction avant de commencer."
        return f"La correction coûte {Money.euros(price_cents)}, une seule fois."

    def _good_points(self) -> list[str]:
        """The names of the points that are fine."""
        return self._summary.good_words

    def _good_fact(self, good_words: str) -> str:
        """A point that is fine, as a sentence of the page."""
        return _GOOD_FACTS.get(good_words, f"{good_words[0].upper()}{good_words[1:]} : rien à signaler.")

    def _good_sentence(self) -> str:
        """The points that are fine in one sentence (« 9 points sont bons : le cadenas, … »)."""
        count: int = len(self._summary.good_words)
        return f"{count} points sont bons : {', '.join(self._summary.good_words)}."

    @staticmethod
    def _lower_first(sentence: str) -> str:
        """A sentence with its first letter in lower case, to follow « j’ai vu que »."""
        return sentence[:1].lower() + sentence[1:]

    @staticmethod
    def _mailto(address: str | None, subject: str, body: str) -> str:
        """A ``mailto:`` link, empty when no address is known."""
        if not address:
            return ""
        query: str = f"subject={quote(subject)}" + (f"&body={quote(body)}" if body else "")
        return f"mailto:{address}?{query}"


# How the page says that a point is fine, by the point's short name in the catalogue.
_GOOD_FACTS: dict[str, str] = {
    "le cadenas": "Le cadenas de sécurité est en place.",
    "le moteur du site": "Le moteur de votre site est une version suivie.",
    "le logiciel du site": "Le logiciel de votre site est à jour.",
    "aucun piratage": "Aucun lien suspect sur votre page d’accueil.",
    "l’adresse e-mail": "L’adresse e-mail affichée sur votre site reçoit bien les messages.",
    "l’expéditeur des e-mails": "Vos e-mails sont reconnus par les messageries.",
    "la protection du nom": "Votre nom de domaine est protégé contre l’usurpation.",
    "le numéro de la fiche Google": "Le numéro de votre site est le même que sur votre fiche Google.",
    "le numéro cliquable": "Sur téléphone, un appui sur votre numéro lance l’appel.",
    "l’année en bas de page": "L’année affichée en bas de page est à jour.",
    "la lecture sur téléphone": "Le site se lit bien sur téléphone.",
    "la présentation dans Google": "Google a ce qu’il lui faut pour présenter votre site.",
}


class SheetLines:
    """The lines of a site's sheet that sum the check up for the owner of the module."""

    @staticmethod
    def good_line(summary: SiteSummary) -> str | None:
        """« 7 points sont bons : … », None when no point is fine."""
        count: int = len(summary.good_words)
        if count == 0:
            return None
        if count == 1:
            return f"1 point est bon : {summary.good_words[0]}."
        return f"{count} points sont bons : {', '.join(summary.good_words)}."

    @staticmethod
    def hidden_line(summary: SiteSummary) -> str | None:
        """What could not be seen from outside, None when everything was."""
        if not summary.hidden_words:
            return None
        return f"Pas visible de l’extérieur, donc pas contrôlé : {', '.join(summary.hidden_words)}."

    @staticmethod
    def check_summary(summary: SiteSummary) -> str:
        """One sentence on a client's last check, for the care plans."""
        if summary.fixes:
            return f"À corriger : {SheetLines._lower_first(summary.fixes[0].fact)}"
        if summary.watches:
            watch: SitePoint = summary.watches[0]
            label: str = POINT_BY_KEY[watch.key].good_words
            return (
                f"Un point à surveiller : {label}."
                if len(summary.watches) == 1
                else (f"{len(summary.watches)} points à surveiller, dont {label}.")
            )
        return "Tout est en ordre."

    @staticmethod
    def _lower_first(sentence: str) -> str:
        """A sentence with its first letter in lower case."""
        return sentence[:1].lower() + sentence[1:]
