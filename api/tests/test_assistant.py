"""The assistant: a conversation the language model holds with tools, or one tool picked by the words alone."""

from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import CHECK_DAY
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.email_log import EmailLog
from models.user import User
from services.module_assistant_engine import (
    AssistantTool,
    AssistantToolArguments,
    AssistantToolResult,
    ModuleAssistantEngine,
)

from devleadhunter_site_care.catalog import IssueKind, SiteStatus
from devleadhunter_site_care.models.care_plan import SiteCarePlan
from devleadhunter_site_care.models.site import SiteCareSite
from devleadhunter_site_care.schemas.site import SiteListItem
from devleadhunter_site_care.services.assistant_service import AssistantService
from devleadhunter_site_care.services.site_service import SiteService

_API: str = "/api/v1/site-care/assistant"


@pytest.fixture(autouse=True)
def language_model_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """The language model is off: the words of a question alone pick the tool."""
    monkeypatch.setattr(ModuleAssistantEngine, "is_available", property(lambda _self: False))


def _site(
    db: Session,
    owner: User,
    *,
    host: str,
    kinds: tuple[IssueKind, ...],
    city: str = "Rennes",
    written_at: datetime | None = None,
    page_opened_at: datetime | None = None,
) -> SiteCareSite:
    """A site to write to, with its kinds of issue."""
    site = SiteCareSite(
        user_id=owner.id,
        business_name=f"Entreprise {host}",
        trade="paysagiste",
        city=city,
        website=f"https://{host}",
        host=host,
        email=f"contact@{host}",
        status=SiteStatus.TO_WRITE.value,
        kinds_filter="," + ",".join(kind.value for kind in kinds) + ",",
        search_text=SiteService.search_text_of(f"Entreprise {host}", city, host),
        checked_at=CHECK_DAY,
        page_slug=host,
        written_at=written_at,
        page_opened_at=page_opened_at,
    )
    db.add(site)
    db.commit()
    return site


def _claude_saying(monkeypatch: pytest.MonkeyPatch, replies: list[SimpleNamespace]) -> list[dict[str, Any]]:
    """Make Claude give these messages in order; each request is returned as it left."""
    received: list[dict[str, Any]] = []

    async def create_message(
        _self: ModuleAssistantEngine, *, messages: list[dict[str, Any]], **request: object
    ) -> SimpleNamespace:
        received.append({**request, "messages": list(messages)})
        return replies[len(received) - 1]

    monkeypatch.setattr(ModuleAssistantEngine, "is_available", property(lambda _self: True))
    monkeypatch.setattr(ModuleAssistantEngine, "_create_message", create_message)
    return received


def _tool_call(name: str, arguments: dict[str, Any]) -> SimpleNamespace:
    """A message of Claude that calls one tool."""
    return SimpleNamespace(
        stop_reason="tool_use", content=[SimpleNamespace(type="tool_use", id="call_1", name=name, input=arguments)]
    )


def _final_answer(answer: str, next_questions: list[str]) -> SimpleNamespace:
    """A final message of Claude, in the JSON format the engine asks for."""
    text: str = json.dumps(
        {"answer": answer, "next_questions": next_questions, "needs_no_data": False}, ensure_ascii=False
    )
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


def _run(db: Session, owner: User, tool_name: str, arguments: AssistantToolArguments) -> AssistantToolResult:
    """Run one of the assistant's tools the way the language model calls it."""
    tool: AssistantTool = next(tool for tool in AssistantService().tools(CHECK_DAY) if tool.name == tool_name)
    return tool.run(db, owner.id, arguments)


def test_the_words_alone_tell_the_kind_of_issue_and_the_tab() -> None:
    assert AssistantService.tool_call_of_words("Les sites piratés à contacter") == ("chercher_sites", {"kind": "hack"})
    assert AssistantService.tool_call_of_words("Les sites déjà contactés") == ("chercher_sites", {"tab": "ecrits"})


def test_the_words_alone_tell_a_count_the_replies_and_the_watch() -> None:
    assert AssistantService.tool_call_of_words("Combien de sites par type de souci ?")[0] == "compter_sites"
    assert AssistantService.tool_call_of_words("Qui m’a répondu ou a ouvert sa page ?")[0] == "suivi_sites_contactes"
    assert AssistantService.tool_call_of_words("Quoi de neuf dans la veille ?")[0] == "veille"


def test_a_search_drops_the_arguments_it_does_not_know(db: Session, owner: User) -> None:
    _site(db, owner, host="mails.test", kinds=(IssueKind.MAIL,))

    result = _run(db, owner, "chercher_sites", {"kind": "ok", "text": "x" * 200, "tab": "nothing"})

    assert result.sentence == "1 site à contacter."


def test_a_name_the_tab_does_not_hold_is_looked_for_among_every_site(db: Session, owner: User) -> None:
    _site(db, owner, host="ecrit.test", kinds=(IssueKind.MAIL,), written_at=CHECK_DAY)

    result = _run(db, owner, "chercher_sites", {"text": "ecrit.test"})

    assert [card.domain for card in result.cards if isinstance(card, SiteListItem)] == ["ecrit.test"]
    assert result.sentence == "1 site en tout pour « ecrit.test »."


def test_a_count_by_town_ranks_the_towns(db: Session, owner: User) -> None:
    _site(db, owner, host="a.test", kinds=(IssueKind.MAIL,), city="Rennes")
    _site(db, owner, host="b.test", kinds=(IssueKind.MAIL,), city="Rennes")
    _site(db, owner, host="c.test", kinds=(IssueKind.MAIL,), city="Vitré")

    result = _run(db, owner, "compter_sites", {"group_by": "ville"})

    assert result.chart is not None
    assert [(bar.label, bar.value) for bar in result.chart.bars] == [("Rennes", 2), ("Vitré", 1)]


def test_the_detail_of_a_site_links_to_its_sheet(db: Session, owner: User) -> None:
    site = _site(db, owner, host="mails.test", kinds=(IssueKind.MAIL,))

    result = _run(db, owner, "detail_site", {"text": "mails"})

    assert (result.facts["entreprise"], result.facts["site"]) == ("Entreprise mails.test", "mails.test")
    assert result.highlight is not None and result.highlight.link_to == f"/dashboard/site-care/sites/{site.id}"


def test_the_clients_under_care_are_counted_with_what_they_bring(db: Session, owner: User) -> None:
    site = _site(db, owner, host="client.test", kinds=(IssueKind.MAIL,))
    db.add(SiteCarePlan(user_id=owner.id, site_id=site.id, monthly_price_cents=10000))
    db.commit()

    result = _run(db, owner, "clients_en_suivi", {})

    assert result.sentence == "1 client en suivi, 100 € par mois."


def test_the_watch_says_so_when_nothing_changed(db: Session, owner: User) -> None:
    assert _run(db, owner, "veille", {}).sentence == "Rien de nouveau dans la veille."


def test_the_assistant_is_off_with_the_module(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get(_API, headers=auth_headers).status_code == 404


@pytest.mark.usefixtures("site_care_module_switched_on")
class TestAnswers:
    def test_the_home_offers_its_questions(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        home = client.get(_API, headers=auth_headers).json()

        assert [suggestion["tone"] for suggestion in home["suggestions"]] == ["red", "violet", "green", "amber"]

    def test_the_language_model_chains_the_tools_and_writes_the_answer(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        owner: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _site(db, owner, host="pirate.test", kinds=(IssueKind.HACK,), city="Vitré")
        _site(db, owner, host="mails.test", kinds=(IssueKind.MAIL,))
        received = _claude_saying(
            monkeypatch,
            [
                _tool_call("chercher_sites", {"text": "Vitré"}),
                _final_answer("Un seul site à Vitré, et il est piraté.", ["Ouvrir sa fiche"]),
            ],
        )

        answer = client.post(
            f"{_API}/questions",
            headers=auth_headers,
            json={
                "question": "Et à Vitré ?",
                "history": [{"question": "Les sites à contacter", "answer": "2 sites à contacter."}],
            },
        ).json()

        assert answer["text"] == "Un seul site à Vitré, et il est piraté."
        assert [card["domain"] for card in answer["cards"]] == ["pirate.test"]
        assert answer["next_questions"] == ["Ouvrir sa fiche"]
        assert received[0]["messages"][0]["content"] == "Les sites à contacter"

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

    def test_a_count_draws_the_kinds_largest_first(
        self, client: TestClient, auth_headers: dict[str, str], db: Session, owner: User
    ) -> None:
        _site(db, owner, host="pirate.test", kinds=(IssueKind.HACK, IssueKind.MAIL))
        _site(db, owner, host="mails.test", kinds=(IssueKind.MAIL,))

        answer = client.post(
            f"{_API}/questions", headers=auth_headers, json={"question": "Combien de sites par type de souci ?"}
        ).json()

        assert answer["chart"]["bars"] == [{"label": "E-mails", "value": 2}, {"label": "Site piraté", "value": 1}]
        assert answer["text"] == "2 sites contrôlés. En tête : e-mails, sur 2 sites."

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
