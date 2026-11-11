"""Let a search go through the open map: the map's businesses get their table, a search its source and its zone.

``site_care_map_businesses`` holds the businesses OpenStreetMap lists with a website, read or waiting. A search gains
where it looks (``source``, ``departments``, ``families``), what it keeps (``keep_rule``) and how far it fetched the
map (``collected_departments``). A table or a column that exists already is left as it is, so the migration can run
again.

Run alone from the core's ``api/``: ``python -m devleadhunter_site_care.migrations.add_site_care_open_map_search``.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine

from core.database import engine as core_engine

from devleadhunter_site_care.catalog import KeepRule, SearchSource
from devleadhunter_site_care.migrations.schema_changes import SiteCareSchemaChanges
from devleadhunter_site_care.models.map_business import SiteCareMapBusiness
from devleadhunter_site_care.models.search import SiteCareSearch

# A JSON column takes no default on MySQL: the searches made before keep NULL, read as an empty list.
_SEARCH_COLUMNS: dict[str, str] = {
    "source": f"VARCHAR(8) NOT NULL DEFAULT '{SearchSource.OWN_BASE.value}'",
    "departments": "JSON NULL",
    "families": "JSON NULL",
    "collected_departments": "JSON NULL",
    "keep_rule": f"VARCHAR(12) NOT NULL DEFAULT '{KeepRule.EVERY_SITE.value}'",
}


def run_migration(engine: Engine | None = None) -> None:
    """
    Create the map businesses' table and add the search's new columns, whichever are missing.

    Args:
        engine: The database to migrate, the core's when omitted.
    """
    changes: SiteCareSchemaChanges = SiteCareSchemaChanges(engine or core_engine)
    created: list[str] = changes.create_missing_tables(SiteCareMapBusiness)
    added: list[str] = changes.add_missing_columns(SiteCareSearch.__tablename__, _SEARCH_COLUMNS)
    print(
        f"add_site_care_open_map_search: created {', '.join(created) or 'no table'}, "
        f"added {', '.join(added) or 'no column'}"
    )


if __name__ == "__main__":
    run_migration()
