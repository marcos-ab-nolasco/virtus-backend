"""Goal management tools for the GoalAgent.

Provides tools for listing goals and updating goal status.
Goal creation is handled by SaveAnnualGoalTool and SaveMonthlyObjectiveTool
from onboarding_tools.py (already registered in the tool registry).
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ListUserGoalsTool(BaseTool):
    """List the user's annual goals with objective counts."""

    name = "list_user_goals"
    description = (
        "List the user's annual goals. Use this before creating a new goal to check for "
        "duplicates. Returns goal id, title, life_area, target_year, priority, status, "
        "and monthly_objectives_count. Optionally filter by status."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's UUID"},
            "status_filter": {
                "type": "string",
                "description": (
                    "Optional filter by goal status: "
                    "PLANNING, ACTIVE, REVIEW_PENDING, COMPLETED, ABANDONED"
                ),
            },
        },
        "required": ["user_id"],
    }

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            from src.db.models.planning import AnnualGoal, MonthlyObjective

            user_id = UUID(args["user_id"])
            status_filter = args.get("status_filter")

            stmt = (
                select(AnnualGoal)
                .where(AnnualGoal.user_id == user_id)
                .order_by(AnnualGoal.priority.asc())
            )
            if status_filter:
                stmt = stmt.where(AnnualGoal.status == status_filter)

            goals_result = await self._db.execute(stmt)
            goals = list(goals_result.scalars().all())

            if not goals:
                return ToolResult(
                    success=True,
                    data={"goals": [], "total": 0},
                )

            # Count monthly objectives per goal in a single query
            goal_ids = [g.id for g in goals]
            obj_result = await self._db.execute(
                select(MonthlyObjective.annual_goal_id).where(
                    MonthlyObjective.annual_goal_id.in_(goal_ids),
                    MonthlyObjective.is_active.is_(True),
                )
            )
            counts: dict[UUID, int] = {}
            for (gid,) in obj_result:
                counts[gid] = counts.get(gid, 0) + 1

            return ToolResult(
                success=True,
                data={
                    "goals": [
                        {
                            "goal_id": str(g.id),
                            "title": g.title,
                            "life_area": g.life_area,
                            "target_year": g.target_year,
                            "priority": g.priority,
                            "status": g.status,
                            "monthly_objectives_count": counts.get(g.id, 0),
                        }
                        for g in goals
                    ],
                    "total": len(goals),
                },
            )

        except ValueError:
            return ToolResult(success=False, error="Invalid user_id format")
        except Exception as e:
            logger.exception("ListUserGoalsTool error")
            return ToolResult(success=False, error=str(e))


class UpdateGoalStatusTool(BaseTool):
    """Update the status of an annual goal."""

    name = "update_goal_status"
    description = (
        "Update the status of an annual goal. "
        "Valid statuses: PLANNING, ACTIVE, REVIEW_PENDING, COMPLETED, ABANDONED."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's UUID"},
            "goal_id": {"type": "string", "description": "The annual goal UUID"},
            "status": {
                "type": "string",
                "description": (
                    "New status: PLANNING, ACTIVE, REVIEW_PENDING, COMPLETED, ABANDONED"
                ),
            },
        },
        "required": ["user_id", "goal_id", "status"],
    }

    _valid_statuses = {"PLANNING", "ACTIVE", "REVIEW_PENDING", "COMPLETED", "ABANDONED"}

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            from sqlalchemy import and_

            from src.db.models.planning import AnnualGoal

            user_id = UUID(args["user_id"])
            goal_id = UUID(args["goal_id"])
            new_status = args["status"]

            if new_status not in self._valid_statuses:
                return ToolResult(
                    success=False,
                    error=f"Invalid status '{new_status}'. Valid: {', '.join(self._valid_statuses)}",
                )

            result = await self._db.execute(
                select(AnnualGoal).where(
                    and_(AnnualGoal.id == goal_id, AnnualGoal.user_id == user_id)
                )
            )
            goal = result.scalar_one_or_none()
            if not goal:
                return ToolResult(success=False, error="Goal not found")

            goal.status = new_status
            await self._db.commit()
            await self._db.refresh(goal)

            return ToolResult(
                success=True,
                data={"goal_id": str(goal.id), "new_status": goal.status},
            )

        except ValueError:
            return ToolResult(success=False, error="Invalid UUID format in user_id or goal_id")
        except Exception as e:
            logger.exception("UpdateGoalStatusTool error")
            return ToolResult(success=False, error=str(e))
