"""Planning API endpoints for AnnualGoal and MonthlyObjective."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user
from src.core.rate_limit import limiter_authenticated
from src.db.models.user import User
from src.db.session import get_db
from src.schemas.planning import (
    AnnualGoalCreate,
    AnnualGoalResponse,
    AnnualGoalUpdate,
    MonthlyObjectiveCreate,
    MonthlyObjectiveResponse,
    MonthlyObjectiveUpdate,
)
from src.services import planning as planning_service

router = APIRouter(prefix="/me/goals", tags=["Goals"])


# ===== Annual Goals =====


@router.get("/annual", response_model=list[AnnualGoalResponse])
@limiter_authenticated.limit("20/minute")
async def list_annual_goals(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnnualGoalResponse]:
    """List current user's annual goals."""
    goals = await planning_service.list_annual_goals(db, current_user.id)
    return [AnnualGoalResponse.model_validate(g) for g in goals]


@router.post("/annual", response_model=AnnualGoalResponse, status_code=status.HTTP_201_CREATED)
@limiter_authenticated.limit("10/minute")
async def create_annual_goal(
    request: Request,
    data: AnnualGoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnnualGoalResponse:
    """Create a new annual goal."""
    goal = await planning_service.create_annual_goal(db, current_user.id, data)
    return AnnualGoalResponse.model_validate(goal)


@router.patch("/annual/{goal_id}", response_model=AnnualGoalResponse)
@limiter_authenticated.limit("10/minute")
async def update_annual_goal(
    request: Request,
    goal_id: UUID,
    data: AnnualGoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnnualGoalResponse:
    """Update an annual goal (partial)."""
    goal = await planning_service.update_annual_goal(db, current_user.id, goal_id, data)
    return AnnualGoalResponse.model_validate(goal)


@router.delete("/annual/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter_authenticated.limit("10/minute")
async def delete_annual_goal(
    request: Request,
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an annual goal."""
    await planning_service.delete_annual_goal(db, current_user.id, goal_id)


@router.get("/annual/{goal_id}/objectives", response_model=list[MonthlyObjectiveResponse])
@limiter_authenticated.limit("20/minute")
async def list_monthly_objectives(
    request: Request,
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MonthlyObjectiveResponse]:
    """List monthly objectives for an annual goal."""
    objectives = await planning_service.list_monthly_objectives(db, current_user.id, goal_id)
    return [MonthlyObjectiveResponse.model_validate(o) for o in objectives]


# ===== Monthly Objectives =====


@router.post(
    "/monthly",
    response_model=MonthlyObjectiveResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter_authenticated.limit("10/minute")
async def create_monthly_objective(
    request: Request,
    data: MonthlyObjectiveCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MonthlyObjectiveResponse:
    """Create a new monthly objective."""
    obj = await planning_service.create_monthly_objective(db, current_user.id, data)
    return MonthlyObjectiveResponse.model_validate(obj)


@router.patch("/monthly/{obj_id}", response_model=MonthlyObjectiveResponse)
@limiter_authenticated.limit("10/minute")
async def update_monthly_objective(
    request: Request,
    obj_id: UUID,
    data: MonthlyObjectiveUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MonthlyObjectiveResponse:
    """Update a monthly objective (partial)."""
    obj = await planning_service.update_monthly_objective(db, current_user.id, obj_id, data)
    return MonthlyObjectiveResponse.model_validate(obj)


@router.delete("/monthly/{obj_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter_authenticated.limit("10/minute")
async def delete_monthly_objective(
    request: Request,
    obj_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a monthly objective."""
    await planning_service.delete_monthly_objective(db, current_user.id, obj_id)
