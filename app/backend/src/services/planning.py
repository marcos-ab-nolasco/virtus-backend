"""Planning service layer for AnnualGoal and MonthlyObjective CRUD."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.planning import AnnualGoal, MonthlyObjective
from src.schemas.planning import (
    AnnualGoalCreate,
    AnnualGoalUpdate,
    MonthlyObjectiveCreate,
    MonthlyObjectiveUpdate,
)

# ===== AnnualGoal =====


async def list_annual_goals(db: AsyncSession, user_id: uuid.UUID) -> list[AnnualGoal]:
    """List all annual goals for a user, ordered by priority."""
    result = await db.execute(
        select(AnnualGoal).where(AnnualGoal.user_id == user_id).order_by(AnnualGoal.priority.asc())
    )
    return list(result.scalars().all())


async def get_annual_goal(db: AsyncSession, user_id: uuid.UUID, goal_id: uuid.UUID) -> AnnualGoal:
    """Get a single annual goal, ensuring ownership."""
    result = await db.execute(
        select(AnnualGoal).where(and_(AnnualGoal.id == goal_id, AnnualGoal.user_id == user_id))
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annual goal not found",
        )
    return goal


async def create_annual_goal(
    db: AsyncSession, user_id: uuid.UUID, data: AnnualGoalCreate
) -> AnnualGoal:
    """Create a new annual goal."""
    goal = AnnualGoal(user_id=user_id, **data.model_dump())
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


async def update_annual_goal(
    db: AsyncSession, user_id: uuid.UUID, goal_id: uuid.UUID, data: AnnualGoalUpdate
) -> AnnualGoal:
    """Partial update of an annual goal."""
    goal = await get_annual_goal(db, user_id, goal_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(goal, field, value)
    await db.commit()
    await db.refresh(goal)
    return goal


async def delete_annual_goal(db: AsyncSession, user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    """Delete an annual goal (cascade removes monthly objectives)."""
    goal = await get_annual_goal(db, user_id, goal_id)
    await db.delete(goal)
    await db.commit()


# ===== MonthlyObjective =====


async def list_monthly_objectives(
    db: AsyncSession, user_id: uuid.UUID, annual_goal_id: uuid.UUID
) -> list[MonthlyObjective]:
    """List monthly objectives for a specific annual goal."""
    await get_annual_goal(db, user_id, annual_goal_id)
    result = await db.execute(
        select(MonthlyObjective)
        .where(
            and_(
                MonthlyObjective.user_id == user_id,
                MonthlyObjective.annual_goal_id == annual_goal_id,
            )
        )
        .order_by(MonthlyObjective.created_at.asc())
    )
    return list(result.scalars().all())


async def get_monthly_objective(
    db: AsyncSession, user_id: uuid.UUID, obj_id: uuid.UUID
) -> MonthlyObjective:
    """Get a single monthly objective, ensuring ownership."""
    result = await db.execute(
        select(MonthlyObjective).where(
            and_(
                MonthlyObjective.id == obj_id,
                MonthlyObjective.user_id == user_id,
            )
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monthly objective not found",
        )
    return obj


async def create_monthly_objective(
    db: AsyncSession, user_id: uuid.UUID, data: MonthlyObjectiveCreate
) -> MonthlyObjective:
    """Create a new monthly objective."""
    obj = MonthlyObjective(user_id=user_id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_monthly_objective(
    db: AsyncSession, user_id: uuid.UUID, obj_id: uuid.UUID, data: MonthlyObjectiveUpdate
) -> MonthlyObjective:
    """Partial update of a monthly objective."""
    obj = await get_monthly_objective(db, user_id, obj_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_monthly_objective(db: AsyncSession, user_id: uuid.UUID, obj_id: uuid.UUID) -> None:
    """Delete a monthly objective."""
    obj = await get_monthly_objective(db, user_id, obj_id)
    await db.delete(obj)
    await db.commit()
