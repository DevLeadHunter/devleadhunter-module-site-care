"""What the routes of « Nouvelle recherche » receive and return (see ``docs/API.md``)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from devleadhunter_site_care.catalog import BusinessFamily, KeepRule, SearchSource
from devleadhunter_site_care.french_departments import FrenchDepartments


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


class LabelledChoice(BaseModel):
    """A choice of a search: its key, its name and, for some, a line that explains it."""

    key: str
    label: str
    hint: str | None = None


class OpenMapOptions(BaseModel):
    """What a search on the open map can ask for."""

    departments: list[LabelledChoice]
    families: list[LabelledChoice]
    keep_rules: list[LabelledChoice]
    max_count: int
    max_departments: int
    credit: str


class SearchOptions(BaseModel):
    """What a new search can ask for."""

    sources: list[LabelledChoice]
    countries: list[CountryOption]
    trades: list[TradeAvailability]
    max_count: int
    open_map: OpenMapOptions


class SearchCreateBody(BaseModel):
    """A new search, in the owner's base (the default) or on the open map."""

    source: SearchSource = SearchSource.OWN_BASE
    trades: list[str] = Field(default_factory=list, max_length=30)
    country: str = Field(default=FrenchDepartments.COUNTRY_CODE, min_length=2, max_length=2)
    cities: list[str] = Field(default_factory=list, max_length=20)
    departments: list[str] = Field(default_factory=list, max_length=20)
    families: list[BusinessFamily] = Field(default_factory=list, max_length=10)
    keep_rule: KeepRule = KeepRule.EVERY_SITE
    count: int = Field(default=50, ge=1, le=2000)

    @field_validator("departments")
    @classmethod
    def _known_departments(cls, departments: list[str]) -> list[str]:
        """Refuse a département the module does not know, so a typing mistake never searches nowhere."""
        unknown: list[str] = [code for code in departments if code.upper() not in FrenchDepartments.NAMES]
        if unknown:
            raise ValueError(f"Département inconnu : {', '.join(unknown)}.")
        return departments


class SearchView(BaseModel):
    """A search and how far it is."""

    id: int
    status: str
    status_label: str
    source: str
    source_label: str
    keep_rule_label: str
    requested_count: int
    checked_count: int
    imported_count: int
    progress_label: str
    trades_label: str
    zone_label: str
    note: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
