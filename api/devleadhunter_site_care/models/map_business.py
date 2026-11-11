"""Map business model — one business the open map lists with a website, waiting to be read or already read."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.clock import naive_utc_now
from core.database import UTF8MB4_TABLE_OPTIONS, Base


class SiteCareMapBusiness(Base):
    """
    A business of the open map (OpenStreetMap) whose website a search can read.

    A row stays once its site was read, whatever the search kept of it: the next search on the same département
    never reads that site again.

    Attributes:
        user_id: The owner.
        department: The French département it was listed in.
        family: Its family of businesses (craft, shop, office…).
        map_reference: Its object on the map (« node/123 »).
        business_name: The business.
        trade: Its trade, the core's key when the core knows it, else its name in French.
        city: Its town, when the map gives it.
        phone: Its phone number, when the map gives it.
        email: Its email address, when the map gives it.
        website: Its site's address.
        host: The site's host without « www. », one per owner.
        latitude: Where it is, to name its town when the map does not.
        longitude: Where it is.
        read_at: When its site was read, None while it waits.
        was_kept: Whether the search that read it kept the site.
    """

    __tablename__ = "site_care_map_businesses"
    __table_args__ = (
        UniqueConstraint("user_id", "host", name="uq_site_care_map_businesses_user_host"),
        UTF8MB4_TABLE_OPTIONS,
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    family: Mapped[str] = mapped_column(String(12), nullable=False)
    map_reference: Mapped[str] = mapped_column(String(32), nullable=False)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str] = mapped_column(String(500), nullable=False)
    host: Mapped[str] = mapped_column(String(190), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    was_kept: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=naive_utc_now, nullable=False)

    def __repr__(self) -> str:
        """String representation of the map business."""
        return f"<SiteCareMapBusiness id={self.id} host={self.host} department={self.department}>"
