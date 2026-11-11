"""The module's tests run on the core's fixtures, from the core's ``api/``.

``python -m pytest ../../devleadhunter-module-site-care/api/tests`` from the core's ``api/``: ``tests`` then names the
core's test package (this folder has no ``__init__.py``, so it never shadows it), whose fixtures give each test an
in-memory database with every table — the module's included, its models being loaded below — and keep the outside
world offline. The core's own autouse fixture leaves no module installed; the one here installs this module after
it, switched off as in production, until a test asks for ``site_care_module_switched_on``. No test reads a real
site: a check is given the reading it would have made.
"""

from collections.abc import Iterator
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from api.v1.product_module_mounting import include_product_module_routers
from core.database import get_db
from core.product_modules.registry import product_module_registry
from enums.sending_provider import SendingProvider
from models.user import User
from services.auth_service import AuthService
from services.product_module_service import product_module_service
from tests.conftest import *  # noqa: F403

from devleadhunter_site_care.catalog import BusinessFamily
from devleadhunter_site_care.module import SiteCareModule
from devleadhunter_site_care.services import search_service as search_service_module
from devleadhunter_site_care.services import send_service as send_service_module
from devleadhunter_site_care.services import watch_service as watch_service_module
from devleadhunter_site_care.services.open_map import (
    ListedBusiness,
    OpenMapAnswer,
    OpenMapDirectory,
    TownLocator,
)
from devleadhunter_site_care.services.site_reader import SiteReading
from devleadhunter_site_care.services.wordpress_releases import WordPressReleases

_SITE_CARE_MODULE: SiteCareModule = SiteCareModule()
_SITE_CARE_MODULE.load()

CHECK_DAY: datetime = datetime(2026, 11, 11, 10, 0, 0)


@pytest.fixture(autouse=True)
def site_care_module_installed(no_product_module_installed: None) -> Iterator[SiteCareModule]:
    """The module installed next to the core and switched off, its production default."""
    product_module_registry.use([_SITE_CARE_MODULE])
    yield _SITE_CARE_MODULE


@pytest.fixture(autouse=True)
def wordpress_org_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """wordpress.org is never asked: the current branch is 7.1."""

    async def current_branch(_self: WordPressReleases) -> tuple[int, int]:
        return (7, 1)

    monkeypatch.setattr(WordPressReleases, "current_branch", current_branch)


@pytest.fixture(autouse=True)
def open_map_answers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """
    OpenStreetMap and the list of communes are never asked.

    Returns:
        What the open map answers per département code, filled by a test; a département missing here has no
        business. A point is placed in no commune unless a test says otherwise.
    """
    answer_by_department: dict[str, str] = {}

    async def businesses_of(
        _self: OpenMapDirectory, department: str, families: list[BusinessFamily]
    ) -> list[ListedBusiness]:
        return OpenMapAnswer.businesses_of(answer_by_department.get(department, ""), families)

    async def town_at(_self: TownLocator, _latitude: float, _longitude: float) -> str | None:
        return None

    monkeypatch.setattr(OpenMapDirectory, "businesses_of", businesses_of)
    monkeypatch.setattr(TownLocator, "town_at", town_at)
    return answer_by_department


@pytest.fixture
def site_care_module_switched_on(db: Session, site_care_module_installed: SiteCareModule) -> SiteCareModule:
    """The module switched on in the test database, the way the super admin does it."""
    product_module_service.set_enabled(db, SiteCareModule.key, True, user_id=1)
    return site_care_module_installed


@pytest.fixture
def owner(db: Session) -> User:
    """The user who owns the module's data."""
    user = User(name="Léo Guillaume", email="leo@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def auth_headers(owner: User) -> dict[str, str]:
    """The owner's bearer token, as the dashboard sends it."""
    return {"Authorization": f"Bearer {AuthService.create_access_token({'sub': owner.email})}"}


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """The installed modules' routers mounted the way the core mounts them, on the test's database."""
    app = FastAPI()
    v1_router = APIRouter()
    include_product_module_routers(v1_router)
    app.include_router(v1_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def background_sessions(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    """The background loop opens its own sessions: they go to the test's database."""
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(search_service_module, "SessionLocal", session_factory)
    monkeypatch.setattr(watch_service_module, "SessionLocal", session_factory)


@pytest.fixture
def sender_configured(monkeypatch: pytest.MonkeyPatch, resend_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The owner has a working sender; the payloads handed to Resend are returned."""
    monkeypatch.setattr(
        send_service_module,
        "resolve_sending_identity",
        lambda _db, _user_id: SimpleNamespace(
            provider=SendingProvider.RESEND.value,
            gmail_account=None,
            from_email="leo@mail.example.com",
            from_name="Léo",
            resend_api_key="re_test",
        ),
    )
    monkeypatch.setattr(send_service_module, "inbox_copy_address", lambda _identity: None)
    return resend_payloads


def reading_of(host: str = "jardins-guillot.test", **facts: Any) -> SiteReading:
    """
    A reading of a healthy home page, with the facts a test changes.

    Args:
        host: The site's host.
        facts: The fields of :class:`SiteReading` to override.

    Returns:
        The reading a check of that site would have made on :data:`CHECK_DAY`.
    """
    healthy: dict[str, Any] = {
        "host": host,
        "read_at": CHECK_DAY,
        "status_code": 200,
        "https": "ok",
        "certificate_end": datetime(2027, 2, 1),
        "powered_by": "PHP/8.4.1",
        "generators": ["WordPress 7.1"],
        "cms": "WordPress",
        "has_viewport": True,
        "has_description": True,
        "has_structured_data": True,
        "has_tel_link": True,
        "shows_phone": True,
        "page_digits": "0299000000",
        "emails": [f"contact@{host}"],
        "copyright_years": [2026],
        "has_mail_server": True,
        "has_spf": True,
        "has_dmarc": True,
        "shown_mail_domains": {host: True},
    }
    healthy.update(facts)
    return SiteReading(**healthy)
