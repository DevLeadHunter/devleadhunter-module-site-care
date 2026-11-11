"""The monthly care: the clients who took it, and the report each of them gets every month."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now

from devleadhunter_site_care.models.care_plan import SiteCarePlan
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings
from devleadhunter_site_care.services.send_service import send_service
from devleadhunter_site_care.services.site_service import SiteCareError

_MIN_MONTHLY_PRICE_CENTS: int = 100
_MAX_MONTHLY_PRICE_CENTS: int = 100_000


class CarePlanService:
    """Starts and stops the monthly care of a site, and sends its reports."""

    def active_plans(self, db: Session, user_id: int) -> list[tuple[SiteCarePlan, SiteCareSite]]:
        """
        The owner's clients under care, with their site.

        Args:
            db: Active database session.
            user_id: The owner.

        Returns:
            The running plans, the oldest first.
        """
        rows = db.execute(
            select(SiteCarePlan, SiteCareSite)
            .join(SiteCareSite, SiteCareSite.id == SiteCarePlan.site_id)
            .where(SiteCarePlan.user_id == user_id, SiteCarePlan.stopped_at.is_(None))
            .order_by(SiteCarePlan.started_at)
        ).all()
        return [(plan, site) for plan, site in rows]

    def active_plan_of(self, db: Session, site_id: int) -> SiteCarePlan | None:
        """
        The running plan of a site.

        Args:
            db: Active database session.
            site_id: The site.

        Returns:
            The plan, or None when the site is not under care.
        """
        return (
            db.execute(select(SiteCarePlan).where(SiteCarePlan.site_id == site_id, SiteCarePlan.stopped_at.is_(None)))
            .scalars()
            .first()
        )

    def active_site_ids(self, db: Session, site_ids: list[int]) -> set[int]:
        """
        Which sites of a list are under care.

        Args:
            db: Active database session.
            site_ids: The sites of a page of the list.

        Returns:
            The ids of those under care.
        """
        if not site_ids:
            return set()
        return set(
            db.execute(
                select(SiteCarePlan.site_id).where(
                    SiteCarePlan.site_id.in_(site_ids), SiteCarePlan.stopped_at.is_(None)
                )
            ).scalars()
        )

    def start(self, db: Session, site: SiteCareSite, monthly_price_cents: int) -> SiteCarePlan:
        """
        Put a site under monthly care.

        Args:
            db: Active database session.
            site: The client's site.
            monthly_price_cents: What the client pays each month.

        Returns:
            The new plan.

        Raises:
            SiteCareError: The site is already under care, or the price is out of range.
        """
        if self.active_plan_of(db, site.id) is not None:
            raise SiteCareError("Ce site est déjà en suivi.")
        if not _MIN_MONTHLY_PRICE_CENTS <= monthly_price_cents <= _MAX_MONTHLY_PRICE_CENTS:
            raise SiteCareError("Le prix du suivi doit être compris entre 1 € et 1 000 € par mois.")
        plan: SiteCarePlan = SiteCarePlan(
            user_id=site.user_id, site_id=site.id, monthly_price_cents=monthly_price_cents
        )
        db.add(plan)
        db.commit()
        return plan

    def get(self, db: Session, user_id: int, plan_id: int) -> SiteCarePlan | None:
        """
        One of the owner's running plans.

        Args:
            db: Active database session.
            user_id: The owner.
            plan_id: The plan.

        Returns:
            The plan, or None when it is not his or has stopped.
        """
        plan: SiteCarePlan | None = db.get(SiteCarePlan, plan_id)
        if plan is None or plan.user_id != user_id or plan.stopped_at is not None:
            return None
        return plan

    def stop(self, db: Session, plan: SiteCarePlan) -> None:
        """
        End a site's monthly care.

        Args:
            db: Active database session.
            plan: The plan to end.
        """
        plan.stopped_at = naive_utc_now()
        db.commit()

    @staticmethod
    def is_report_due(plan: SiteCarePlan, now: datetime) -> bool:
        """Whether this month's report has not left yet."""
        last: datetime | None = plan.last_report_at
        return last is None or (last.year, last.month) != (now.year, now.month)

    async def send_report(self, db: Session, plan: SiteCarePlan, site: SiteCareSite, settings: OwnerSettings) -> None:
        """
        Send a client this month's report.

        Args:
            db: Active database session.
            plan: The client's plan.
            site: His site.
            settings: The owner's settings.

        Raises:
            SiteCareError: This month's report already left, or the message was refused.
        """
        if not self.is_report_due(plan, naive_utc_now()):
            raise SiteCareError("Le rapport de ce mois est déjà parti.")
        plan.last_report_at = await send_service.send_monthly_report(db, site, settings)
        db.commit()


care_plan_service = CarePlanService()
