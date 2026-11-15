"""The assistant: a question understood with or without the language model, answered from the owner's sites."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pytest
from conftest import CHECK_DAY
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.email_log import EmailLog
from models.user import User
from services.llm_service import LLMService

from devleadhunter_site_care.catalog import IssueKind, SiteStatus, SiteTab
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.services.assistant_service import (
    AssistantIntent,
    AssistantRequest,
    AssistantService,
)

_API: str = "/api/v1/site-care/assistant"


@pytest.fixture(autouse=True)
def language_model_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """The language model is off: the words of a question alone are read."""
    monkeypatch.setattr(LLMService, "is_configured", property(lambda _self: False))


def _site(
    db: Session,
    owner: User,
    *,
    host: str,
    kinds: tuple[IssueKind, ...],
    written_at: datetime | None = None,
    page_opened_at: datetime | None = None,
) -> SiteCareSite:
    """A site to write to, with its kinds of issue."""
    site = SiteCareSite(
        user_id=owner.id,
        business_name=f"Entreprise {host}",
        trade="paysagiste",
        city="Rennes",
        website=f"https://{host}",
        host=host,
        email=f"contact@{host}",
        status=SiteStatus.TO_WRITE.value,
        kinds_filter="," + ",".join(kind.value for kind in kinds) + ",",
        search_text=f"entreprise {host} rennes",
        checked_at=CHECK_DAY,
        page_slug=host,
        written_at=written_at,
        page_opened_at=page_opened_at,
    )
    db.add(site)
    db.commit()
    return site


def test_the_words_alone_tell_the_kind_of_issue_and_the_tab() -> None:
    assert AssistantService.understand_from_words("Les sites piratés à contacter") == AssistantRequest(
        intent=AssistantIntent.SEARCH, kind=IssueKind.HACK
    )
    assert AssistantService.understand_from_words("Les sites déjà contactés") == AssistantRequest(
        intent=AssistantIntent.SEARCH, tab=SiteTab.WRITTEN
    )


def test_the_words_alone_tell_a_count_and_the_replies() -> None:
    assert AssistantService.understand_from_words("Combien de sites par type de souci ?").intent == (
        AssistantIntent.COUNT
    )
    assert AssistantService.understand_from_words("Qui m’a répondu ou a ouvert sa page ?").intent == (
        AssistantIntent.REPLIES
    )


def test_an_answer_of_the_language_model_out_of_bounds_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    async def answer(_self: LLMService, _messages: list[dict[str, Any]], **_options: object) -> dict[str, Any] | None:
        return {"intent": "search", "kind": "ok", "place": "x" * 200, "tab": "nothing"}

    monkeypatch.setattr(LLMService, "is_configured", property(lambda _self: True))
    monkeypatch.setattr(LLMService, "complete_json", answer)

    assert asyncio.run(AssistantService().understand("des sites")) == AssistantRequest(intent=AssistantIntent.SEARCH)


def test_an_unknown_intent_falls_back_on_the_words(monkeypatch: pytest.MonkeyPatch) -> None:
    async def answer(_self: LLMService, _messages: list[dict[str, Any]], **_options: object) -> dict[str, Any] | None:
        return {"intent": "delete_everything"}

    monkeypatch.setattr(LLMService, "is_configured", property(lambda _self: True))
    monkeypatch.setattr(LLMService, "complete_json", answer)

    assert asyncio.run(AssistantService().understand("Combien de sites ?")).intent == AssistantIntent.COUNT


def test_the_assistant_is_off_with_the_module(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get(_API, headers=auth_headers).status_code == 404


@pytest.mark.usefixtures("site_care_module_switched_on")
class TestAnswers:
    def test_the_home_offers_its_questions(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        home = client.get(_API, headers=auth_headers).json()

        assert [suggestion["tone"] for suggestion in home["suggestions"]] == ["red", "violet", "green", "amber"]

    def test_a_search_keeps_the_sites_of_its_kind(
        self, client: TestClient, auth_headers: dict[str, str], db: Session, owner: User
    ) -> None:
        _site(db, owner, host="pirate.test", kinds=(IssueKind.HACK, IssueKind.MAIL))
        _site(db, owner, host="mails.test", kinds=(IssueKind.MAIL,))

        answer = client.post(
            f"{_API}/questions", headers=auth_headers, json={"question": "Les sites piratés à contacter"}
        ).json()

        assert [card["domain"] for card in answer["cards"]] == ["pirate.test"]
        assert answer["text"] == "1 site à contacter avec le souci « Site piraté »."

    def test_a_name_the_tab_does_not_hold_is_looked_for_among_every_site(self, db: Session, owner: User) -> None:
        _site(db, owner, host="ecrit.test", kinds=(IssueKind.MAIL,), written_at=CHECK_DAY)

        answer = AssistantService().respond(
            db, owner.id, AssistantRequest(intent=AssistantIntent.SEARCH, place="ecrit.test")
        )

        assert [card.domain for card in answer.cards] == ["ecrit.test"]
        assert answer.text == "1 site en tout pour « ecrit.test »."

    def test_a_count_draws_the_kinds_largest_first(
        self, client: TestClient, auth_headers: dict[str, str], db: Session, owner: User
    ) -> None:
        _site(db, owner, host="pirate.test", kinds=(IssueKind.HACK, IssueKind.MAIL))
        _site(db, owner, host="mails.test", kinds=(IssueKind.MAIL,))

        answer = client.post(
            f"{_API}/questions", headers=auth_headers, json={"question": "Combien de sites par type de souci ?"}
        ).json()

        assert answer["chart"]["bars"] == [{"label": "E-mails", "value": 2}, {"label": "Site piraté", "value": 1}]
        assert answer["text"] == "2 sites contrôlés. Le souci le plus fréquent : e-mails, sur 2 sites."

    def test_the_replies_put_the_last_reply_first(
        self, client: TestClient, auth_headers: dict[str, str], db: Session, owner: User
    ) -> None:
        _site(db, owner, host="ouvert.test", kinds=(IssueKind.MAIL,), written_at=CHECK_DAY, page_opened_at=CHECK_DAY)
        replied = _site(db, owner, host="repondu.test", kinds=(IssueKind.MAIL,), written_at=CHECK_DAY)
        log = EmailLog(
            user_id=owner.id,
            recipient_email="contact@repondu.test",
            subject="Votre site",
            body_html="",
            provider="resend",
            replied_at=CHECK_DAY,
        )
        db.add(log)
        db.flush()
        replied.last_email_log_id = log.id
        db.commit()

        answer = client.post(
            f"{_API}/questions", headers=auth_headers, json={"question": "Qui m’a répondu ou a ouvert sa page ?"}
        ).json()

        assert answer["text"] == "2 sites contactés : 1 réponse, 1 page ouverte."
        assert (answer["highlight"]["title"], answer["highlight"]["badge"]) == ("Entreprise repondu.test", "Réponse")
        assert answer["highlight"]["link_to"] == f"/dashboard/site-care/sites/{replied.id}"

    def test_the_replies_say_so_when_nothing_was_written(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        answer = client.post(f"{_API}/questions", headers=auth_headers, json={"question": "Qui m’a répondu ?"}).json()

        assert answer["text"] == "Vous n’avez encore écrit à aucun site."
