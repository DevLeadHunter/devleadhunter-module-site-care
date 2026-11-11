"""Builds what the routes return about sites: every label of the list and of a sheet is written here."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from enums.email_status import EmailStatus
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from services.prospect_search.trade_catalog import TradeCatalog

from devleadhunter_site_care.catalog import KIND_LABELS, IssueKind, PointState, SiteStatus, SiteTab
from devleadhunter_site_care.models.care_plan import SiteCarePlan
from devleadhunter_site_care.models.sent_message import SiteCareSentMessage
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.schemas.site import (
    CarePlanBrief,
    MessageView,
    OfferLineView,
    SentMessageView,
    SiteCounts,
    SiteDetail,
    SiteLead,
    SiteListItem,
    SiteListResponse,
    SitePointView,
    SiteState,
    TradeOption,
)
from devleadhunter_site_care.services.care_plan_service import care_plan_service
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings
from devleadhunter_site_care.services.send_service import FIRST_MESSAGE, send_service
from devleadhunter_site_care.services.site_message import Money, OutgoingMessage, SheetLines, SiteMessageWriter
from devleadhunter_site_care.services.site_points import SitePoint
from devleadhunter_site_care.services.site_service import SiteListing, site_service
from devleadhunter_site_care.services.site_summary import SiteSummarizer, SiteSummary

_SHORT_MONTHS: tuple[str, ...] = (
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
)
_UNREACHABLE_TEXT: str = (
    "L’adresse du site ne mène plus nulle part. C’est peut-être un prospect pour le module Sites web."
)
_UNREADABLE_TEXT: str = "Le site n’a pas pu être lu automatiquement. Il faut l’ouvrir à la main pour le regarder."
_EMAIL_STATUS_LABELS: dict[str, str] = {
    EmailStatus.PENDING.value: "En cours d’envoi",
    EmailStatus.SENDING.value: "En cours d’envoi",
    EmailStatus.SENT.value: "Envoyé",
    EmailStatus.DELIVERED.value: "Reçu",
    EmailStatus.DELIVERY_DELAYED.value: "Retardé",
    EmailStatus.OPENED.value: "Ouvert",
    EmailStatus.CLICKED.value: "Lien ouvert",
    EmailStatus.REPLIED.value: "A répondu",
    EmailStatus.BOUNCED.value: "Adresse en erreur",
    EmailStatus.FAILED.value: "Échec de l’envoi",
    EmailStatus.COMPLAINED.value: "Signalé comme spam",
    EmailStatus.SUPPRESSED.value: "Adresse bloquée",
}


class SiteViews:
    """Turns sites into the list's lines and the sheet."""

    def list_response(self, db: Session, listing: SiteListing, settings: OwnerSettings) -> SiteListResponse:
        """
        A page of the list as the dashboard shows it.

        Args:
            db: Active database session.
            listing: The page and the counts.
            settings: The owner's settings.

        Returns:
            The response of ``GET /site-care/sites``.
        """
        replied_site_ids, blocked_site_ids = self._contact_marks(db, listing.sites)
        cared_site_ids: set[int] = care_plan_service.active_site_ids(db, [site.id for site in listing.sites])
        return SiteListResponse(
            counts=SiteCounts(
                total=listing.total_count,
                with_email=listing.with_email_count,
                to_fix=listing.to_fix_count,
                written=listing.written_count,
            ),
            tab_counts={tab.value: count for tab, count in listing.tab_counts.items()},
            trades=[TradeOption(key=key, label=TradeCatalog.resolve(key).label) for key in listing.trades],
            matching_count=listing.matching_count,
            sites=[
                self._list_item(
                    site,
                    site_service.summary_of(site, settings.writing_rules),
                    has_replied=site.id in replied_site_ids,
                    is_blocked=site.id in blocked_site_ids,
                    is_under_care=site.id in cared_site_ids,
                )
                for site in listing.sites
            ],
        )

    def detail(self, db: Session, site: SiteCareSite, settings: OwnerSettings) -> SiteDetail:
        """
        The sheet of a site.

        Args:
            db: Active database session.
            site: The site.
            settings: The owner's settings.

        Returns:
            The response of the site routes.
        """
        summary: SiteSummary = site_service.summary_of(site, settings.writing_rules)
        replied_site_ids, blocked_site_ids = self._contact_marks(db, [site])
        plan: SiteCarePlan | None = care_plan_service.active_plan_of(db, site.id)
        item: SiteListItem = self._list_item(
            site,
            summary,
            has_replied=site.id in replied_site_ids,
            is_blocked=site.id in blocked_site_ids,
            is_under_care=plan is not None,
        )
        writer: SiteMessageWriter = send_service.writer_for(site, settings)
        message: OutgoingMessage | None = writer.first_message(with_page_link=False)
        with_link: OutgoingMessage | None = writer.first_message(with_page_link=True)
        refusal: str | None = send_service.first_message_refusal(db, site, settings)
        is_unread: bool = site.status in (SiteStatus.UNREACHABLE.value, SiteStatus.UNREADABLE.value)
        return SiteDetail(
            **item.model_dump(),
            phone=site.phone,
            google_rating=site.google_rating,
            google_reviews_count=site.google_reviews_count,
            google_maps_url=site.google_maps_url,
            unread_text=self._unread_text(site),
            fixes=[self._point_view(point) for point in summary.fixes],
            watches=[self._point_view(point) for point in summary.watches],
            good_line=None if is_unread else SheetLines.good_line(summary),
            hidden_line=None if is_unread else SheetLines.hidden_line(summary),
            offer=[
                OfferLineView(label=line.label, price_label=Money.label(line.price_cents))
                for line in SiteSummarizer.offer_lines(summary.corrections, settings.prices)
            ],
            monthly_label=f"{Money.euros(settings.monthly_price_cents)} par mois",
            message=(
                MessageView(
                    subject=message.subject,
                    paragraphs=message.paragraphs,
                    paragraphs_with_link=with_link.paragraphs,
                )
                if message is not None and with_link is not None
                else None
            ),
            page_url=send_service.page_url(site) if summary.lead is not None else None,
            can_send=refusal is None,
            send_refusal=refusal,
            sent_messages=self._sent_messages(db, site),
            care_plan=(
                CarePlanBrief(id=plan.id, monthly_price_cents=plan.monthly_price_cents, started_at=plan.started_at)
                if plan is not None
                else None
            ),
        )

    @staticmethod
    def short_day(moment: datetime) -> str:
        """A day as the state badge writes it: « 9 nov. »."""
        return f"{moment.day} {_SHORT_MONTHS[moment.month - 1]}"

    def _list_item(
        self, site: SiteCareSite, summary: SiteSummary, *, has_replied: bool, is_blocked: bool, is_under_care: bool
    ) -> SiteListItem:
        """One line of the list."""
        tab: SiteTab = site_service.tab_of(site)
        return SiteListItem(
            id=site.id,
            business_name=site.business_name,
            trade_label=TradeCatalog.resolve(site.trade).label if site.trade else "",
            city=site.city,
            country=site.country,
            domain=site.host,
            website=site.website,
            email=site.email,
            tab=tab.value,
            state=self._state(site, tab, has_replied=has_replied, is_blocked=is_blocked, is_under_care=is_under_care),
            lead=self._lead(site, summary),
            also=summary.also_line,
            checked_at=site.checked_at,
        )

    def _state(
        self, site: SiteCareSite, tab: SiteTab, *, has_replied: bool, is_blocked: bool, is_under_care: bool
    ) -> SiteState:
        """Where the owner stands with a site, the most telling state first."""
        if is_under_care:
            return SiteState(key="care", label="En suivi", tone="green")
        if is_blocked:
            return SiteState(key="do_not_contact", label="Ne plus contacter", tone="neutral")
        if has_replied:
            return SiteState(key="replied", label="A répondu", tone="violet")
        if site.written_at is not None:
            return SiteState(key="written", label=f"Écrit le {self.short_day(site.written_at)}", tone="neutral")
        if tab == SiteTab.REVIEW:
            return SiteState(key="review", label="À revoir", tone="amber")
        if tab == SiteTab.NOTHING:
            return SiteState(key="nothing", label="Rien à faire", tone="neutral")
        if tab == SiteTab.NO_EMAIL:
            return SiteState(key="no_email", label="Sans email", tone="neutral")
        return SiteState(key="to_write", label="À écrire", tone="ink")

    @staticmethod
    def _lead(site: SiteCareSite, summary: SiteSummary) -> SiteLead:
        """The tag and the sentence of a line."""
        if site.status == SiteStatus.UNREACHABLE.value:
            return SiteLead(
                kind=IssueKind.REVIEW.value,
                kind_label=KIND_LABELS[IssueKind.REVIEW],
                tone="amber",
                sentence="Le site ne répond plus",
            )
        if site.status == SiteStatus.UNREADABLE.value:
            return SiteLead(
                kind=IssueKind.REVIEW.value,
                kind_label=KIND_LABELS[IssueKind.REVIEW],
                tone="amber",
                sentence="Le site n’a pas pu être lu automatiquement",
            )
        lead: SitePoint | None = summary.lead
        if lead is None or lead.kind is None:
            return SiteLead(
                kind=IssueKind.OK.value,
                kind_label=KIND_LABELS[IssueKind.OK],
                tone="green",
                sentence="Tout ce qui se voit de l’extérieur est bon",
            )
        return SiteLead(
            kind=lead.kind.value,
            kind_label=KIND_LABELS[lead.kind],
            tone="red" if lead.state == PointState.FIX else "amber",
            tech=lead.tech or None,
            sentence=lead.sentence,
        )

    @staticmethod
    def _point_view(point: SitePoint) -> SitePointView:
        """A point of the sheet."""
        kind: IssueKind = point.kind or IssueKind.REVIEW
        return SitePointView(
            key=point.key.value, kind=kind.value, kind_label=KIND_LABELS[kind], tech=point.tech or None, fact=point.fact
        )

    @staticmethod
    def _unread_text(site: SiteCareSite) -> str | None:
        """What the sheet says of a site that could not be read."""
        if site.status == SiteStatus.UNREACHABLE.value:
            return _UNREACHABLE_TEXT
        return _UNREADABLE_TEXT if site.status == SiteStatus.UNREADABLE.value else None

    @staticmethod
    def _contact_marks(db: Session, sites: list[SiteCareSite]) -> tuple[set[int], set[int]]:
        """
        Which sites answered, and which the core forbids writing to, read in two queries for a whole page.

        Returns:
            The ids of the sites whose last message got a reply, and of those whose prospect asked not to be contacted.
        """
        log_ids: dict[int, int] = {
            site.last_email_log_id: site.id for site in sites if site.last_email_log_id is not None
        }
        prospect_ids: dict[int, int] = {site.prospect_id: site.id for site in sites if site.prospect_id is not None}
        replied: set[int] = set()
        blocked: set[int] = set()
        if log_ids:
            replied = {
                log_ids[log_id]
                for log_id in db.execute(
                    select(EmailLog.id).where(EmailLog.id.in_(list(log_ids)), EmailLog.replied_at.is_not(None))
                ).scalars()
            }
        if prospect_ids:
            blocked = {
                prospect_ids[prospect_id]
                for prospect_id in db.execute(
                    select(ProspectDB.id).where(
                        ProspectDB.id.in_(list(prospect_ids)), ProspectDB.do_not_contact.is_(True)
                    )
                ).scalars()
            }
        return replied, blocked

    @staticmethod
    def _sent_messages(db: Session, site: SiteCareSite) -> list[SentMessageView]:
        """The messages that left about a site, the latest first, with what became of each."""
        rows = db.execute(
            select(SiteCareSentMessage, EmailLog.status)
            .outerjoin(EmailLog, EmailLog.id == SiteCareSentMessage.email_log_id)
            .where(SiteCareSentMessage.site_id == site.id)
            .order_by(SiteCareSentMessage.sent_at.desc())
        ).all()
        return [
            SentMessageView(
                kind=sent.kind,
                kind_label="Premier message" if sent.kind == FIRST_MESSAGE else "Rapport du mois",
                subject=sent.subject,
                sent_at=sent.sent_at,
                status_label=_EMAIL_STATUS_LABELS.get(status or "", "Envoyé"),
            )
            for sent, status in rows
        ]


site_views = SiteViews()
