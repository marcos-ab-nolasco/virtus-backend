"""
GetUserFullHistory Tool

Returns a consolidated view of the user's journey:
life area scores, deep onboarding insights, annual goals, strengths, and interests.
Tolerant: returns partial data if the user hasn't completed all onboarding modules.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.db.models.planning import AnnualGoal, LifeAreaScore, OnboardingInsight
from src.db.models.user_profile import UserProfile
from src.db.session import get_async_sessionmaker
from src.tools.base import BaseTool, ToolResult


class GetUserFullHistoryTool(BaseTool):
    """
    Tool that returns a consolidated view of the user's journey.

    Parameters:
        user_id: UUID of the user

    Returns:
        Structured dict with life_areas, insights, annual_goals, strengths, interests.
    """

    name = "get_user_full_history"
    description = (
        "Get a consolidated view of the user's journey including life area scores, "
        "deep onboarding insights (Ikigai, ACT values, Future Self, WOOP), annual goals, "
        "strengths, and interests. Returns partial data if onboarding is incomplete."
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
                # Life area scores
                scores_result = await db.execute(
                    select(LifeAreaScore).where(LifeAreaScore.user_id == user_id)
                )
                scores = scores_result.scalars().all()
                life_areas = [
                    {
                        "area": s.area,
                        "current": s.current_score,
                        "desired": s.desired_score,
                        "is_priority": s.is_priority,
                    }
                    for s in scores
                ]

                # Onboarding insights
                insight_result = await db.execute(
                    select(OnboardingInsight).where(OnboardingInsight.user_id == user_id)
                )
                insight = insight_result.scalar_one_or_none()
                insights: dict[str, Any] = {}
                if insight:
                    insights = {
                        "top_values": insight.top_values or [],
                        "value_behavior_gap": insight.value_behavior_gap,
                        "future_self": insight.future_self_description,
                        "milestone_6months": insight.milestone_6months,
                        "milestone_3months": insight.milestone_3months,
                        "first_step": insight.first_step,
                        "energizing_activities": insight.energizing_activities or [],
                        "recognized_skills": insight.recognized_skills or [],
                        "best_outcome": insight.best_outcome,
                    }

                # Annual goals
                goals_result = await db.execute(
                    select(AnnualGoal)
                    .where(AnnualGoal.user_id == user_id)
                    .order_by(AnnualGoal.priority)
                )
                goals = goals_result.scalars().all()
                annual_goals = [
                    {
                        "title": g.title,
                        "life_area": g.life_area,
                        "priority": g.priority,
                        "status": g.status,
                        "target_year": g.target_year,
                    }
                    for g in goals
                ]

                # Profile: strengths and interests
                profile_result = await db.execute(
                    select(UserProfile).where(UserProfile.user_id == user_id)
                )
                profile = profile_result.scalar_one_or_none()
                raw_strengths: Any = profile.strengths if profile else None
                raw_interests: Any = profile.interests if profile else None
                strengths: list[Any] = raw_strengths or []
                interests: list[Any] = raw_interests or []

            return ToolResult(
                success=True,
                data={
                    "life_areas": life_areas,
                    "insights": insights,
                    "annual_goals": annual_goals,
                    "strengths": strengths,
                    "interests": interests,
                },
                error=None,
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Failed to get user full history: {type(e).__name__}: {str(e)}",
            )
