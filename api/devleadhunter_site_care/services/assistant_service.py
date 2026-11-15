"""
The assistant of the sites: a question in plain words, answered from the owner's own sites.

The language model only turns the question into a request (what to look for, with which filters). Every figure, line
and sentence of the answer is then read from the database, so the model can invent none of them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.orm import Session

from models.email_log import EmailLog
from schemas.module_assistant import (
    AssistantBar,
    AssistantChart,
    AssistantHighlight,
    AssistantHome,
    AssistantSuggestion,
)
from services.llm_service import llm_service

from devleadhunter_site_care.catalog import KIND_LABELS, IssueKind, SiteTab
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.schemas.assistant import SiteCareAssistantAnswer
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings, owner_settings_service
from devleadhunter_site_care.services.site_service import SiteListing, site_service
from devleadhunter_site_care.services.site_views import site_views


class AssistantIntent(StrEnum):
    """What a question asks for."""

    SEARCH = "search"
    COUNT = "count"
    REPLIES = "replies"


@dataclass(frozen=True)
class AssistantRequest:
    """
    A question, once understood.

    Attributes:
        intent: What it asks for.
        kind: The kind of issue wanted, None for any.
        place: Words of a town or a name to look for, None for none.
        tab: The tab of « Mes prospects » the sites are read from.
    """

    intent: AssistantIntent
    kind: IssueKind | None = None
    place: str | None = None
    tab: SiteTab = SiteTab.TO_WRITE


class AssistantService:
    """Understands a question about the sites and answers it from the database."""

    CARDS_SHOWN: ClassVar[int] = 6
    BARS_SHOWN: ClassVar[int] = 5
    LONGEST_PLACE: ClassVar[int] = 60
    SITE_PATH: ClassVar[str] = "/dashboard/site-care/sites"
    HACKED_QUESTION: ClassVar[str] = "Les sites piratés à contacter"
    COUNT_QUESTION: ClassVar[str] = "Combien de sites par type de souci ?"
    REPLIES_QUESTION: ClassVar[str] = "Qui m’a répondu ou a ouvert sa page ?"
    RISK_QUESTION: ClassVar[str] = "Les sites avec une version à risque"
    HOME: ClassVar[AssistantHome] = AssistantHome(
        lead="Posez une question sur vos sites, ou touchez une suggestion pour l’envoyer.",
        suggestions=[
            AssistantSuggestion(label=HACKED_QUESTION, tone="red", icon="i-lucide-shield-alert"),
            AssistantSuggestion(label=COUNT_QUESTION, tone="violet", icon="i-lucide-chart-no-axes-column"),
            AssistantSuggestion(label=REPLIES_QUESTION, tone="green", icon="i-lucide-mail"),
            AssistantSuggestion(label=RISK_QUESTION, tone="amber", icon="i-lucide-triangle-alert"),
        ],
    )
    COUNTED_KINDS: ClassVar[tuple[IssueKind, ...]] = tuple(
        kind for kind in IssueKind if kind not in (IssueKind.OK, IssueKind.REVIEW)
    )
    KIND_WORDS_IN_QUESTIONS: ClassVar[tuple[tuple[IssueKind, tuple[str, ...]], ...]] = (
        (IssueKind.HACK, ("pirat", "hack")),
        (IssueKind.RISK, ("risque", "php")),
        (IssueKind.LATE, ("retard", "mise à jour", "mises à jour", "wordpress")),
        (IssueKind.SECURITY, ("sécurité", "cadenas", "https")),
        (IssueKind.MOBILE, ("téléphone", "mobile")),
        (IssueKind.CONTACT, ("coordonnées",)),
        (IssueKind.DATED, ("daté", "vieux", "ancien")),
        (IssueKind.GOOGLE, ("google",)),
        (IssueKind.MAIL, ("mail",)),
    )
    TAB_WORDINGS: ClassVar[dict[SiteTab, str]] = {
        SiteTab.TO_WRITE: "à contacter",
        SiteTab.WRITTEN: "déjà contactés",
        SiteTab.ALL: "en tout",
    }
    SYSTEM_PROMPT: ClassVar[str] = (
        "Tu traduis la question d’un développeur indépendant sur les sites d’entreprises qu’il a contrôlés en une "
        "requête JSON. Réponds par un seul objet JSON, sans texte autour, avec ces clés :\n"
        '- "intent" : "search" (il veut voir des sites), "count" (il veut un comptage ou une répartition) ou '
        '"replies" (il parle de ses messages envoyés, des réponses ou des pages ouvertes) ;\n'
        '- "kind" : le type de souci s’il en nomme un, parmi "hack" (site piraté), "security" (cadenas, https), '
        '"risk" (version de PHP à risque), "late" (WordPress ou autre logiciel pas à jour), "mail" (e-mails, SPF, '
        'DMARC), "mobile" (affichage sur téléphone), "contact" (coordonnées), "dated" (allure ancienne), "google" '
        "(présentation dans Google), sinon null ;\n"
        '- "place" : le nom de la ville ou de l’entreprise s’il en nomme une, sinon null ;\n'
        '- "tab" : "written" s’il parle des sites déjà contactés, "all" s’il veut tous les sites, sinon "to_write".'
    )

    def respond(self, db: Session, user_id: int, request: AssistantRequest) -> SiteCareAssistantAnswer:
        """
        Answer a question once understood.

        Args:
            db: Active database session.
            user_id: The owner.
            request: What the question asks for.

        Returns:
            The answer, every figure and line read from his sites.
        """
        if request.intent == AssistantIntent.REPLIES:
            return self._replies(db, user_id)
        if request.intent == AssistantIntent.COUNT:
            return self._count(db, user_id)
        return self._search(db, user_id, request)

    async def understand(self, question: str) -> AssistantRequest:
        """
        Turn a question into a request.

        Args:
            question: The owner's words.

        Returns:
            What the language model understood, or what the words alone tell while it is off or gave no usable answer.
        """
        if llm_service.is_configured:
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ]
            understood: dict[str, Any] | None = await llm_service.complete_json(
                messages, max_tokens=300, temperature=0.1
            )
            request: AssistantRequest | None = self._request_of(understood) if understood is not None else None
            if request is not None:
                return request
        return self.understand_from_words(question)

    @classmethod
    def understand_from_words(cls, question: str) -> AssistantRequest:
        """
        Read a question without the language model.

        Args:
            question: The owner's words.

        Returns:
            The request its words tell.
        """
        words: str = question.lower()
        if any(word in words for word in ("répon", "ouvert", "relanc")):
            return AssistantRequest(intent=AssistantIntent.REPLIES)
        if any(word in words for word in ("combien", "répartition", "par type")):
            return AssistantRequest(intent=AssistantIntent.COUNT)
        kind: IssueKind | None = next(
            (known for known, kind_words in cls.KIND_WORDS_IN_QUESTIONS if any(word in words for word in kind_words)),
            None,
        )
        tab: SiteTab = SiteTab.TO_WRITE
        if "déjà" in words or "contactés" in words:
            tab = SiteTab.WRITTEN
        elif "tous les sites" in words:
            tab = SiteTab.ALL
        return AssistantRequest(intent=AssistantIntent.SEARCH, kind=kind, tab=tab)

    @classmethod
    def _request_of(cls, understood: dict[str, Any]) -> AssistantRequest | None:
        """
        Check what the language model answered.

        Args:
            understood: Its JSON object.

        Returns:
            The request, None when the intent is none of the three; a value out of its bounds is dropped.
        """
        intent: object = understood.get("intent")
        if intent not in {known.value for known in AssistantIntent}:
            return None
        kind: object = understood.get("kind")
        place: object = understood.get("place")
        tab: object = understood.get("tab")
        has_place: bool = isinstance(place, str) and 0 < len(place.strip()) <= cls.LONGEST_PLACE
        return AssistantRequest(
            intent=AssistantIntent(str(intent)),
            kind=IssueKind(str(kind)) if kind in {counted.value for counted in cls.COUNTED_KINDS} else None,
            place=str(place).strip() if has_place else None,
            tab=SiteTab(str(tab)) if tab in {known.value for known in cls.TAB_WORDINGS} else SiteTab.TO_WRITE,
        )

    def _search(self, db: Session, user_id: int, request: AssistantRequest) -> SiteCareAssistantAnswer:
        """
        The sites of a tab that match the filters.

        Args:
            db: Active database session.
            user_id: The owner.
            request: The filters.

        Returns:
            Their count in a sentence and the most pressing lines; a town or a name the tab does not hold is looked
            for among every site.
        """
        settings: OwnerSettings = owner_settings_service.get(db, user_id)
        tab: SiteTab = request.tab
        listing: SiteListing = self._listing(db, user_id, request, tab)
        if listing.matching_count == 0 and request.place is not None and tab != SiteTab.ALL:
            tab = SiteTab.ALL
            listing = self._listing(db, user_id, request, tab)
        described: str = self.TAB_WORDINGS[tab]
        if request.kind is not None:
            described += f" avec le souci « {KIND_LABELS[request.kind]} »"
        if request.place is not None:
            described += f" pour « {request.place} »"
        found: int = listing.matching_count
        if found == 0:
            text: str = f"Aucun site {described}."
        elif found > len(listing.sites):
            text = f"{self._sites(found)} {described}. Voici les {len(listing.sites)} plus pressants."
        else:
            text = f"{self._sites(found)} {described}."
        return SiteCareAssistantAnswer(
            text=text,
            cards=site_views.list_response(db, listing, settings).sites,
            next_questions=[self.COUNT_QUESTION, self.REPLIES_QUESTION],
        )

    def _listing(self, db: Session, user_id: int, request: AssistantRequest, tab: SiteTab) -> SiteListing:
        """
        The first sites of a tab that match the filters of a request.

        Args:
            db: Active database session.
            user_id: The owner.
            request: The filters.
            tab: The tab to read.

        Returns:
            Their count and the sites shown.
        """
        return site_service.list_sites(
            db,
            user_id,
            tab=tab,
            trade=None,
            kind=request.kind.value if request.kind else None,
            text=request.place,
            limit=self.CARDS_SHOWN,
            offset=0,
        )

    def _count(self, db: Session, user_id: int) -> SiteCareAssistantAnswer:
        """
        The sites checked, counted by kind of issue.

        Args:
            db: Active database session.
            user_id: The owner.

        Returns:
            The total in a sentence and the chart, largest first.
        """
        owned: ColumnElement[bool] = self._owned(user_id)
        total: int = self._number(db, owned)
        if total == 0:
            return SiteCareAssistantAnswer(text="Aucun site contrôlé pour l’instant.")
        bars: list[AssistantBar] = sorted(
            (
                AssistantBar(
                    label=KIND_LABELS[kind],
                    value=self._number(db, and_(owned, SiteCareSite.kinds_filter.like(f"%,{kind.value},%"))),
                )
                for kind in self.COUNTED_KINDS
            ),
            key=lambda bar: -bar.value,
        )
        bars = [bar for bar in bars if bar.value > 0][: self.BARS_SHOWN]
        checked: str = f"{self._sites(total)} contrôlé{'s' if total > 1 else ''}"
        if not bars:
            return SiteCareAssistantAnswer(
                text=f"{checked}, aucun souci relevé.", next_questions=[self.REPLIES_QUESTION]
            )
        return SiteCareAssistantAnswer(
            text=f"{checked}. Le souci le plus fréquent : {bars[0].label.lower()}, sur {self._sites(bars[0].value)}.",
            chart=AssistantChart(title="Sites par type de souci", bars=bars),
            next_questions=[self.HACKED_QUESTION, self.RISK_QUESTION],
        )

    def _replies(self, db: Session, user_id: int) -> SiteCareAssistantAnswer:
        """
        Where the sites written to stand.

        Args:
            db: Active database session.
            user_id: The owner.

        Returns:
            The counts in a sentence, and the site to look at first: the last reply, else the last page opened.
        """
        written: ColumnElement[bool] = and_(self._owned(user_id), SiteCareSite.written_at.is_not(None))
        written_count: int = self._number(db, written)
        if written_count == 0:
            return SiteCareAssistantAnswer(
                text="Vous n’avez encore écrit à aucun site.", next_questions=[self.HACKED_QUESTION]
            )
        replied_sites: list[SiteCareSite] = list(
            db.execute(
                select(SiteCareSite)
                .join(EmailLog, EmailLog.id == SiteCareSite.last_email_log_id)
                .where(written, EmailLog.replied_at.is_not(None))
                .order_by(EmailLog.replied_at.desc())
            ).scalars()
        )
        opened: ColumnElement[bool] = and_(written, SiteCareSite.page_opened_at.is_not(None))
        opened_count: int = self._number(db, opened)
        last_opened: SiteCareSite | None = db.execute(
            select(SiteCareSite).where(opened).order_by(SiteCareSite.page_opened_at.desc()).limit(1)
        ).scalar_one_or_none()
        reply_count: int = len(replied_sites)
        text: str = (
            f"{self._sites(written_count)} contacté{'s' if written_count > 1 else ''} : "
            f"{reply_count} réponse{'s' if reply_count > 1 else ''}, "
            f"{opened_count} page{'s' if opened_count > 1 else ''} ouverte{'s' if opened_count > 1 else ''}."
        )
        first: SiteCareSite | None = replied_sites[0] if replied_sites else last_opened
        highlight: AssistantHighlight | None = None
        if first is not None:
            highlight = AssistantHighlight(
                title=first.business_name,
                badge="Réponse" if replied_sites else "Page ouverte",
                meta=" · ".join(part for part in (first.host, first.city) if part),
                text=None,
                link_label="Ouvrir la fiche",
                link_to=f"{self.SITE_PATH}/{first.id}",
            )
        return SiteCareAssistantAnswer(text=text, highlight=highlight, next_questions=[self.COUNT_QUESTION])

    @staticmethod
    def _owned(user_id: int) -> ColumnElement[bool]:
        """The owner's sites still in his list."""
        return and_(SiteCareSite.user_id == user_id, SiteCareSite.archived_at.is_(None))

    @staticmethod
    def _number(db: Session, condition: ColumnElement[bool]) -> int:
        """How many sites match a condition."""
        return int(db.execute(select(func.count()).select_from(SiteCareSite).where(condition)).scalar() or 0)

    @staticmethod
    def _sites(count: int) -> str:
        """A count of sites in words (« 1 site », « 12 sites »)."""
        return f"{count} site{'s' if count > 1 else ''}"


assistant_service: AssistantService = AssistantService()
