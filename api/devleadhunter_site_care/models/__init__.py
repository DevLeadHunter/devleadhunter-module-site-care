"""
The tables of the « Entretien de sites » module.

Importing this package registers every one of them on the core's metadata, which is what the module's ``load()``
does before ``init_db()`` creates the missing tables.
"""

from devleadhunter_site_care.models.care_plan import SiteCarePlan
from devleadhunter_site_care.models.owner_settings import SiteCareOwnerSettings
from devleadhunter_site_care.models.search import SiteCareSearch
from devleadhunter_site_care.models.sent_message import SiteCareSentMessage
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.models.watch_event import SiteCareWatchEvent

__all__ = [
    "SiteCareOwnerSettings",
    "SiteCarePlan",
    "SiteCareSearch",
    "SiteCareSentMessage",
    "SiteCareSite",
    "SiteCareWatchEvent",
]
