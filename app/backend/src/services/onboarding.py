"""Onboarding service layer for business logic.

Handles setup phase (name/timezone/frequency) and module-based deep onboarding.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.conversation import Conversation, ConversationContext
from src.db.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier
from src.db.models.user_profile import OnboardingStatus, UserProfile

# Deep onboarding phase sequence
ONBOARDING_PHASES = ["phase_1", "phase_2", "phase_3", "phase_4", "phase_5"]

# Phase to progress percentage mapping
PHASE_PROGRESS = {
    "phase_1": 0,
    "phase_2": 20,
    "phase_3": 40,
    "phase_4": 60,
    "phase_5": 80,
}


async def _get_user_profile(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Get user profile by user_id.

    Raises:
        HTTPException: 404 if profile not found
    """
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    return profile


async def get_onboarding_state(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
    """Get the current onboarding state for a user."""
    profile = await _get_user_profile(db, user_id)

    progress = 0
    current = profile.onboarding_current_step
    if profile.onboarding_status == OnboardingStatus.COMPLETED:
        progress = 100
    elif profile.onboarding_status == OnboardingStatus.SETUP_COMPLETED:
        # Calculate based on modules completed
        data = profile.onboarding_data or {}
        modules = data.get("modules", {})
        completed = sum(1 for m in modules.values() if m.get("status") == "completed")
        progress = completed * 20  # 5 modules × 20%
    elif current and current.startswith("phase_"):
        progress = PHASE_PROGRESS.get(current, 0)

    return {
        "status": profile.onboarding_status.value,
        "current_step": profile.onboarding_current_step,
        "progress_percent": progress,
        "started_at": (
            profile.onboarding_started_at.isoformat() if profile.onboarding_started_at else None
        ),
        "completed_at": (
            profile.onboarding_completed_at.isoformat() if profile.onboarding_completed_at else None
        ),
        "data": profile.onboarding_data or {},
    }


async def _activate_trial_if_free(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Activate 14-day trial if user is on FREE tier. Idempotent."""
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    subscription = result.scalar_one_or_none()
    if subscription and subscription.tier == SubscriptionTier.FREE:
        subscription.tier = SubscriptionTier.TRIAL
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.trial_ends_at = datetime.now(UTC) + timedelta(days=14)


async def complete_onboarding(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Mark onboarding as completed and activate trial subscription."""
    profile = await _get_user_profile(db, user_id)

    profile.onboarding_status = OnboardingStatus.COMPLETED
    profile.onboarding_completed_at = datetime.now(UTC)

    await _activate_trial_if_free(db, user_id)

    await db.commit()
    await db.refresh(profile)

    return profile


async def reset_onboarding(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Reset onboarding state to NOT_STARTED."""
    profile = await _get_user_profile(db, user_id)

    profile.onboarding_status = OnboardingStatus.NOT_STARTED
    profile.onboarding_started_at = None
    profile.onboarding_current_step = None
    profile.onboarding_data = None
    profile.onboarding_completed_at = None

    await db.commit()
    await db.refresh(profile)

    return profile


async def start_deep_onboarding(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Start the deep onboarding phase flow for a user (sets phase_1 as current step).

    Used as a fallback when OnboardingAgent processes a conversation for a user
    who has not yet reached SETUP_COMPLETED.
    """
    profile = await _get_user_profile(db, user_id)

    if profile.onboarding_status == OnboardingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed for this user",
        )

    profile.onboarding_status = OnboardingStatus.IN_PROGRESS
    profile.onboarding_started_at = datetime.now(UTC)
    profile.onboarding_current_step = "phase_1"
    profile.onboarding_data = {}

    await db.commit()
    await db.refresh(profile)

    return profile


async def advance_phase(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Advance to the next deep onboarding phase.

    If at phase_5, triggers complete_onboarding() which activates the trial.
    """
    profile = await _get_user_profile(db, user_id)

    current_phase = profile.onboarding_current_step

    if current_phase is None or current_phase not in ONBOARDING_PHASES:
        profile.onboarding_current_step = ONBOARDING_PHASES[0]
    elif current_phase == "phase_5":
        return await complete_onboarding(db, user_id)
    else:
        current_index = ONBOARDING_PHASES.index(current_phase)
        next_index = current_index + 1
        if next_index < len(ONBOARDING_PHASES):
            profile.onboarding_current_step = ONBOARDING_PHASES[next_index]
        else:
            return await complete_onboarding(db, user_id)

    await db.commit()
    await db.refresh(profile)

    return profile


async def mark_structured_submitted(
    db: AsyncSession, user_id: uuid.UUID, submission_type: str
) -> None:
    """Set a flag in onboarding_data to track which structured inputs were submitted."""
    flag_map = {
        "slider_grid": "life_areas_submitted",
        "chip_selector_values": "values_submitted",
        "chip_selector_obstacles": "obstacle_submitted",
    }
    flag = flag_map.get(submission_type)
    if not flag:
        return

    profile = await _get_user_profile(db, user_id)
    data = dict(profile.onboarding_data or {})
    data[flag] = True
    profile.onboarding_data = data
    await db.commit()


async def skip_onboarding(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Skip onboarding and mark as completed."""
    profile = await _get_user_profile(db, user_id)

    if profile.onboarding_status == OnboardingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed for this user",
        )

    profile.onboarding_status = OnboardingStatus.COMPLETED
    profile.onboarding_completed_at = datetime.now(UTC)

    await _activate_trial_if_free(db, user_id)

    await db.commit()
    await db.refresh(profile)

    return profile


# ---------------------------------------------------------------------------
# Module-based onboarding functions (progressive model)
# ---------------------------------------------------------------------------


def _ensure_module_structure(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure onboarding_data has the modules dict with all 5 phases initialised."""
    result = dict(data)
    if "modules" not in result or not isinstance(result["modules"], dict):
        result["modules"] = {}

    for phase in ONBOARDING_PHASES:
        if phase not in result["modules"]:
            result["modules"][phase] = {"status": "not_started"}

    return result


async def complete_setup(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Mark setup as complete and initialise 5 onboarding modules.

    Transitions status: NOT_STARTED / IN_PROGRESS → SETUP_COMPLETED.
    Idempotent if already SETUP_COMPLETED or COMPLETED.
    """
    profile = await _get_user_profile(db, user_id)

    if profile.onboarding_status not in (
        OnboardingStatus.NOT_STARTED,
        OnboardingStatus.IN_PROGRESS,
    ):
        return profile

    data = _ensure_module_structure(dict(profile.onboarding_data or {}))

    profile.onboarding_status = OnboardingStatus.SETUP_COMPLETED
    profile.onboarding_started_at = profile.onboarding_started_at or datetime.now(UTC)
    profile.onboarding_data = data

    await db.commit()
    await db.refresh(profile)

    return profile


async def update_module_status(
    db: AsyncSession, user_id: uuid.UUID, phase: str, new_status: str
) -> UserProfile:
    """Update the status of a single onboarding module in the JSONB field."""
    if phase not in ONBOARDING_PHASES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid phase: {phase}",
        )

    profile = await _get_user_profile(db, user_id)
    data = _ensure_module_structure(dict(profile.onboarding_data or {}))

    now_iso = datetime.now(UTC).isoformat()
    module = dict(data["modules"].get(phase, {"status": "not_started"}))
    module["status"] = new_status

    if new_status == "in_progress" and "started_at" not in module:
        module["started_at"] = now_iso
    elif new_status == "completed":
        module["completed_at"] = now_iso

    modules = dict(data["modules"])
    modules[phase] = module
    data["modules"] = modules
    profile.onboarding_data = data

    await db.commit()
    await db.refresh(profile)

    return profile


async def get_module_progress(db: AsyncSession, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return progress for all 5 modules.

    Always returns 5 entries — not_started if no data exists yet.
    """
    profile = await _get_user_profile(db, user_id)
    data = profile.onboarding_data or {}
    modules = data.get("modules", {})

    result = []
    for phase in ONBOARDING_PHASES:
        mod = modules.get(phase, {"status": "not_started"})
        result.append(
            {
                "phase": phase,
                "status": mod.get("status", "not_started"),
                "started_at": mod.get("started_at"),
                "completed_at": mod.get("completed_at"),
            }
        )

    return result


async def start_module(db: AsyncSession, user_id: uuid.UUID, phase_index: int) -> dict[str, Any]:
    """Start or resume an onboarding module conversation.

    - not_started / in_progress: finds/creates conversation, marks in_progress.
    - completed (revisit): creates a new enrichment conversation.

    Returns:
        Dict with conversation_id, module_status, is_enrichment, modules
    """
    if phase_index < 0 or phase_index >= len(ONBOARDING_PHASES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid module index: {phase_index}. Must be 0-4.",
        )

    phase = ONBOARDING_PHASES[phase_index]
    profile = await _get_user_profile(db, user_id)
    data = _ensure_module_structure(dict(profile.onboarding_data or {}))
    module = data["modules"].get(phase, {"status": "not_started"})
    current_status = module.get("status", "not_started")

    is_enrichment = current_status == "completed"
    phase_num = phase_index + 1
    conversation_title = f"Onboarding: Módulo {phase_num}"

    if is_enrichment:
        conv = Conversation(
            user_id=user_id,
            title=f"{conversation_title} (enriquecimento)",
            ai_provider="openai",
            ai_model="gpt-4",
            context_type=ConversationContext.ONBOARDING_MODULE,
        )
        db.add(conv)
        await db.flush()
        conversation_id = str(conv.id)
    else:
        result = await db.execute(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.title == conversation_title,
                Conversation.context_type == ConversationContext.ONBOARDING_MODULE,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            conversation_id = str(existing.id)
        else:
            conv = Conversation(
                user_id=user_id,
                title=conversation_title,
                ai_provider="openai",
                ai_model="gpt-4",
                context_type=ConversationContext.ONBOARDING_MODULE,
            )
            db.add(conv)
            await db.flush()
            conversation_id = str(conv.id)

        if current_status == "not_started":
            now_iso = datetime.now(UTC).isoformat()
            modules = dict(data["modules"])
            modules[phase] = {"status": "in_progress", "started_at": now_iso}
            data["modules"] = modules
            profile.onboarding_data = data

    await db.commit()
    await db.refresh(profile)

    modules_progress = await get_module_progress(db, user_id)

    return {
        "conversation_id": conversation_id,
        "module_status": "in_progress" if not is_enrichment else "completed",
        "is_enrichment": is_enrichment,
        "modules": modules_progress,
    }


async def complete_module(db: AsyncSession, user_id: uuid.UUID, phase: str) -> UserProfile:
    """Mark an onboarding module as completed.

    If all 5 modules are completed, transitions status to COMPLETED
    and activates the trial subscription.
    """
    profile = await update_module_status(db, user_id, phase, "completed")

    data = profile.onboarding_data or {}
    modules = data.get("modules", {})
    all_done = all(modules.get(p, {}).get("status") == "completed" for p in ONBOARDING_PHASES)

    if all_done and profile.onboarding_status != OnboardingStatus.COMPLETED:
        profile.onboarding_status = OnboardingStatus.COMPLETED
        profile.onboarding_completed_at = datetime.now(UTC)
        await _activate_trial_if_free(db, user_id)
        await db.commit()
        await db.refresh(profile)

    return profile
