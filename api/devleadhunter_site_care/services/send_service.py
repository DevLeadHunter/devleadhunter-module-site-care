"""
Sends the module's messages through the core: its sender, its signature, its unsubscribe footer, its reply capture.

A business becomes a prospect of the core the first time it is written to. From then on the core's rules apply to
it like to any prospect: « ne plus contacter », the lock between modules, the unsubscribe list.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.config import settings as core_settings
from enums.source import Source
from enums.website_status import WebsiteStatus
from models.email_log import EmailLog
from models.prospect import ProspectCreate
from models.prospect_db import ProspectDB
from models.prospect_search_candidate import ProspectSearchCandidate
from services import reply_capture_service
from services.activity_log_service import activity_log_service
from services.campaign_queue_service import CampaignQueueService
from services.contact_lock_service import contact_lock_service
from services.email_sending_service import EmailSendingService
from services.email_signatures import render_default_signature_html
from services.organization_service import organization_service
from services.prospect_emails import set_prospect_emails
from services.prospect_search.service import ProspectSearchError, prospect_search_service
from services.prospect_search.trade_catalog import TradeCatalog
from services.prospect_service import prospect_service
from services.reply_inbox_forward_service import inbox_copy_address
from services.sending_identity import SendingIdentity, SendingNotConfiguredError, resolve_sending_identity
from services.unsubscribe_service import unsubscribe_service

from devleadhunter_site_care import MODULE_KEY
from devleadhunter_site_care.models.sent_message import SiteCareSentMessage
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings
from devleadhunter_site_care.services.site_message import OutgoingMessage, SiteMessageWriter, SiteSubject
from devleadhunter_site_care.services.site_points import FrenchDates
from devleadhunter_site_care.services.site_service import SiteCareError, site_service

logger = logging.getLogger(__name__)

ACTIVITY_CATEGORY: str = MODULE_KEY
FIRST_MESSAGE: str = "first"
MONTHLY_REPORT: str = "report"


class SendService:
    """Sends a site's first message and a client's monthly report."""

    @staticmethod
    def page_url(site: SiteCareSite) -> str:
        """The public address of the page prepared for a site's owner."""
        return f"{core_settings.demo_host_base_url.rstrip('/')}/bilan/{site.page_slug}"

    def writer_for(self, site: SiteCareSite, settings: OwnerSettings) -> SiteMessageWriter:
        """
        The writer of a site's messages and page.

        Args:
            site: The site written about.
            settings: The owner's settings.

        Returns:
            The writer, on the site's stored check.
        """
        return SiteMessageWriter(
            SiteSubject(business_name=site.business_name, domain=site.host, page_url=self.page_url(site)),
            site_service.summary_of(site, settings.writing_rules),
            settings,
        )

    def first_message_refusal(self, db: Session, site: SiteCareSite, settings: OwnerSettings) -> str | None:
        """
        Why the first message cannot leave, from what is already known without asking anything outside.

        Args:
            db: Active database session.
            site: The site.
            settings: The owner's settings.

        Returns:
            The French reason, or None when the message can be tried.
        """
        if self.writer_for(site, settings).first_message(with_page_link=False) is None:
            return "Rien à écrire pour ce site."
        if site.written_at is not None:
            return f"Déjà écrit le {FrenchDates.day(site.written_at.date())}."
        if not site.email:
            return "Pas d’adresse e-mail pour ce prospect."
        prospect: ProspectDB | None = db.get(ProspectDB, site.prospect_id) if site.prospect_id else None
        return self._prospect_refusal(prospect, site.email, naive_utc_now()) if prospect is not None else None

    async def send_first_message(
        self, db: Session, site: SiteCareSite, settings: OwnerSettings, *, with_page_link: bool
    ) -> None:
        """
        Send the first message about a site to its business.

        Args:
            db: Active database session.
            site: The site.
            settings: The owner's settings.
            with_page_link: Whether the message carries the link of the page prepared for the owner.

        Raises:
            SiteCareError: The message cannot leave; the reason is in French, ready to be shown.
        """
        refusal: str | None = self.first_message_refusal(db, site, settings)
        if refusal is not None:
            raise SiteCareError(refusal)
        message: OutgoingMessage | None = self.writer_for(site, settings).first_message(with_page_link=with_page_link)
        if message is None or not site.email:
            raise SiteCareError("Rien à écrire pour ce site.")
        identity: SendingIdentity = self._sending_identity(db, site.user_id)
        if unsubscribe_service.is_unsubscribed(db, site.email):
            raise SiteCareError(f"{site.email} s’est désabonné : plus aucun message ne part vers cette adresse.")
        prospect: ProspectDB = await self._prospect_of(db, site)
        now: datetime = naive_utc_now()
        prospect_refusal: str | None = self._prospect_refusal(prospect, site.email, now)
        if prospect_refusal is not None:
            raise SiteCareError(prospect_refusal)
        sending: EmailSendingService = EmailSendingService(db)
        identification_refusal: str | None = sending.sender_identification_refusal(site.user_id, str(prospect.id))
        if identification_refusal:
            raise SiteCareError(identification_refusal)

        email_log_id: int = await self._send(
            db, site, identity, message, prospect_id=prospect.id, is_transactional=False
        )
        contact_lock_service.record_contact(prospect, MODULE_KEY, now)
        site.written_at = now
        site.last_email_log_id = email_log_id
        db.add(
            SiteCareSentMessage(
                user_id=site.user_id,
                site_id=site.id,
                email_log_id=email_log_id,
                kind=FIRST_MESSAGE,
                subject=message.subject,
                with_page_link=with_page_link,
                sent_at=now,
            )
        )
        db.commit()
        self._hold_back_campaigns(db, prospect.id)
        activity_log_service.record(
            category=ACTIVITY_CATEGORY,
            action="first_message_sent",
            title=f"Message envoyé à {site.business_name}",
            detail=message.subject,
            user_id=site.user_id,
            entity_type="site_care_site",
            entity_id=site.id,
        )

    async def send_monthly_report(self, db: Session, site: SiteCareSite, settings: OwnerSettings) -> datetime:
        """
        Send a client his monthly report.

        Args:
            db: Active database session.
            site: The client's site.
            settings: The owner's settings.

        Returns:
            When the report left.

        Raises:
            SiteCareError: The report cannot leave; the reason is in French.
        """
        if not site.email:
            raise SiteCareError("Pas d’adresse e-mail pour ce client.")
        identity: SendingIdentity = self._sending_identity(db, site.user_id)
        message: OutgoingMessage = self.writer_for(site, settings).monthly_report(site.checked_at)
        email_log_id: int = await self._send(
            db, site, identity, message, prospect_id=site.prospect_id, is_transactional=True
        )
        now: datetime = naive_utc_now()
        db.add(
            SiteCareSentMessage(
                user_id=site.user_id,
                site_id=site.id,
                email_log_id=email_log_id,
                kind=MONTHLY_REPORT,
                subject=message.subject,
                sent_at=now,
            )
        )
        db.commit()
        return now

    @staticmethod
    def reply_address(db: Session, site: SiteCareSite) -> str | None:
        """
        Where the page's « Me répondre » button writes to.

        Args:
            db: Active database session.
            site: The site the page is about.

        Returns:
            The reply address of the message that was sent (the answer then lands in the conversation), else the
            sender's own address; None when the owner has no sender yet.
        """
        if site.last_email_log_id is not None and db.get(EmailLog, site.last_email_log_id) is not None:
            return reply_capture_service.reply_address_for_log(site.last_email_log_id)
        try:
            return resolve_sending_identity(db, site.user_id).from_email
        except SendingNotConfiguredError:
            return None

    @staticmethod
    def sender_email(db: Session, user_id: int) -> str | None:
        """The address the owner's messages leave from, None while sending is not configured."""
        try:
            return resolve_sending_identity(db, user_id).from_email
        except SendingNotConfiguredError:
            return None

    async def _send(
        self,
        db: Session,
        site: SiteCareSite,
        identity: SendingIdentity,
        message: OutgoingMessage,
        *,
        prospect_id: int | None,
        is_transactional: bool,
    ) -> int:
        """
        Hand a message to the core's send path, signed like every email of the owner.

        Returns:
            The id of the core's email log.

        Raises:
            SiteCareError: The provider refused the message.
        """
        copy_to: str | None = inbox_copy_address(identity)
        try:
            result: dict = await EmailSendingService(db).send_via_user_identity(
                user_id=site.user_id,
                recipient_email=site.email or "",
                subject=message.subject,
                body_html=message.body_html + render_default_signature_html(db, site.user_id),
                recipient_name=site.business_name,
                prospect_id=str(prospect_id) if prospect_id is not None else None,
                bcc=[copy_to] if copy_to else None,
                is_transactional=is_transactional,
            )
        except Exception as exc:
            logger.warning("[SiteCare] message to site %s refused before sending: %s", site.id, exc)
            raise SiteCareError(f"Le message n’est pas parti : {exc}") from exc
        if not result.get("success") or result.get("email_log_id") is None:
            raise SiteCareError(f"Le message n’est pas parti : {result.get('error') or 'erreur inconnue'}")
        return int(result["email_log_id"])

    @staticmethod
    def _sending_identity(db: Session, user_id: int) -> SendingIdentity:
        """The owner's sender, or the reason he has none yet."""
        try:
            return resolve_sending_identity(db, user_id)
        except SendingNotConfiguredError as exc:
            raise SiteCareError(str(exc)) from exc

    @staticmethod
    def _prospect_refusal(prospect: ProspectDB, email: str, now: datetime) -> str | None:
        """Why the core forbids writing to a prospect, None when it allows it."""
        if prospect.do_not_contact:
            return "Ce prospect a demandé à ne plus être contacté."
        if prospect.is_dismissed:
            return "Ce prospect est écarté."
        if prospect.email_undeliverable and (prospect.email or "").lower() == email.lower():
            return "Son adresse e-mail est en erreur : les messages n’y arrivent pas."
        if contact_lock_service.is_locked_for_module(prospect, MODULE_KEY, now):
            locked_until: datetime | None = contact_lock_service.locked_until(prospect, now)
            module_label: str = contact_lock_service.module_label(prospect.contacted_by_module)
            until: str = f" jusqu’au {FrenchDates.day(locked_until.date())}" if locked_until else ""
            return f"Déjà contacté par le module {module_label} : on ne lui écrit pas{until}."
        return None

    async def _prospect_of(self, db: Session, site: SiteCareSite) -> ProspectDB:
        """
        The core prospect of a site's business, created the first time the business is written to.

        A business that comes from a core search is kept there by hand, the core's own way of turning a discarded
        candidate into a prospect; one the core already knows is reused.

        Raises:
            SiteCareError: The core refused to make it a prospect.
        """
        if site.prospect_id is None:
            candidate: ProspectSearchCandidate | None = (
                db.get(ProspectSearchCandidate, site.candidate_id) if site.candidate_id else None
            )
            site.prospect_id = (
                await self._keep_candidate(db, site.user_id, candidate)
                if candidate is not None
                else await self._create_prospect(db, site)
            )
            db.commit()
        prospect: ProspectDB | None = db.get(ProspectDB, site.prospect_id)
        if prospect is None:
            raise SiteCareError("Ce prospect n’existe plus dans la base.")
        if site.email and (prospect.email or "").lower() != site.email.lower():
            set_prospect_emails(prospect, [site.email, *(prospect.emails or [])])
            db.commit()
        return prospect

    @staticmethod
    async def _keep_candidate(db: Session, user_id: int, candidate: ProspectSearchCandidate) -> int:
        """Make a discarded candidate a prospect through the core's search, or reuse the prospect it already is."""
        if candidate.prospect_id is None:
            try:
                await prospect_search_service.keep_candidate(db, user_id, candidate.search_id, candidate.id)
            except ProspectSearchError as exc:
                db.refresh(candidate)
                if candidate.prospect_id is None:
                    raise SiteCareError(str(exc)) from exc
            db.refresh(candidate)
        if candidate.prospect_id is None:
            raise SiteCareError("Le prospect n’a pas pu être créé.")
        return int(candidate.prospect_id)

    @staticmethod
    async def _create_prospect(db: Session, site: SiteCareSite) -> int:
        """Create the prospect of a site that no core search found (added by hand)."""
        created = await prospect_service.create_prospect(
            db=db,
            prospect=ProspectCreate(
                name=site.business_name,
                city=site.city,
                country=site.country,
                phone=site.phone,
                email=site.email,
                website=site.website,
                website_status=WebsiteStatus.LIVE,
                google_maps_url=site.google_maps_url,
                google_rating=site.google_rating,
                google_reviews_count=site.google_reviews_count,
                category=TradeCatalog.resolve(site.trade or "entreprise").prospect_category,
                source=Source.MANUAL,
                confidence=3,
            ),
            user_id=site.user_id,
            organization_id=organization_service.user_org_id(db, site.user_id),
        )
        return int(created.id)

    @staticmethod
    def _hold_back_campaigns(db: Session, prospect_id: int) -> None:
        """A message by hand supersedes the campaigns: hold back the pending sends of this prospect."""
        try:
            CampaignQueueService(db).skip_pending_for_prospect(prospect_id, label="Contacté par Entretien de sites")
        except Exception:
            logger.warning("[SiteCare] could not hold back campaign sends of prospect %s", prospect_id, exc_info=True)


send_service = SendService()
