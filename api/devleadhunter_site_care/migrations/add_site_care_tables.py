"""Create the six tables of the module: sites, owner settings, searches, watch events, care plans, sent messages.

Every row is scoped to the user who owns the module's data (``user_id``), like the rest of the product. A table that
exists already is left as it is, so the migration can run again.

Run alone from the core's ``api/``: ``python -m devleadhunter_site_care.migrations.add_site_care_tables``.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine

from core.database import engine as core_engine

from devleadhunter_site_care.migrations.schema_changes import SiteCareSchemaChanges
from devleadhunter_site_care.models.care_plan import SiteCarePlan
from devleadhunter_site_care.models.owner_settings import SiteCareOwnerSettings
from devleadhunter_site_care.models.search import SiteCareSearch
from devleadhunter_site_care.models.sent_message import SiteCareSentMessage
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.models.watch_event import SiteCareWatchEvent


def run_migration(engine: Engine | None = None) -> None:
    """
    Create the module's tables that are missing.

    Args:
        engine: The database to migrate, the core's when omitted.
    """
    created: list[str] = SiteCareSchemaChanges(engine or core_engine).create_missing_tables(
        SiteCareSite, SiteCareOwnerSettings, SiteCareSearch, SiteCareWatchEvent, SiteCarePlan, SiteCareSentMessage
    )
    print(f"add_site_care_tables: created {', '.join(created) or 'nothing (all present)'}")


if __name__ == "__main__":
    run_migration()
