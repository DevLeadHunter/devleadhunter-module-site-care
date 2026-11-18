"""
The assistant of the sites: a conversation in plain words, answered from the owner's own sites.

The language model holds the conversation and picks the tools below; each tool reads the database and hands back
facts, lines and charts. The model never reads the database itself and the page only draws what a tool found. While
the model is off, the words of the question alone pick one tool.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import ClassVar

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.orm import Session

from models.email_log import EmailLog
from schemas.module_assistant import (
    AssistantBar,
    AssistantChart,
    AssistantHighlight,
    AssistantHome,
    AssistantPastExchange,
    AssistantSuggestion,
)
from services.module_assistant_engine import (
    AssistantArgumentReader,
    AssistantOutcome,
    AssistantTool,
    AssistantToolArguments,
    AssistantToolResult,
    module_assistant_engine,
)
from services.prospect_search.trade_catalog import TradeCatalog

from devleadhunter_site_care.catalog import KIND_LABELS, IssueKind, SiteTab
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.schemas.assistant import SiteCareAssistantAnswer
from devleadhunter_site_care.schemas.site import SiteDetail, SiteListItem
from devleadhunter_site_care.services.care_plan_service import care_plan_service
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings, owner_settings_service
from devleadhunter_site_care.services.site_message import Money
from devleadhunter_site_care.services.site_service import SiteListing, site_service
from devleadhunter_site_care.services.site_views import site_views
from devleadhunter_site_care.services.watch_service import WatchLine, watch_service


class AssistantService:
    """Answers questions about the sites, with the language model's tools or the words of the question alone."""

    CARDS_SHOWN: ClassVar[int] = 6
    BARS_SHOWN: ClassVar[int] = 6
    WATCH_LINES_SHOWN: ClassVar[int] = 8
    TEXT_MAXIMUM_LENGTH: ClassVar[int] = 60
    SITE_PATH: ClassVar[str] = "/dashboard/site-care/sites"
    WATCH_PATH: ClassVar[str] = "/dashboard/site-care/watch"
    CARE_PLANS_PATH: ClassVar[str] = "/dashboard/site-care/care-plans"
    SUBJECT: ClassVar[str] = (
        "Ce module regarde de l’extérieur les sites d’entreprises (artisans, commerces) et relève leurs soucis : "
        "site piraté, sécurité, version de PHP à risque, mise à jour en retard, e-mails, affichage sur téléphone, "
        "coordonnées, site daté, présentation dans Google. Il propose d’écrire au propriétaire avec un prix pour "
        "la correction, surveille les sites (la veille) et suit les clients qui paient un entretien mensuel."
    )
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
    TAB_CHOICES: ClassVar[dict[str, SiteTab]] = {
        "a_ecrire": SiteTab.TO_WRITE,
        "ecrits": SiteTab.WRITTEN,
        "sans_email": SiteTab.NO_EMAIL,
        "rien_a_signaler": SiteTab.NOTHING,
        "a_revoir": SiteTab.REVIEW,
        "tous": SiteTab.ALL,
    }
    TAB_WORDINGS: ClassVar[dict[SiteTab, str]] = {
        SiteTab.TO_WRITE: "à contacter",
        SiteTab.WRITTEN: "déjà contactés",
        SiteTab.NO_EMAIL: "sans adresse e-mail",
        SiteTab.NOTHING: "sans souci relevé",
        SiteTab.REVIEW: "à revoir",
        SiteTab.ALL: "en tout",
    }
    GROUPINGS: ClassVar[tuple[str, ...]] = ("souci", "etat", "ville", "metier")

    async def answer(
        self, db: Session, user_id: int, question: str, history: Sequence[AssistantPastExchange], now: datetime
    ) -> SiteCareAssistantAnswer:
        """
        Answer a question of the conversation.

        Args:
            db: Active database session.
            user_id: The owner.
            question: His words.
            history: The conversation so far, oldest first.
            now: The moment, naive UTC.

        Returns:
            The answer: the language model's words on what its tools read, or one tool's own sentence while the
            model is off or gave nothing usable.
        """
        outcome: AssistantOutcome | None = await module_assistant_engine.answer(
            db, user_id, subject=self.SUBJECT, tools=self.tools(now), question=question, history=history
        )
        if outcome is None:
            return self.answer_from_words(db, user_id, question, now)
        return SiteCareAssistantAnswer(
            text=outcome.text,
            cards=[card for card in outcome.cards if isinstance(card, SiteListItem)],
            chart=outcome.chart,
            highlight=outcome.highlight,
            next_questions=outcome.next_questions or [self.COUNT_QUESTION, self.REPLIES_QUESTION],
            context=outcome.context,
        )

    def answer_from_words(self, db: Session, user_id: int, question: str, now: datetime) -> SiteCareAssistantAnswer:
        """
        Answer a question without the language model: its words pick one tool.

        Args:
            db: Active database session.
            user_id: The owner.
            question: His words.
            now: The moment, naive UTC.

        Returns:
            What the tool read, in its own sentence.
        """
        tool_name, arguments = self.tool_call_of_words(question)
        tool: AssistantTool = next(tool for tool in self.tools(now) if tool.name == tool_name)
        result: AssistantToolResult = tool.run(db, user_id, arguments)
        next_questions: list[str] = [self.COUNT_QUESTION, self.REPLIES_QUESTION]
        if tool_name == "compter_sites":
            next_questions = [self.HACKED_QUESTION, self.RISK_QUESTION]
        elif tool_name == "suivi_sites_contactes":
            next_questions = [self.COUNT_QUESTION]
        return SiteCareAssistantAnswer(
            text=result.sentence,
            cards=[card for card in result.cards if isinstance(card, SiteListItem)],
            chart=result.chart,
            highlight=result.highlight,
            next_questions=next_questions,
        )

    @classmethod
    def tool_call_of_words(cls, question: str) -> tuple[str, AssistantToolArguments]:
        """
        Read a question without the language model.

        Args:
            question: The owner's words.

        Returns:
            The tool its words ask for, and its arguments.
        """
        words: str = question.lower()
        if any(word in words for word in ("répon", "ouvert", "relanc")):
            return "suivi_sites_contactes", {}
        if any(word in words for word in ("combien", "répartition", "par type")):
            return "compter_sites", {"group_by": "souci"}
        if "veille" in words or "changé" in words:
            return "veille", {}
        if "client" in words or "suivi" in words:
            return "clients_en_suivi", {}
        arguments: AssistantToolArguments = {}
        kind: IssueKind | None = next(
            (known for known, kind_words in cls.KIND_WORDS_IN_QUESTIONS if any(word in words for word in kind_words)),
            None,
        )
        if kind is not None:
            arguments["kind"] = kind.value
        if "déjà" in words or "contactés" in words:
            arguments["tab"] = "ecrits"
        elif "tous les sites" in words:
            arguments["tab"] = "tous"
        return "chercher_sites", arguments

    def tools(self, now: datetime) -> list[AssistantTool]:
        """
        The ways of reading the sites the language model may call.

        Args:
            now: The moment, naive UTC.

        Returns:
            The tools, each closed over the moment of the question.
        """
        return [
            AssistantTool(
                name="chercher_sites",
                description=(
                    "Liste des sites qui passent les filtres, les plus pressants d’abord, avec leur nombre ; la "
                    "page affiche les six premiers en cartes. Sans filtre : les sites à contacter."
                ),
                parameters={
                    "kind": {
                        "type": "string",
                        "enum": [kind.value for kind in self.COUNTED_KINDS],
                        "description": (
                            "Type de souci : hack (site piraté), security (cadenas, https), risk (version de PHP à "
                            "risque), late (WordPress ou autre logiciel pas à jour), mail (e-mails, SPF, DMARC), "
                            "mobile (affichage sur téléphone), contact (coordonnées), dated (allure ancienne), "
                            "google (présentation dans Google)."
                        ),
                    },
                    "text": {
                        "type": "string",
                        "description": "Une ville, un nom d’entreprise ou une adresse de site, cherché tel quel.",
                    },
                    "tab": {
                        "type": "string",
                        "enum": list(self.TAB_CHOICES),
                        "description": (
                            "a_ecrire (défaut : à contacter), ecrits (déjà contactés), sans_email, "
                            "rien_a_signaler, a_revoir, tous."
                        ),
                    },
                },
                run=self._search,
            ),
            AssistantTool(
                name="compter_sites",
                description=(
                    "Répartition de tous les sites contrôlés, que la page affiche en graphique à barres : par type "
                    "de souci, état (à contacter, contactés…), ville ou métier."
                ),
                parameters={"group_by": {"type": "string", "enum": list(self.GROUPINGS)}},
                run=self._count,
            ),
            AssistantTool(
                name="suivi_sites_contactes",
                description=(
                    "Où en sont les messages envoyés : sites contactés, réponses reçues, pages ouvertes par les "
                    "propriétaires, et le site à regarder d’abord."
                ),
                run=lambda db, user_id, _arguments: self._contacted(db, user_id),
            ),
            AssistantTool(
                name="detail_site",
                description=(
                    "Fiche complète d’un site : ce qui est à corriger, à surveiller, ce qui va bien, l’offre et "
                    "son prix, l’entretien mensuel, les messages déjà envoyés et leur état. À appeler pour toute "
                    "question sur un site précis."
                ),
                parameters={
                    "text": {
                        "type": "string",
                        "description": "Nom de l’entreprise ou adresse du site, pour le retrouver.",
                    }
                },
                run=self._detail,
            ),
            AssistantTool(
                name="veille",
                description=(
                    "Ce que la veille a vu ces derniers jours (sites piratés, sites tombés, points qui se sont "
                    "dégradés) et les échéances qui approchent (fin de suivi d’une version de PHP, certificats)."
                ),
                run=lambda db, user_id, _arguments: self._watch(db, user_id, now),
            ),
            AssistantTool(
                name="clients_en_suivi",
                description=(
                    "Les clients qui paient l’entretien mensuel : leur nombre, le revenu par mois et leur liste."
                ),
                run=lambda db, user_id, _arguments: self._care_plans(db, user_id),
            ),
        ]

    def _search(self, db: Session, user_id: int, arguments: AssistantToolArguments) -> AssistantToolResult:
        """
        The sites of a tab that match the filters.

        Args:
            db: Active database session.
            user_id: The owner.
            arguments: The filters the model or the words gave.

        Returns:
            Their count and the most pressing lines; a town or a name the tab does not hold is looked for among
            every site.
        """
        settings: OwnerSettings = owner_settings_service.get(db, user_id)
        tab: SiteTab = self.TAB_CHOICES[
            AssistantArgumentReader.choice(arguments, "tab", list(self.TAB_CHOICES), default="a_ecrire")
        ]
        kind_value: str = AssistantArgumentReader.choice(
            arguments, "kind", [kind.value for kind in self.COUNTED_KINDS], default=""
        )
        kind: IssueKind | None = IssueKind(kind_value) if kind_value else None
        text: str | None = AssistantArgumentReader.words(arguments, "text", longest=self.TEXT_MAXIMUM_LENGTH)
        listing: SiteListing = self._listing(db, user_id, tab, kind, text)
        if listing.matching_count == 0 and text is not None and tab != SiteTab.ALL:
            tab = SiteTab.ALL
            listing = self._listing(db, user_id, tab, kind, text)
        described: str = self.TAB_WORDINGS[tab]
        if kind is not None:
            described += f" avec le souci « {KIND_LABELS[kind]} »"
        if text is not None:
            described += f" pour « {text} »"
        found: int = listing.matching_count
        cards: list[SiteListItem] = site_views.list_response(db, listing, settings).sites
        if found == 0:
            sentence: str = f"Aucun site {described}."
        elif found > len(cards):
            sentence = f"{self._sites_label(found)} {described}. Voici les {len(cards)} plus pressants."
        else:
            sentence = f"{self._sites_label(found)} {described}."
        return AssistantToolResult(
            facts={
                "nombre": found,
                "filtres": described,
                "affiches": [
                    {
                        "entreprise": card.business_name,
                        "metier": card.trade_label,
                        "ville": card.city,
                        "site": card.domain,
                        "souci_principal": card.lead.kind_label,
                        "constat": card.lead.sentence,
                        "aussi": card.also,
                        "prix_a_proposer": card.price_label,
                        "etat": card.state.label,
                    }
                    for card in cards
                ],
            },
            sentence=sentence,
            cards=cards,
        )

    def _listing(
        self, db: Session, user_id: int, tab: SiteTab, kind: IssueKind | None, text: str | None
    ) -> SiteListing:
        """The first sites of a tab that match a kind of issue and some words."""
        return site_service.list_sites(
            db,
            user_id,
            tab=tab,
            trade=None,
            kind=kind.value if kind else None,
            text=text,
            limit=self.CARDS_SHOWN,
            offset=0,
        )

    def _count(self, db: Session, user_id: int, arguments: AssistantToolArguments) -> AssistantToolResult:
        """
        The sites checked, split one way.

        Args:
            db: Active database session.
            user_id: The owner.
            arguments: How to split them.

        Returns:
            The total and the chart, largest first.
        """
        owned: ColumnElement[bool] = self._owned_sites_condition(user_id)
        total: int = self._count_sites(db, owned)
        if total == 0:
            return AssistantToolResult(facts={"nombre": 0}, sentence="Aucun site contrôlé pour l’instant.")
        grouping: str = AssistantArgumentReader.choice(arguments, "group_by", self.GROUPINGS, default="souci")
        counts: dict[str, int]
        if grouping == "etat":
            title: str = "Sites par état"
            counts = {
                self.TAB_WORDINGS[tab].capitalize(): self._count_sites(db, and_(owned, site_service.tab_filter(tab)))
                for tab in SiteTab
                if tab != SiteTab.ALL
            }
        elif grouping in ("ville", "metier"):
            column = SiteCareSite.city if grouping == "ville" else SiteCareSite.trade
            title = "Sites par ville" if grouping == "ville" else "Sites par métier"
            rows = db.execute(
                select(column, func.count()).where(owned, column.is_not(None), column != "").group_by(column)
            ).all()
            counts = {
                (str(value) if grouping == "ville" else TradeCatalog.resolve(str(value)).label): int(count)
                for value, count in rows
            }
        else:
            title = "Sites par type de souci"
            counts = {
                KIND_LABELS[kind]: self._count_sites(
                    db, and_(owned, SiteCareSite.kinds_filter.like(f"%,{kind.value},%"))
                )
                for kind in self.COUNTED_KINDS
            }
        ranked: list[tuple[str, int]] = sorted(
            ((label, count) for label, count in counts.items() if count > 0), key=lambda item: (-item[1], item[0])
        )
        bars: list[AssistantBar] = [
            AssistantBar(label=label, value=count) for label, count in ranked[: self.BARS_SHOWN]
        ]
        checked: str = f"{self._sites_label(total)} contrôlé{'s' if total > 1 else ''}"
        if not bars:
            return AssistantToolResult(facts={"nombre": total}, sentence=f"{checked}, rien à répartir.")
        return AssistantToolResult(
            facts={"nombre": total, "repartition": title, "barres": dict(ranked[:20])},
            sentence=f"{checked}. En tête : {bars[0].label.lower()}, sur {self._sites_label(bars[0].value)}.",
            chart=AssistantChart(title=title, bars=bars),
        )

    def _contacted(self, db: Session, user_id: int) -> AssistantToolResult:
        """
        Where the sites written to stand.

        Args:
            db: Active database session.
            user_id: The owner.

        Returns:
            The counts, and the site to look at first: the last reply, else the last page opened.
        """
        written: ColumnElement[bool] = and_(self._owned_sites_condition(user_id), SiteCareSite.written_at.is_not(None))
        written_count: int = self._count_sites(db, written)
        if written_count == 0:
            return AssistantToolResult(facts={"sites_contactes": 0}, sentence="Vous n’avez encore écrit à aucun site.")
        replied_sites: list[SiteCareSite] = list(
            db.execute(
                select(SiteCareSite)
                .join(EmailLog, EmailLog.id == SiteCareSite.last_email_log_id)
                .where(written, EmailLog.replied_at.is_not(None))
                .order_by(EmailLog.replied_at.desc())
            ).scalars()
        )
        opened: ColumnElement[bool] = and_(written, SiteCareSite.page_opened_at.is_not(None))
        opened_sites: list[SiteCareSite] = list(
            db.execute(
                select(SiteCareSite).where(opened).order_by(SiteCareSite.page_opened_at.desc()).limit(self.CARDS_SHOWN)
            ).scalars()
        )
        opened_count: int = self._count_sites(db, opened)
        reply_count: int = len(replied_sites)
        first: SiteCareSite | None = (replied_sites or opened_sites or [None])[0]
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
        return AssistantToolResult(
            facts={
                "sites_contactes": written_count,
                "reponses": [site.business_name for site in replied_sites[: self.CARDS_SHOWN]],
                "nombre_de_reponses": reply_count,
                "pages_ouvertes": [
                    {"entreprise": site.business_name, "ouvertures": site.page_open_count} for site in opened_sites
                ],
                "nombre_de_pages_ouvertes": opened_count,
            },
            sentence=(
                f"{self._sites_label(written_count)} contacté{'s' if written_count > 1 else ''} : "
                f"{reply_count} réponse{'s' if reply_count > 1 else ''}, "
                f"{opened_count} page{'s' if opened_count > 1 else ''} ouverte{'s' if opened_count > 1 else ''}."
            ),
            highlight=highlight,
        )

    def _detail(self, db: Session, user_id: int, arguments: AssistantToolArguments) -> AssistantToolResult:
        """
        The whole sheet of one site.

        Args:
            db: Active database session.
            user_id: The owner.
            arguments: Words of its business name or of its address.

        Returns:
            What is to fix, to watch and fine, its offer and its messages, with its line and the link to its sheet.
        """
        text: str | None = AssistantArgumentReader.words(arguments, "text", longest=self.TEXT_MAXIMUM_LENGTH)
        if text is None:
            return AssistantToolResult(facts={"trouve": False}, sentence="Dites-moi de quel site vous parlez.")
        listing: SiteListing = self._listing(db, user_id, SiteTab.ALL, None, text)
        if not listing.sites:
            return AssistantToolResult(facts={"trouve": False}, sentence=f"Aucun site ne correspond à « {text} ».")
        settings: OwnerSettings = owner_settings_service.get(db, user_id)
        site: SiteCareSite = listing.sites[0]
        detail: SiteDetail = site_views.detail(db, site, settings)
        listing.sites = [site]
        return AssistantToolResult(
            facts={
                "trouve": True,
                "entreprise": detail.business_name,
                "metier": detail.trade_label,
                "ville": detail.city,
                "site": detail.domain,
                "etat": detail.state.label,
                "adresse_email_connue": detail.email is not None,
                "a_corriger": [{"souci": point.kind_label, "constat": point.fact} for point in detail.fixes],
                "a_surveiller": [{"souci": point.kind_label, "constat": point.fact} for point in detail.watches],
                "ce_qui_va_bien": detail.good_line,
                "offre": [{"correction": line.label, "prix": line.price_label} for line in detail.offer],
                "prix_a_proposer": detail.price_label,
                "entretien_mensuel": detail.monthly_label,
                "messages_envoyes": [
                    {"objet": sent.subject, "etat": sent.status_label} for sent in detail.sent_messages
                ],
                "client_en_suivi": detail.care_plan is not None,
            },
            sentence=f"{detail.business_name} ({detail.domain}) : {detail.lead.sentence}",
            cards=site_views.list_response(db, listing, settings).sites,
            highlight=AssistantHighlight(
                title=detail.business_name,
                badge=detail.state.label,
                meta=" · ".join(part for part in (detail.domain, detail.city) if part),
                text=None,
                link_label="Ouvrir la fiche",
                link_to=f"{self.SITE_PATH}/{site.id}",
            ),
        )

    def _watch(self, db: Session, user_id: int, now: datetime) -> AssistantToolResult:
        """
        What the watch saw lately and the dates coming up.

        Args:
            db: Active database session.
            user_id: The owner.
            now: The moment, naive UTC.

        Returns:
            The lines of the watch page, the most pressing as the highlight.
        """
        changes: list[WatchLine] = watch_service.recent_changes(
            watch_service.changes_that_still_hold(db, user_id, now), now
        )
        deadlines: list[WatchLine] = [watch_date.line for watch_date in watch_service.upcoming_dates(db, user_id, now)]
        if not changes and not deadlines:
            return AssistantToolResult(
                facts={"changements": [], "echeances": []}, sentence="Rien de nouveau dans la veille."
            )
        first: WatchLine = (changes or deadlines)[0]
        return AssistantToolResult(
            facts={
                "changements": [
                    {"titre": line.title, "detail": line.detail, "quand": line.when_label, "sites": line.site_count}
                    for line in changes[: self.WATCH_LINES_SHOWN]
                ],
                "echeances": [
                    {"titre": line.title, "detail": line.detail, "quand": line.when_label, "sites": line.site_count}
                    for line in deadlines[: self.WATCH_LINES_SHOWN]
                ],
            },
            sentence=(
                f"{len(changes)} changement{'s' if len(changes) > 1 else ''} vu{'s' if len(changes) > 1 else ''} "
                f"ces derniers jours, {len(deadlines)} échéance{'s' if len(deadlines) > 1 else ''} à venir."
            ),
            highlight=AssistantHighlight(
                title=first.title,
                badge=first.when_label,
                meta=first.detail,
                text=None,
                link_label="Ouvrir la veille",
                link_to=self.WATCH_PATH,
            ),
        )

    def _care_plans(self, db: Session, user_id: int) -> AssistantToolResult:
        """
        The clients under monthly care.

        Args:
            db: Active database session.
            user_id: The owner.

        Returns:
            Their count, what they bring each month and their list.
        """
        plans = care_plan_service.active_plans(db, user_id)
        if not plans:
            return AssistantToolResult(facts={"clients": 0}, sentence="Aucun client en suivi pour l’instant.")
        monthly_cents: int = sum(plan.monthly_price_cents for plan, _site in plans)
        return AssistantToolResult(
            facts={
                "clients": len(plans),
                "revenu_mensuel": Money.euros(monthly_cents),
                "liste": [
                    {
                        "entreprise": site.business_name,
                        "site": site.host,
                        "par_mois": Money.euros(plan.monthly_price_cents),
                    }
                    for plan, site in plans[:20]
                ],
            },
            sentence=(
                f"{len(plans)} client{'s' if len(plans) > 1 else ''} en suivi, {Money.euros(monthly_cents)} par mois."
            ),
            highlight=AssistantHighlight(
                title="Clients en suivi",
                badge=str(len(plans)),
                meta=f"{Money.euros(monthly_cents)} par mois",
                text=None,
                link_label="Ouvrir les clients en suivi",
                link_to=self.CARE_PLANS_PATH,
            ),
        )

    @staticmethod
    def _owned_sites_condition(user_id: int) -> ColumnElement[bool]:
        """The owner's sites still in his list."""
        return and_(SiteCareSite.user_id == user_id, SiteCareSite.archived_at.is_(None))

    @staticmethod
    def _count_sites(db: Session, condition: ColumnElement[bool]) -> int:
        """How many sites match a condition."""
        return int(db.execute(select(func.count()).select_from(SiteCareSite).where(condition)).scalar() or 0)

    @staticmethod
    def _sites_label(count: int) -> str:
        """A count of sites in words (« 1 site », « 12 sites »)."""
        return f"{count} site{'s' if count > 1 else ''}"


assistant_service: AssistantService = AssistantService()
