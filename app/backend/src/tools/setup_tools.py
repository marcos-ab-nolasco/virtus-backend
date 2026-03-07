"""Setup tools for the SetupAgent.

Provides tools to save user profile data, preferences, and complete the setup phase.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

ONBOARDING_PHASES = ["phase_1", "phase_2", "phase_3", "phase_4", "phase_5"]


class SaveUserProfileTool(BaseTool):
    """Save user profile data (preferred_name) during setup."""

    name = "save_user_profile"
    description = (
        "Save user profile information such as preferred_name. "
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
        },
        "required": ["user_id"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
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

            await self._db.commit()
            await self._db.refresh(profile)

            logger.info(f"Saved profile data for user {user_id}")
            return ToolResult(success=True, data={"saved": True})

        except Exception as e:
            logger.error(f"Error saving user profile: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class SaveUserPreferencesTool(BaseTool):
    """Save user preferences (timezone, contact_frequency) during setup."""

    name = "save_user_preferences"
    description = (
        "Save user preferences such as contact_frequency and timezone. "
        "Use this to persist preference data from the setup conversation."
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
        try:
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


class CompleteSetupTool(BaseTool):
    """Complete the setup phase and initialize module structure."""

    name = "complete_setup"
    description = (
        "Mark the setup as complete, initialize the 5 onboarding modules, "
        "and signal whether the user wants to explore the dashboard or deepen into modules."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's UUID"},
            "next_action": {
                "type": "string",
                "enum": ["explore", "deepen"],
                "description": (
                    "What the user wants to do next: "
                    "'explore' = go to dashboard, 'deepen' = start a module right away"
                ),
            },
        },
        "required": ["user_id", "next_action"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            from src.db.models.user_profile import OnboardingStatus
            from src.services.onboarding import complete_setup

            user_id = UUID(args["user_id"])
            next_action = args.get("next_action", "explore")

            await complete_setup(self._db, user_id)

            logger.info(f"Setup completed for user {user_id}, next_action={next_action}")

            return ToolResult(
                success=True,
                data={
                    "status": OnboardingStatus.SETUP_COMPLETED,
                    "next_action": next_action,
                },
            )

        except Exception as e:
            logger.error(f"Error completing setup: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))
