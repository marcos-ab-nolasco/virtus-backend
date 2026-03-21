"""
GetObservedPatterns Tool

Returns the user's inferred behavioral patterns from UserProfile.observed_patterns (JSONB).
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.db.models.user_profile import UserProfile
from src.db.session import get_async_sessionmaker
from src.tools.base import BaseTool, ToolResult


class GetObservedPatternsTool(BaseTool):
    """
    Tool that returns inferred behavioral patterns for a user.

    Parameters:
        user_id: UUID of the user

    Returns:
        List of {pattern_type, description, confidence, evidence_count}.
        Returns empty list if no patterns have been inferred yet.
    """

    name = "get_observed_patterns"
    description = (
        "Get inferred behavioral patterns for a user. "
        "Each pattern has pattern_type, description, confidence, and evidence_count. "
        "Returns an empty list if no patterns have been observed yet."
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
                result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
                profile = result.scalar_one_or_none()

                if profile is None or profile.observed_patterns is None:
                    return ToolResult(success=True, data=[], error=None)

                return ToolResult(success=True, data=profile.observed_patterns, error=None)

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Failed to get observed patterns: {type(e).__name__}: {str(e)}",
            )
