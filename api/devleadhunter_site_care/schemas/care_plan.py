"""What the care plan routes return (see ``docs/API.md``)."""

from __future__ import annotations

from pydantic import BaseModel


class CarePlanStats(BaseModel):
    """The three figures above the clients."""

    client_count: int
    monthly_revenue_label: str
    reports_due_count: int


class CarePlanView(BaseModel):
    """A client under monthly care."""

    id: int
    site_id: int
    business_name: str
    trade_label: str
    city: str | None = None
    domain: str
    last_check_summary: str
    last_checked_label: str
    report_state: str
    report_label: str
    report_detail: str
    monthly_label: str
    since_label: str
    can_send_report: bool


class CarePlanListResponse(BaseModel):
    """The clients under care."""

    stats: CarePlanStats
    plans: list[CarePlanView]
