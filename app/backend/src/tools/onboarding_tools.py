"""Onboarding tools for the deep OnboardingAgent.

Provides tools to persist data collected during the 5-phase conversational
onboarding (Wheel of Life, Ikigai, ACT, Future Self, WOOP).
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SaveLifeAreaScoresTool(BaseTool):
    """Upsert Wheel-of-Life scores for one or more life areas."""

    name = "save_life_area_scores"
    description = (
        "Save or update satisfaction scores for life areas collected during Phase 1. "
        "Pass a list of area scores; each entry is upserted by (user_id, area)."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's UUID"},
            "scores": {
                "type": "array",
                "description": "List of area scores to upsert",
                "items": {
                    "type": "object",
                    "properties": {
                        "area": {
                            "type": "string",
                            "description": (
                                "LifeArea value: HEALTH, WORK, RELATIONSHIPS, PERSONAL_TIME, "
                                "FINANCE, PERSONAL_GROWTH, LEISURE, FREEDOM_TIME"
                            ),
                        },
                        "current_score": {
                            "type": "integer",
                            "description": "Current satisfaction (1-10)",
                        },
                        "desired_score": {
                            "type": "integer",
                            "description": "Desired satisfaction (1-10)",
                        },
                        "is_priority": {
                            "type": "boolean",
                            "description": "Whether this area is a top priority",
                        },
                    },
                    "required": ["area", "current_score", "desired_score"],
                },
            },
        },
        "required": ["user_id", "scores"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            from src.db.models.planning import LifeAreaScore

            user_id = UUID(args["user_id"])
            scores: list[dict[str, Any]] = args.get("scores", [])

            if not scores:
                return ToolResult(success=False, error="No scores provided")

            saved = []
            for entry in scores:
                area = entry["area"]

                result = await self._db.execute(
                    select(LifeAreaScore).where(
                        LifeAreaScore.user_id == user_id,
                        LifeAreaScore.area == area,
                    )
                )
                record = result.scalar_one_or_none()

                if record is None:
                    record = LifeAreaScore(
                        user_id=user_id,
                        area=area,
                        current_score=entry["current_score"],
                        desired_score=entry["desired_score"],
                        is_priority=entry.get("is_priority", False),
                    )
                    self._db.add(record)
                else:
                    record.current_score = entry["current_score"]
                    record.desired_score = entry["desired_score"]
                    record.is_priority = entry.get("is_priority", record.is_priority)

                saved.append(area)

            await self._db.commit()
            logger.info(f"Saved life area scores for user {user_id}: {saved}")
            return ToolResult(success=True, data={"saved_areas": saved})

        except Exception as e:
            logger.error(f"Error saving life area scores: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class SaveOnboardingInsightTool(BaseTool):
    """Create or merge OnboardingInsight data for a user."""

    name = "save_onboarding_insight"
    description = (
        "Upsert structured insight data collected during deep onboarding phases 2-4. "
        "Only the fields provided are updated; existing fields are preserved."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's UUID"},
            "energizing_activities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Activities that energize the user (Ikigai: what you love)",
            },
            "recognized_skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Skills others recognize in the user (Ikigai: what you're good at)",
            },
            "market_problems": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Problems in the world the user wants to solve",
            },
            "top_values": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Top 3-5 personal values",
            },
            "value_behavior_gap": {
                "type": "string",
                "description": "Gap between values and current behavior",
            },
            "future_self_description": {
                "type": "string",
                "description": "Description of ideal life in 12 months",
            },
            "milestone_6months": {
                "type": "string",
                "description": "What must be true at 6 months",
            },
            "milestone_3months": {
                "type": "string",
                "description": "What must be true at 3 months",
            },
            "first_step": {
                "type": "string",
                "description": "First concrete step toward the vision",
            },
            "best_outcome": {
                "type": "string",
                "description": "Best imaginable outcome if goals are achieved (WOOP)",
            },
            "internal_obstacle": {
                "type": "string",
                "description": "Main internal obstacle (WOOP)",
            },
            "if_then_plan": {
                "type": "string",
                "description": "Implementation intention: if [obstacle] then [action] (WOOP)",
            },
        },
        "required": ["user_id"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            from src.db.models.planning import OnboardingInsight

            user_id = UUID(args["user_id"])

            result = await self._db.execute(
                select(OnboardingInsight).where(OnboardingInsight.user_id == user_id)
            )
            insight = result.scalar_one_or_none()

            if insight is None:
                insight = OnboardingInsight(user_id=user_id)
                self._db.add(insight)

            # Only update fields that were explicitly provided
            updatable_fields = [
                "energizing_activities",
                "recognized_skills",
                "market_problems",
                "top_values",
                "value_behavior_gap",
                "future_self_description",
                "milestone_6months",
                "milestone_3months",
                "first_step",
                "best_outcome",
                "internal_obstacle",
                "if_then_plan",
            ]
            updated = []
            for field in updatable_fields:
                if field in args and args[field] is not None:
                    setattr(insight, field, args[field])
                    updated.append(field)

            await self._db.commit()
            logger.info(f"Saved onboarding insight for user {user_id}. Updated: {updated}")
            return ToolResult(success=True, data={"updated_fields": updated})

        except Exception as e:
            logger.error(f"Error saving onboarding insight: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class SaveAnnualGoalTool(BaseTool):
    """Create an annual goal linked to a life area."""

    name = "save_annual_goal"
    description = "Save an annual goal for a priority life area. Returns the created goal_id."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's UUID"},
            "title": {"type": "string", "description": "Goal title (concise, max 255 chars)"},
            "life_area": {
                "type": "string",
                "description": (
                    "LifeArea: HEALTH, WORK, RELATIONSHIPS, PERSONAL_TIME, "
                    "FINANCE, PERSONAL_GROWTH, LEISURE, FREEDOM_TIME"
                ),
            },
            "target_year": {
                "type": "integer",
                "description": "The year this goal targets (e.g. 2026)",
            },
            "priority": {
                "type": "integer",
                "description": "Ordering priority (1 = highest)",
                "default": 1,
            },
            "description": {
                "type": "string",
                "description": "Optional longer description",
            },
        },
        "required": ["user_id", "title", "life_area", "target_year"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            from src.db.models.planning import AnnualGoal

            user_id = UUID(args["user_id"])

            goal = AnnualGoal(
                user_id=user_id,
                title=args["title"],
                life_area=args["life_area"],
                target_year=args["target_year"],
                priority=args.get("priority", 1),
                description=args.get("description"),
            )
            self._db.add(goal)
            await self._db.flush()  # get the generated id
            await self._db.commit()

            logger.info(f"Saved annual goal {goal.id} for user {user_id}")
            return ToolResult(success=True, data={"goal_id": str(goal.id)})

        except Exception as e:
            logger.error(f"Error saving annual goal: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class SaveMonthlyObjectiveTool(BaseTool):
    """Create a monthly objective, optionally linked to an annual goal."""

    name = "save_monthly_objective"
    description = (
        "Save a monthly objective for the user. Optionally links to an annual goal. "
        "Returns the created objective_id."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's UUID"},
            "description": {
                "type": "string",
                "description": "Objective description",
            },
            "annual_goal_id": {
                "type": "string",
                "description": "Optional UUID of the linked annual goal",
            },
            "is_active": {
                "type": "boolean",
                "description": "Whether this objective is active",
                "default": True,
            },
        },
        "required": ["user_id", "description"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            from src.db.models.planning import MonthlyObjective

            user_id = UUID(args["user_id"])
            annual_goal_id = UUID(args["annual_goal_id"]) if args.get("annual_goal_id") else None

            objective = MonthlyObjective(
                user_id=user_id,
                description=args["description"],
                annual_goal_id=annual_goal_id,
                is_active=args.get("is_active", True),
            )
            self._db.add(objective)
            await self._db.flush()
            await self._db.commit()

            logger.info(f"Saved monthly objective {objective.id} for user {user_id}")
            return ToolResult(success=True, data={"objective_id": str(objective.id)})

        except Exception as e:
            logger.error(f"Error saving monthly objective: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class SaveWeeklyPriorityTool(BaseTool):
    """Create a weekly priority objective."""

    name = "save_weekly_priority"
    description = "Save a weekly priority for the user. Returns the created priority_id."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's UUID"},
            "description": {
                "type": "string",
                "description": "Priority description",
            },
            "priority": {
                "type": "string",
                "enum": ["PRIMARY", "SECONDARY"],
                "description": "Priority level",
                "default": "PRIMARY",
            },
            "monthly_objective_id": {
                "type": "string",
                "description": "Optional UUID of the linked monthly objective",
            },
            "annual_goal_id": {
                "type": "string",
                "description": "Optional UUID of the linked annual goal",
            },
            "area": {
                "type": "string",
                "description": "Optional LifeArea this priority belongs to",
            },
        },
        "required": ["user_id", "description"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            from src.db.models.planning import ObjectivePriority, WeeklyObjective

            user_id = UUID(args["user_id"])
            monthly_objective_id = (
                UUID(args["monthly_objective_id"]) if args.get("monthly_objective_id") else None
            )
            annual_goal_id = UUID(args["annual_goal_id"]) if args.get("annual_goal_id") else None

            priority_value = args.get("priority", "PRIMARY")
            try:
                priority = ObjectivePriority(priority_value)
            except ValueError:
                priority = ObjectivePriority.PRIMARY

            objective = WeeklyObjective(
                user_id=user_id,
                description=args["description"],
                priority=priority,
                monthly_objective_id=monthly_objective_id,
                annual_goal_id=annual_goal_id,
                area=args.get("area"),
            )
            self._db.add(objective)
            await self._db.flush()
            await self._db.commit()

            logger.info(f"Saved weekly priority {objective.id} for user {user_id}")
            return ToolResult(success=True, data={"priority_id": str(objective.id)})

        except Exception as e:
            logger.error(f"Error saving weekly priority: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))


class AdvancePhaseTool(BaseTool):
    """Complete the current module and advance to the next onboarding phase."""

    name = "advance_phase"
    description = (
        "Mark the current phase as complete and advance to the next onboarding phase. "
        "At phase_5, triggers complete_onboarding() which activates the Trial subscription. "
        "Also named complete_current_module — use this when the user has finished a module."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's UUID"},
        },
        "required": ["user_id"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            from src.db.models.user_profile import OnboardingStatus, UserProfile
            from src.services.onboarding import (
                advance_phase,
                complete_module,
                start_deep_onboarding,
            )

            user_id = UUID(args["user_id"])

            result = await self._db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                return ToolResult(success=False, error="User profile not found")

            if profile.onboarding_status == OnboardingStatus.NOT_STARTED:
                await start_deep_onboarding(self._db, user_id)

            # Get current phase before advancing so we can mark it complete
            current_phase = profile.onboarding_current_step
            if current_phase and current_phase.startswith("phase_"):
                await complete_module(self._db, user_id, current_phase)

            profile = await advance_phase(self._db, user_id)

            logger.info(
                f"Advanced phase for user {user_id}: "
                f"step={profile.onboarding_current_step}, "
                f"status={profile.onboarding_status.value}"
            )

            return ToolResult(
                success=True,
                data={
                    "current_step": profile.onboarding_current_step,
                    "status": profile.onboarding_status.value,
                },
            )

        except Exception as e:
            logger.error(f"Error advancing phase: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))
