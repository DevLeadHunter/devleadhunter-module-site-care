"""What the routes of « Nouvelle recherche » receive and return (see ``docs/API.md``)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CountryOption(BaseModel):
    """A country the base holds businesses for."""

    code: str
    label: str
    available_count: int


class TradeAvailability(BaseModel):
    """A trade the base holds businesses for, with how many per country."""

    key: str
    label: str
    available_by_country: dict[str, int]


class SearchOptions(BaseModel):
    """What a new search can ask for."""

    countries: list[CountryOption]
    trades: list[TradeAvailability]


class SearchCreateBody(BaseModel):
    """A new search."""

    trades: list[str] = Field(default_factory=list, max_length=30)
    country: str = Field(default="FR", min_length=2, max_length=2)
    cities: list[str] = Field(default_factory=list, max_length=20)
    count: int = Field(default=50, ge=1, le=300)


class SearchView(BaseModel):
    """A search and how far it is."""

    id: int
    status: str
    status_label: str
    requested_count: int
    checked_count: int
    imported_count: int
    trades_label: str
    zone_label: str
    note: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
