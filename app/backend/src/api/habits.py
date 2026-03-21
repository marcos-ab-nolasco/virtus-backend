"""Habits API endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user
from src.core.rate_limit import limiter_authenticated
from src.db.models.user import User
from src.db.session import get_db
from src.schemas.habit import (
    HabitCreate,
    HabitLogCreate,
    HabitLogListResponse,
    HabitLogResponse,
    HabitResponse,
    HabitStatsResponse,
    HabitUpdate,
)
from src.services import habit as habit_service

router = APIRouter(prefix="/me/habits", tags=["Habits"])


@router.get("", response_model=list[HabitResponse])
@limiter_authenticated.limit("20/minute")
async def list_habits(
    request: Request,
    is_active: bool | None = Query(None),
    is_archived: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[HabitResponse]:
    """List current user's habits with today's log status."""
    habits = await habit_service.list_habits(
        db, current_user.id, is_active=is_active, is_archived=is_archived
    )
    today_log_map = await habit_service.get_today_log_map(
        db, current_user.id, [h.id for h in habits]
    )
    return [
        HabitResponse.model_validate(h).model_copy(
            update={
                "today_log": HabitLogResponse.model_validate(today_log_map[h.id])
                if h.id in today_log_map
                else None
            }
        )
        for h in habits
    ]


@router.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
@limiter_authenticated.limit("10/minute")
async def create_habit(
    request: Request,
    data: HabitCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HabitResponse:
    """Create a new habit."""
    habit = await habit_service.create_habit(db, current_user.id, data)
    return HabitResponse.model_validate(habit)


@router.get("/{habit_id}", response_model=HabitResponse)
@limiter_authenticated.limit("20/minute")
async def get_habit(
    request: Request,
    habit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HabitResponse:
    """Get a habit by ID."""
    habit = await habit_service.get_habit(db, current_user.id, habit_id)
    return HabitResponse.model_validate(habit)


@router.patch("/{habit_id}", response_model=HabitResponse)
@limiter_authenticated.limit("10/minute")
async def update_habit(
    request: Request,
    habit_id: UUID,
    data: HabitUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HabitResponse:
    """Update a habit (partial)."""
    habit = await habit_service.update_habit(db, current_user.id, habit_id, data)
    return HabitResponse.model_validate(habit)


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter_authenticated.limit("10/minute")
async def delete_habit(
    request: Request,
    habit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a habit."""
    await habit_service.delete_habit(db, current_user.id, habit_id)


@router.post("/{habit_id}/archive", response_model=HabitResponse)
@limiter_authenticated.limit("10/minute")
async def archive_habit(
    request: Request,
    habit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HabitResponse:
    """Archive a habit."""
    habit = await habit_service.archive_habit(db, current_user.id, habit_id)
    return HabitResponse.model_validate(habit)


@router.post(
    "/{habit_id}/logs", response_model=HabitLogResponse, status_code=status.HTTP_201_CREATED
)
@limiter_authenticated.limit("30/minute")
async def toggle_habit_log(
    request: Request,
    habit_id: UUID,
    data: HabitLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HabitLogResponse:
    """Toggle a habit log (upsert for habit+date)."""
    log = await habit_service.toggle_habit_log(db, current_user.id, habit_id, data)
    return HabitLogResponse.model_validate(log)


@router.get("/{habit_id}/logs", response_model=HabitLogListResponse)
@limiter_authenticated.limit("20/minute")
async def list_habit_logs(
    request: Request,
    habit_id: UUID,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HabitLogListResponse:
    """List habit logs with optional date range."""
    logs, total = await habit_service.list_habit_logs(
        db,
        current_user.id,
        habit_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return HabitLogListResponse(
        logs=[HabitLogResponse.model_validate(log) for log in logs],
        total=total,
    )


@router.get("/{habit_id}/stats", response_model=HabitStatsResponse)
@limiter_authenticated.limit("20/minute")
async def get_habit_stats(
    request: Request,
    habit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HabitStatsResponse:
    """Get stats for a habit (streak, completion rates, heatmap)."""
    return await habit_service.get_habit_stats(db, current_user.id, habit_id)
