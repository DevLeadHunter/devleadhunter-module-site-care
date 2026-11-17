"""The assistant: what it offers before the first question, and its answers."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.database import get_db
from models.user import User
from schemas.module_assistant import AssistantHome, AssistantQuestion
from services.auth_service import get_current_active_user

from devleadhunter_site_care.schemas.assistant import SiteCareAssistantAnswer
from devleadhunter_site_care.services.assistant_service import assistant_service

router = APIRouter(prefix="/site-care/assistant", tags=["site-care-assistant"])


@router.get("", response_model=AssistantHome)
async def get_home(_current_user: User = Depends(get_current_active_user)) -> AssistantHome:
    """The sentence under the title and the questions offered."""
    return assistant_service.HOME


@router.post("/questions", response_model=SiteCareAssistantAnswer)
async def ask(
    body: AssistantQuestion,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SiteCareAssistantAnswer:
    """Answer a question of the conversation from the owner's own sites."""
    return await assistant_service.answer(db, current_user.id, body.question.strip(), body.history, naive_utc_now())
