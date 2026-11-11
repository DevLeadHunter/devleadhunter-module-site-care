"""« Suivis »: the clients under monthly care and their monthly report."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.database import get_db
from models.user import User
from services.auth_service import get_current_active_user
from services.prospect_search.trade_catalog import TradeCatalog

from devleadhunter_site_care.models.care_plan import SiteCarePlan
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.schemas.care_plan import CarePlanListResponse, CarePlanStats, CarePlanView
from devleadhunter_site_care.services.care_plan_service import care_plan_service
from devleadhunter_site_care.services.owner_settings_service import OwnerSettings, owner_settings_service
from devleadhunter_site_care.services.site_message import Money, SheetLines
from devleadhunter_site_care.services.site_points import FrenchDates
from devleadhunter_site_care.services.site_service import SiteCareError, site_service

router = APIRouter(prefix="/site-care/care-plans", tags=["site-care-care-plans"])


def _plan_view(plan: SiteCarePlan, site: SiteCareSite, settings: OwnerSettings, now: datetime) -> CarePlanView:
    """
    A client under care as the dashboard shows it.

    Args:
        plan: The client's plan.
        site: His site.
        settings: The owner's settings.
        now: The current instant (naive UTC).

    Returns:
        The line of the « Suivis » page.
    """
    is_due: bool = care_plan_service.is_report_due(plan, now)
    if not is_due and plan.last_report_at is not None:
        report_detail: str = f"Le {FrenchDates.day(plan.last_report_at.date())}"
    elif plan.last_report_at is None and (plan.started_at.year, plan.started_at.month) == (now.year, now.month):
        first_of_next_month: date = date(now.year + (now.month == 12), now.month % 12 + 1, 1)
        report_detail = f"Premier rapport le {FrenchDates.day(first_of_next_month)}"
    else:
        report_detail = "Le rapport de ce mois n’est pas encore parti"
    return CarePlanView(
        id=plan.id,
        site_id=site.id,
        business_name=site.business_name,
        trade_label=TradeCatalog.resolve(site.trade).label if site.trade else "",
        city=site.city,
        domain=site.host,
        last_check_summary=SheetLines.check_summary(site_service.summary_of(site, settings.writing_rules)),
        last_checked_label=f"Regardé le {FrenchDates.day(site.checked_at.date())}",
        report_state="due" if is_due else "sent",
        report_label="À envoyer" if is_due else "Envoyé",
        report_detail=report_detail,
        monthly_label=f"{Money.euros(plan.monthly_price_cents)} par mois",
        since_label=f"Depuis le {FrenchDates.day(plan.started_at.date())}",
        can_send_report=is_due and bool(site.email),
    )


def _owned_plan(db: Session, user: User, plan_id: int) -> tuple[SiteCarePlan, SiteCareSite]:
    """
    The user's running plan with its site, or a 404.

    Args:
        db: Active database session.
        user: The connected user.
        plan_id: The plan asked for.

    Returns:
        The plan and its site.
    """
    plan: SiteCarePlan | None = care_plan_service.get(db, user.id, plan_id)
    site: SiteCareSite | None = db.get(SiteCareSite, plan.site_id) if plan is not None else None
    if plan is None or site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suivi introuvable")
    return plan, site


@router.get("", response_model=CarePlanListResponse)
async def list_care_plans(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CarePlanListResponse:
    """The user's clients under monthly care."""
    now: datetime = naive_utc_now()
    settings: OwnerSettings = owner_settings_service.get(db, current_user.id)
    plans: list[tuple[SiteCarePlan, SiteCareSite]] = care_plan_service.active_plans(db, current_user.id)
    views: list[CarePlanView] = [_plan_view(plan, site, settings, now) for plan, site in plans]
    return CarePlanListResponse(
        stats=CarePlanStats(
            client_count=len(views),
            monthly_revenue_label=Money.euros(sum(plan.monthly_price_cents for plan, _ in plans)),
            reports_due_count=sum(1 for view in views if view.report_state == "due"),
        ),
        plans=views,
    )


@router.post("/{plan_id}/report", response_model=CarePlanView)
async def send_monthly_report(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CarePlanView:
    """Send the client this month's report; 409 with the reason when it cannot leave."""
    plan, site = _owned_plan(db, current_user, plan_id)
    settings: OwnerSettings = owner_settings_service.get(db, current_user.id)
    try:
        await care_plan_service.send_report(db, plan, site, settings)
    except SiteCareError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _plan_view(plan, site, settings, naive_utc_now())


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_care_plan(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    """End the monthly care of a site."""
    plan, _ = _owned_plan(db, current_user, plan_id)
    care_plan_service.stop(db, plan)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
