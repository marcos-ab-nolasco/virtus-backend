"""
GetInferredValues Tool

Returns the user's values and moral profile from OnboardingInsight and UserProfile.
Useful for decision support and deep reflection sessions.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.db.models.planning import OnboardingInsight
from src.db.models.user_profile import UserProfile
from src.db.session import get_async_sessionmaker
from src.tools.base import BaseTool, ToolResult


class GetInferredValuesTool(BaseTool):
    """
    Tool that returns values and moral profile for a user.

    Parameters:
        user_id: UUID of the user

    Returns:
        Dict with top_values, value_behavior_gap, and moral_profile.
        Returns empty top_values if OnboardingInsight does not exist yet.
    """

    name = "get_inferred_values"
    description = (
        "Get the user's declared values and moral profile. "
        "Includes top personal values, any identified gap between values and behavior, "
        "and a moral foundations profile (care, fairness, liberty, etc.). "
        "Returns empty top_values if the user hasn't completed the values module."
    )
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

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            user_id_str = args.get("user_id")
            if not user_id_str:
                return ToolResult(success=False, data=None, error="Missing required field: user_id")

            try:
                user_id = UUID(user_id_str)
            except (ValueError, TypeError):
                return ToolResult(
                    success=False, data=None, error=f"Invalid UUID format: {user_id_str}"
                )

            session_factory = get_async_sessionmaker()
            async with session_factory() as db:
                insight_result = await db.execute(
                    select(OnboardingInsight).where(OnboardingInsight.user_id == user_id)
                )
                insight = insight_result.scalar_one_or_none()

                profile_result = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == user_id)
                )
                profile = profile_result.scalar_one_or_none()

            top_values: list[str] = []
            value_behavior_gap: str | None = None
            if insight:
                top_values = insight.top_values or []
                value_behavior_gap = insight.value_behavior_gap

            moral_profile: dict[str, Any] | None = None
            if profile and profile.moral_profile is not None:
                moral_profile = profile.moral_profile

            return ToolResult(
                success=True,
                data={
                    "top_values": top_values,
                    "value_behavior_gap": value_behavior_gap,
                    "moral_profile": moral_profile,
                },
                error=None,
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Failed to get inferred values: {type(e).__name__}: {str(e)}",
            )
