"""What the settings routes receive and return (see ``docs/API.md``)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PriceLine(BaseModel):
    """A correction and its price; None for a correction that is quoted."""

    key: str
    label: str = ""
    price_cents: int | None = Field(default=None, ge=0, le=1_000_000)


class PointSwitch(BaseModel):
    """A point and whether the owner wants it looked at."""

    key: str
    family_label: str = ""
    label: str = ""
    is_enabled: bool = True


class PresenterView(BaseModel):
    """Who writes, as the message and the page show him."""

    name: str = Field(default="", max_length=120)
    role: str = Field(default="", max_length=160)
    tagline: str = Field(default="", max_length=300)
    site_url: str = Field(default="", max_length=300)
    photo_url: str = Field(default="", max_length=500)


class OwnerSettingsView(BaseModel):
    """The owner's settings, read and written in the same shape."""

    prices: list[PriceLine]
    monthly_price_cents: int = Field(..., ge=100, le=100_000)
    trigger: str = Field(..., pattern="^(fix|watch)$")
    points: list[PointSwitch]
    presenter: PresenterView
    sender_email: str | None = None
