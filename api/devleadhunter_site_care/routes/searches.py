"""« Nouvelle recherche »: what the base holds, and the searches that bring it into the module."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from services.auth_service import get_current_active_user
from services.prospect_search.trade_catalog import TradeCatalog

from devleadhunter_site_care.models.search import SiteCareSearch
from devleadhunter_site_care.schemas.search import (
    CountryOption,
    SearchCreateBody,
    SearchOptions,
    SearchView,
    TradeAvailability,
)
from devleadhunter_site_care.services.search_service import COUNTRY_LABELS, AvailableTrade, search_service
from devleadhunter_site_care.services.site_service import SiteCareError

router = APIRouter(prefix="/site-care", tags=["site-care-searches"])

_STATUS_LABELS: dict[str, str] = {
    "pending": "En attente",
    "running": "En cours",
    "completed": "Terminée",
    "failed": "Arrêtée",
}


def _search_view(search: SiteCareSearch) -> SearchView:
    """
    A search as the dashboard shows it.

    Args:
        search: The stored search.

    Returns:
        Its view, the trades and the zone in words.
    """
    country_label: str = COUNTRY_LABELS.get(search.country, search.country)
    return SearchView(
        id=search.id,
        status=search.status,
        status_label=_STATUS_LABELS.get(search.status, search.status),
        requested_count=search.requested_count,
        checked_count=search.checked_count,
        imported_count=search.imported_count,
        trades_label=(
            ", ".join(TradeCatalog.resolve(trade).label for trade in search.trades)
            if search.trades
            else "Tous les métiers"
        ),
        zone_label=f"{country_label} : {', '.join(search.cities)}" if search.cities else country_label,
        note=search.note,
        created_at=search.created_at,
        completed_at=search.completed_at,
    )


@router.get("/search-options", response_model=SearchOptions)
async def get_search_options(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SearchOptions:
    """The countries and trades the user's base holds businesses for, with how many."""
    trades: list[AvailableTrade] = search_service.available_trades(db, current_user.id)
    count_by_country: dict[str, int] = {}
    for trade in trades:
        for country, count in trade.count_by_country.items():
            count_by_country[country] = count_by_country.get(country, 0) + count
    return SearchOptions(
        countries=[
            CountryOption(code=country, label=COUNTRY_LABELS.get(country, country), available_count=count)
            for country, count in sorted(count_by_country.items(), key=lambda entry: -entry[1])
        ],
        trades=[
            TradeAvailability(key=trade.key, label=trade.label, available_by_country=trade.count_by_country)
            for trade in trades
        ],
    )


@router.post("/searches", response_model=SearchView)
async def create_search(
    body: SearchCreateBody,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SearchView:
    """Queue a search; 409 when one of the user's searches is still running."""
    try:
        search: SiteCareSearch = search_service.create(
            db,
            current_user.id,
            trades=body.trades,
            country=body.country,
            cities=body.cities,
            requested_count=body.count,
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
