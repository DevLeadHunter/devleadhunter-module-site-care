"""Care plan model — a client who took the monthly care of his site."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from core.clock import naive_utc_now
from core.database import UTF8MB4_TABLE_OPTIONS, Base


class SiteCarePlan(Base):
    """
    The monthly care of one site: it is checked regularly and its owner gets a report each month.

    Attributes:
        user_id: The owner of the module's data.
        site_id: The site under care.
        monthly_price_cents: What the client pays each month.
        started_at: When the care began.
        stopped_at: When it ended, None while it runs.
        last_report_at: When the last monthly report left.
    """

    __tablename__ = "site_care_plans"
    __table_args__ = (UTF8MB4_TABLE_OPTIONS,)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    site_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    monthly_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(default=naive_utc_now, nullable=False)
    stopped_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_report_at: Mapped[datetime | None] = mapped_column(nullable=True)
