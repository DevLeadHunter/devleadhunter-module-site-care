"""The assistant: what it offers before the first question, and its answers."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from schemas.module_assistant import AssistantHome, AssistantQuestion
from services.auth_service import get_current_active_user

from devleadhunter_site_care.schemas.assistant import SiteCareAssistantAnswer
from devleadhunter_site_care.services.assistant_service import AssistantRequest, assistant_service

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
    """Answer a question from the owner's own sites."""
    user_id: int = current_user.id
    # The connection goes back to the pool while the language model reads the question.
    db.commit()
    request: AssistantRequest = await assistant_service.understand(body.question.strip())
    return assistant_service.respond(db, user_id, request)
