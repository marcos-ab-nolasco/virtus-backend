"""Onboarding API endpoints.

Provides status, module start, and skip endpoints for the onboarding flow.
The actual onboarding conversation happens through the chat endpoint
via AgentRouter delegation.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user
from src.db.models.user import User
from src.db.session import get_db
from src.schemas.onboarding import (
    ModuleProgress,
    OnboardingSkipResponse,
    OnboardingStatusResponse,
    StartModuleResponse,
)
from src.services import onboarding as onboarding_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Get the current onboarding status, progress, and module list."""
    state = await onboarding_service.get_onboarding_state(db, current_user.id)
    modules_data = await onboarding_service.get_module_progress(db, current_user.id)

    modules = [
        ModuleProgress(
            phase=m["phase"],
            status=m["status"],
            started_at=datetime.fromisoformat(m["started_at"]) if m.get("started_at") else None,
            completed_at=(
                datetime.fromisoformat(m["completed_at"]) if m.get("completed_at") else None
            ),
        )
        for m in modules_data
    ]

    return OnboardingStatusResponse(
        status=state["status"],
        current_step=state["current_step"],
        progress_percent=state["progress_percent"],
        started_at=datetime.fromisoformat(state["started_at"]) if state["started_at"] else None,
        completed_at=(
            datetime.fromisoformat(state["completed_at"]) if state["completed_at"] else None
        ),
        modules=modules,
    )


@router.post("/modules/{module_index}/start", response_model=StartModuleResponse)
async def start_module(
    module_index: Annotated[int, Path(ge=0, le=4, description="Module index (0-4)")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> StartModuleResponse:
    """Start or resume an onboarding module conversation.

    If the module is completed (revisiting), creates a new enrichment conversation.
    Returns the conversation_id to use for the module chat.
    """
    try:
        result = await onboarding_service.start_module(db, current_user.id, module_index)

        modules = [
            ModuleProgress(
                phase=m["phase"],
                status=m["status"],
                started_at=(
                    datetime.fromisoformat(m["started_at"]) if m.get("started_at") else None
                ),
                completed_at=(
                    datetime.fromisoformat(m["completed_at"]) if m.get("completed_at") else None
                ),
            )
            for m in result["modules"]
        ]

        return StartModuleResponse(
            conversation_id=result["conversation_id"],
            module_status=result["module_status"],
            is_enrichment=result["is_enrichment"],
            modules=modules,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/skip", response_model=OnboardingSkipResponse)
async def skip_onboarding(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> OnboardingSkipResponse:
    """Skip onboarding and mark as completed."""
    try:
        profile = await onboarding_service.skip_onboarding(db, current_user.id)

        return OnboardingSkipResponse(
            status=profile.onboarding_status.value,
            completed_at=profile.onboarding_completed_at or datetime.now(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e
