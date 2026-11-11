"""A search in words: what it targets, where it looks, how far it is, why it ended short."""

from __future__ import annotations

from typing import ClassVar

from services.prospect_search.trade_catalog import TradeCatalog

from devleadhunter_site_care.catalog import (
    ACTIVE_SEARCH_STATUSES,
    BUSINESS_FAMILY_LABELS,
    COUNTRY_LABELS,
    BusinessFamily,
    SearchSource,
)
from devleadhunter_site_care.french_departments import FrenchDepartments
from devleadhunter_site_care.models.search import SiteCareSearch


class SearchWording:
    """Writes what the dashboard shows of a search, so no screen composes a sentence."""

    STOPPED_BY_HAND_NOTE: ClassVar[str] = "Recherche arrêtée à la main. Les sites déjà gardés sont dans la liste."
    FAILED_NOTE: ClassVar[str] = (
        "La recherche s’est arrêtée sur une erreur. Les sites déjà regardés sont dans la liste."
    )

    @classmethod
    def targets_of(cls, search: SiteCareSearch) -> str:
        """
        The businesses a search targets.

        Args:
            search: The search.

        Returns:
            The trades asked for in the base, or the families asked for on the open map.
        """
        if cls._is_on_open_map(search):
            families: list[str] = search.families or []
            if len(families) >= len(BusinessFamily):
                return "Toutes les entreprises"
            return ", ".join(BUSINESS_FAMILY_LABELS[BusinessFamily(family)] for family in families)
        if not search.trades:
            return "Tous les métiers"
        return ", ".join(TradeCatalog.resolve(trade).label for trade in search.trades)

    @classmethod
    def zone_of(cls, search: SiteCareSearch) -> str:
        """
        Where a search looks.

        Args:
            search: The search.

        Returns:
            The country and the cities of a search in the base, or the départements of one on the open map.
        """
        if cls._is_on_open_map(search):
            return ", ".join(FrenchDepartments.label_of(code) for code in search.departments or [])
        country_label: str = COUNTRY_LABELS.get(search.country, search.country)
        return f"{country_label} : {', '.join(search.cities)}" if search.cities else country_label

    @classmethod
    def progress_of(cls, search: SiteCareSearch) -> str:
        """
        How far a search is.

        Args:
            search: The search.

        Returns:
            The sites looked at out of those asked for; on the open map, the sites read apart from the sites kept.
        """
        if not cls._is_on_open_map(search):
            looked_at: str = "sites regardés" if search.checked_count > 1 else "site regardé"
            return f"{search.checked_count} {looked_at} sur {search.requested_count}"
        if search.checked_count == 0 and search.status in ACTIVE_SEARCH_STATUSES:
            return "Lecture de la liste des entreprises…"
        return f"{cls._read_and_kept_counts(search)} sur {search.requested_count} demandés"

    @classmethod
    def short_of_sites_note(cls, search: SiteCareSearch) -> str | None:
        """
        Why a search ended with fewer sites than asked.

        Args:
            search: The search, once its source has nothing left for it.

        Returns:
            The reason, None when the search has every site it was asked for.
        """
        if search.imported_count >= search.requested_count:
            return None
        if cls._is_on_open_map(search):
            if search.checked_count == 0:
                return "Tous les sites de cette zone ont déjà été lus."
            return f"{cls._read_and_kept_counts(search)} : la zone n’en a pas d’autres pour ces critères."
        if search.imported_count == 0:
            return "Aucune entreprise disponible pour ces critères."
        return (
            f"La base n’avait que {search.imported_count} entreprises pour ces critères. Les recherches "
            "du module Sites web en apportent de nouvelles."
        )

    @staticmethod
    def _is_on_open_map(search: SiteCareSearch) -> bool:
        """Whether a search goes through the open map rather than the owner's base."""
        return search.source == SearchSource.OPEN_MAP.value

    @staticmethod
    def _read_and_kept_counts(search: SiteCareSearch) -> str:
        """« 196 sites lus, 28 gardés », each word agreeing with its count."""
        read_wording: str = "sites lus" if search.checked_count > 1 else "site lu"
        kept_wording: str = "gardés" if search.imported_count > 1 else "gardé"
        return f"{search.checked_count} {read_wording}, {search.imported_count} {kept_wording}"
