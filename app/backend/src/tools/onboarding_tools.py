"""Onboarding tools for the OnboardingAgent.

Provides tools to save user profile data, preferences, and advance onboarding steps.
These tools are invoked by the OnboardingAgent during the onboarding conversation.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SaveUserProfileTool(BaseTool):
    """Save user profile data during onboarding."""

    name = "save_user_profile"
    description = (
        "Save user profile information such as preferred_name and onboarding_data. "
        "Use this to persist data extracted from the user's responses."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's ID"},
            "preferred_name": {
                "type": "string",
                "description": "The name the user prefers to be called",
            },
            "onboarding_data": {
                "type": "object",
                "description": "Additional onboarding data to merge (e.g. work_context, initial_state)",
            },
        },
        "required": ["user_id"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        """Save profile data for the user."""
        try:
            from uuid import UUID

            from sqlalchemy import select

            from src.db.models.user_profile import UserProfile

            user_id = UUID(args["user_id"])

            result = await self._db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                return ToolResult(success=False, error="User profile not found")

            if "preferred_name" in args and args["preferred_name"]:
                profile.preferred_name = args["preferred_name"]

            if "onboarding_data" in args and args["onboarding_data"]:
                current_data = dict(profile.onboarding_data or {})
                current_data.update(args["onboarding_data"])
                profile.onboarding_data = current_data

            await self._db.commit()
            await self._db.refresh(profile)

            logger.info(f"Saved profile data for user {user_id}")
            return ToolResult(success=True, data={"saved": True})

        except Exception as e:
            logger.error(f"Error saving user profile: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class SaveUserPreferencesTool(BaseTool):
    """Save user preferences during onboarding."""

    name = "save_user_preferences"
    description = (
        "Save user preferences such as contact_frequency and timezone. "
        "Use this to persist preference data from the onboarding conversation."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's ID"},
            "contact_frequency": {
                "type": "string",
                "enum": ["RARELY", "SOMETIMES", "FREQUENTLY"],
                "description": "How often the user wants to be contacted",
            },
            "timezone": {
                "type": "string",
                "description": "User's timezone (e.g. America/Sao_Paulo)",
            },
        },
        "required": ["user_id"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        """Save preferences for the user."""
        try:
            from uuid import UUID

            from sqlalchemy import select

            from src.db.models.user_preferences import ContactFrequency, UserPreferences

            user_id = UUID(args["user_id"])

            result = await self._db.execute(
                select(UserPreferences).where(UserPreferences.user_id == user_id)
            )
            preferences = result.scalar_one_or_none()

            if not preferences:
                return ToolResult(success=False, error="User preferences not found")

            if "contact_frequency" in args and args["contact_frequency"]:
                try:
                    preferences.contact_frequency = ContactFrequency(args["contact_frequency"])
                except ValueError:
                    return ToolResult(
                        success=False,
                        error=f"Invalid contact_frequency: {args['contact_frequency']}",
                    )

            if "timezone" in args and args["timezone"]:
                preferences.timezone = args["timezone"]

            await self._db.commit()
            await self._db.refresh(preferences)

            logger.info(f"Saved preferences for user {user_id}")
            return ToolResult(success=True, data={"saved": True})

        except Exception as e:
            logger.error(f"Error saving user preferences: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class CompleteOnboardingStepTool(BaseTool):
    """Advance the onboarding to the next step."""

    name = "complete_onboarding_step"
    description = (
        "Mark the current onboarding step as complete and advance to the next step. "
        "Call this after collecting the required data for the current step."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's ID"},
            "step": {
                "type": "string",
                "description": "The step being completed (e.g. 'intro', 'name', 'frequency')",
            },
        },
        "required": ["user_id", "step"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        """Advance the onboarding step."""
        try:
            from uuid import UUID

            from src.services.onboarding import advance_step, start_onboarding

            user_id = UUID(args["user_id"])
            step = args.get("step", "")

            # Ensure onboarding is started
            from sqlalchemy import select

            from src.db.models.user_profile import OnboardingStatus, UserProfile

            result = await self._db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                return ToolResult(success=False, error="User profile not found")

            # Auto-start onboarding if not started
            if profile.onboarding_status == OnboardingStatus.NOT_STARTED:
                await start_onboarding(self._db, user_id)

            profile = await advance_step(self._db, user_id)

            logger.info(
                f"Completed onboarding step '{step}' for user {user_id}, "
                f"now at: {profile.onboarding_current_step}, "
                f"status: {profile.onboarding_status.value}"
            )

            return ToolResult(
                success=True,
                data={
                    "completed_step": step,
                    "current_step": profile.onboarding_current_step,
                    "status": profile.onboarding_status.value,
                },
            )

        except Exception as e:
            logger.error(f"Error completing onboarding step: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))
