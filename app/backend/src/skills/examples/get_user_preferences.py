"""
GetUserPreferences Skill

Retrieves the preferences for a specific user.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user_preferences import UserPreferences
from src.db.session import get_async_sessionmaker
from src.skills.base import BaseSkill, SkillResult


class GetUserPreferencesSkill(BaseSkill):
    """
    Skill that retrieves user preferences

    Parameters:
        user_id: UUID of the user

    Returns:
        User preferences information
    """

    name = "get_user_preferences"
    description = "Get the preferences for a specific user including timezone, language, communication style, and check-in settings"
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "UUID of the user",
            },
        },
        "required": ["user_id"],
    }

    async def execute(self, args: dict[str, Any]) -> SkillResult:
        """
        Execute the skill to get user preferences

        Args:
            args: Dictionary with "user_id" key

        Returns:
            SkillResult with user preferences data
        """
        try:
            # Extract user_id
            user_id_str = args.get("user_id")
            if not user_id_str:
                return SkillResult(
                    success=False, data=None, error="Missing required field: user_id"
                )

            try:
                user_id = UUID(user_id_str)
            except (ValueError, TypeError):
                return SkillResult(
                    success=False, data=None, error=f"Invalid UUID format: {user_id_str}"
                )

            # Query user preferences
            session_factory = get_async_sessionmaker()
            async with session_factory() as db:
                stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
                result = await db.execute(stmt)
                prefs = result.scalar_one_or_none()

                if prefs is None:
                    return SkillResult(
                        success=False,
                        data=None,
                        error=f"User preferences not found for user_id: {user_id}",
                    )

                # Serialize preferences
                prefs_data = {
                    "user_id": str(prefs.user_id),
                    "timezone": prefs.timezone,
                    "language": prefs.language,
                    "communication_style": prefs.communication_style.value if prefs.communication_style else None,
                    "morning_checkin_time": prefs.morning_checkin_time.strftime("%H:%M") if prefs.morning_checkin_time else None,
                    "evening_checkin_time": prefs.evening_checkin_time.strftime("%H:%M") if prefs.evening_checkin_time else None,
                    "weekly_review_day": prefs.weekly_review_day.value if prefs.weekly_review_day else None,
                    "week_start_day": prefs.week_start_day.value if prefs.week_start_day else None,
                    "coach_name": prefs.coach_name,
                }

                return SkillResult(success=True, data=prefs_data, error=None)

        except Exception as e:
            return SkillResult(
                success=False,
                data=None,
                error=f"Failed to get user preferences: {type(e).__name__}: {str(e)}",
            )
