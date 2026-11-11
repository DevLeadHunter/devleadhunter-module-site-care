"""« Nouvelle recherche »: what a search can ask for, and the searches that bring businesses into the module."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from services.auth_service import get_current_active_user

from devleadhunter_site_care.catalog import (
    BUSINESS_FAMILY_LABELS,
    COUNTRY_LABELS,
    KEEP_RULE_HINTS,
    KEEP_RULE_LABELS,
    SEARCH_SOURCE_HINTS,
    SEARCH_SOURCE_LABELS,
    KeepRule,
    SearchSource,
)
from devleadhunter_site_care.french_departments import FrenchDepartments
from devleadhunter_site_care.models.search import SiteCareSearch
from devleadhunter_site_care.schemas.search import (
    CountryOption,
    LabelledChoice,
    OpenMapOptions,
    SearchCreateBody,
    SearchOptions,
    SearchView,
    TradeAvailability,
)
from devleadhunter_site_care.services.search_service import (
    AvailableTrade,
    SearchRequest,
    SearchService,
    search_service,
)
from devleadhunter_site_care.services.search_wording import SearchWording
from devleadhunter_site_care.services.site_service import SiteCareError

router = APIRouter(prefix="/site-care", tags=["site-care-searches"])

_STATUS_LABELS: dict[str, str] = {
    "pending": "En attente",
    "running": "En cours",
    "completed": "Terminée",
    "failed": "Arrêtée",
}
_SOURCE_CHOICES: list[LabelledChoice] = [
    LabelledChoice(key=source.value, label=label, hint=SEARCH_SOURCE_HINTS[source])
    for source, label in SEARCH_SOURCE_LABELS.items()
]
_OPEN_MAP_OPTIONS: OpenMapOptions = OpenMapOptions(
    departments=[LabelledChoice(key=code, label=FrenchDepartments.label_of(code)) for code in FrenchDepartments.NAMES],
    families=[LabelledChoice(key=family.value, label=label) for family, label in BUSINESS_FAMILY_LABELS.items()],
    keep_rules=[
        LabelledChoice(key=rule.value, label=label, hint=KEEP_RULE_HINTS[rule])
        for rule, label in KEEP_RULE_LABELS.items()
    ],
    max_count=SearchService.MAX_OPEN_MAP_REQUESTED_COUNT,
    max_departments=SearchService.MAX_DEPARTMENTS,
    credit="Données © les contributeurs d’OpenStreetMap, sous licence ODbL.",
)


def _search_view(search: SiteCareSearch) -> SearchView:
    """
    A search as the dashboard shows it.

    Args:
        search: The stored search.

    Returns:
        Its view, the businesses, the zone and the progress in words.
    """
    return SearchView(
        id=search.id,
        status=search.status,
        status_label=_STATUS_LABELS.get(search.status, search.status),
        source=search.source,
        source_label=SEARCH_SOURCE_LABELS[SearchSource(search.source)],
        keep_rule_label=KEEP_RULE_LABELS[KeepRule(search.keep_rule)],
        requested_count=search.requested_count,
        checked_count=search.checked_count,
        imported_count=search.imported_count,
        progress_label=SearchWording.progress_of(search),
        trades_label=SearchWording.targets_of(search),
        zone_label=SearchWording.zone_of(search),
        note=search.note,
        created_at=search.created_at,
        completed_at=search.completed_at,
    )


@router.get("/search-options", response_model=SearchOptions)
async def get_search_options(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SearchOptions:
    """What a search can ask for: the countries and trades of the user's base, and the open map's choices."""
    trades: list[AvailableTrade] = search_service.available_trades(db, current_user.id)
    count_by_country: dict[str, int] = {}
    for trade in trades:
        for country, count in trade.count_by_country.items():
            count_by_country[country] = count_by_country.get(country, 0) + count
    return SearchOptions(
        sources=_SOURCE_CHOICES,
        countries=[
            CountryOption(code=country, label=COUNTRY_LABELS.get(country, country), available_count=count)
            for country, count in sorted(count_by_country.items(), key=lambda entry: -entry[1])
        ],
        trades=[
            TradeAvailability(key=trade.key, label=trade.label, available_by_country=trade.count_by_country)
            for trade in trades
        ],
        max_count=SearchService.MAX_REQUESTED_COUNT,
        open_map=_OPEN_MAP_OPTIONS,
    )


@router.post("/searches", response_model=SearchView)
async def create_search(
    body: SearchCreateBody,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SearchView:
    """Queue a search; 409 when one of the user's searches is still running or the open map has no zone."""
    try:
        search: SiteCareSearch = search_service.create(
            db,
            current_user.id,
            SearchRequest(
                requested_count=body.count,
                source=body.source,
                trades=body.trades,
                country=body.country,
                cities=body.cities,
                departments=body.departments,
                families=body.families,
                keep_rule=body.keep_rule,
            ),
        )
    except SiteCareError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _search_view(search)


@router.get("/searches/current", response_model=SearchView | None)
async def get_current_search(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SearchView | None:
    """The search the user is waiting for, else his last one, else nothing."""
    search: SiteCareSearch | None = search_service.current(db, current_user.id)
    return _search_view(search) if search is not None else None


@router.post("/searches/current/stop", response_model=SearchView | None)
async def stop_current_search(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SearchView | None:
    """Stop the user's running search; the sites it already brought stay in the list."""
    search: SiteCareSearch | None = search_service.stop(db, current_user.id)
    return _search_view(search) if search is not None else None
