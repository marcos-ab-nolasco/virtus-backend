"""Habit service layer for business logic."""

import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.habit import Habit, HabitLog
from src.schemas.habit import (
    HabitCreate,
    HabitLogCreate,
    HabitStatsResponse,
    HabitUpdate,
    HeatmapEntry,
)


async def list_habits(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    is_active: bool | None = None,
    is_archived: bool | None = None,
) -> list[Habit]:
    """List habits for a user with optional filters."""
    stmt = select(Habit).where(Habit.user_id == user_id)
    if is_active is not None:
        stmt = stmt.where(Habit.is_active == is_active)
    if is_archived is not None:
        stmt = stmt.where(Habit.is_archived == is_archived)
    stmt = stmt.order_by(Habit.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_habit(db: AsyncSession, user_id: uuid.UUID, habit_id: uuid.UUID) -> Habit:
    """Get a single habit, ensuring ownership."""
    result = await db.execute(
        select(Habit).where(and_(Habit.id == habit_id, Habit.user_id == user_id))
    )
    habit = result.scalar_one_or_none()
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    return habit


async def create_habit(db: AsyncSession, user_id: uuid.UUID, data: HabitCreate) -> Habit:
    """Create a new habit."""
    habit = Habit(user_id=user_id, **data.model_dump())
    db.add(habit)
    await db.commit()
    await db.refresh(habit)
    return habit


async def update_habit(
    db: AsyncSession, user_id: uuid.UUID, habit_id: uuid.UUID, data: HabitUpdate
) -> Habit:
    """Partial update of a habit."""
    habit = await get_habit(db, user_id, habit_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(habit, field, value)
    await db.commit()
    await db.refresh(habit)
    return habit


async def delete_habit(db: AsyncSession, user_id: uuid.UUID, habit_id: uuid.UUID) -> None:
    """Delete a habit and its logs."""
    habit = await get_habit(db, user_id, habit_id)
    await db.execute(delete(HabitLog).where(HabitLog.habit_id == habit.id))
    await db.delete(habit)
    await db.commit()


async def archive_habit(db: AsyncSession, user_id: uuid.UUID, habit_id: uuid.UUID) -> Habit:
    """Archive a habit."""
    habit = await get_habit(db, user_id, habit_id)
    habit.is_archived = True
    habit.is_active = False
    habit.archived_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(habit)
    return habit


async def toggle_habit_log(
    db: AsyncSession, user_id: uuid.UUID, habit_id: uuid.UUID, data: HabitLogCreate
) -> HabitLog:
    """Upsert a habit log for a given date."""
    await get_habit(db, user_id, habit_id)

    result = await db.execute(
        select(HabitLog).where(
            and_(HabitLog.habit_id == habit_id, HabitLog.date == data.date)
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.completed = data.completed
        existing.quantity = data.quantity
        existing.notes = data.notes
        existing.channel = data.channel
        await db.commit()
        await db.refresh(existing)
        return existing

    log = HabitLog(
        habit_id=habit_id,
        user_id=user_id,
        **data.model_dump(),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def list_habit_logs(
    db: AsyncSession,
    user_id: uuid.UUID,
    habit_id: uuid.UUID,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[HabitLog], int]:
    """List habit logs with optional date range and pagination."""
    await get_habit(db, user_id, habit_id)

    base = select(HabitLog).where(HabitLog.habit_id == habit_id)
    if start_date:
        base = base.where(HabitLog.date >= start_date)
    if end_date:
        base = base.where(HabitLog.date <= end_date)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar() or 0

    stmt = base.order_by(HabitLog.date.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    logs = list(result.scalars().all())

    return logs, total


async def get_habit_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
    habit_id: uuid.UUID,
    *,
    heatmap_days: int = 90,
) -> HabitStatsResponse:
    """Compute stats for a habit (simplified for DAILY in M1)."""
    await get_habit(db, user_id, habit_id)

    today = date.today()
    heatmap_start = today - timedelta(days=heatmap_days - 1)

    # Fetch all completed logs for this habit
    result = await db.execute(
        select(HabitLog)
        .where(and_(HabitLog.habit_id == habit_id, HabitLog.completed.is_(True)))
        .order_by(HabitLog.date.desc())
    )
    completed_logs = result.scalars().all()
    completed_dates = {log.date for log in completed_logs}

    # Current streak: consecutive days from today backwards
    current_streak = 0
    check_date = today
    while check_date in completed_dates:
        current_streak += 1
        check_date -= timedelta(days=1)

    # Longest streak: scan all completed dates chronologically
    longest_streak = 0
    if completed_dates:
        sorted_dates = sorted(completed_dates)
        streak = 1
        for i in range(1, len(sorted_dates)):
            if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
                streak += 1
            else:
                longest_streak = max(longest_streak, streak)
                streak = 1
        longest_streak = max(longest_streak, streak)

    # Completion rates
    days_7 = {today - timedelta(days=i) for i in range(7)}
    days_30 = {today - timedelta(days=i) for i in range(30)}
    completion_rate_7d = len(completed_dates & days_7) / 7 if days_7 else 0.0
    completion_rate_30d = len(completed_dates & days_30) / 30 if days_30 else 0.0

    # Heatmap: fetch all logs (completed or not) in the heatmap range
    heatmap_result = await db.execute(
        select(HabitLog)
        .where(
            and_(
                HabitLog.habit_id == habit_id,
                HabitLog.date >= heatmap_start,
                HabitLog.date <= today,
            )
        )
        .order_by(HabitLog.date)
    )
    heatmap_logs = {log.date: log for log in heatmap_result.scalars().all()}

    heatmap: list[HeatmapEntry] = []
    for i in range(heatmap_days):
        d = heatmap_start + timedelta(days=i)
        log = heatmap_logs.get(d)
        heatmap.append(
            HeatmapEntry(
                date=d,
                completed=log.completed if log else False,
                quantity=log.quantity if log else None,
            )
        )

    return HabitStatsResponse(
        habit_id=habit_id,
        current_streak=current_streak,
        longest_streak=longest_streak,
        completion_rate_7d=round(completion_rate_7d, 4),
        completion_rate_30d=round(completion_rate_30d, 4),
        total_completions=len(completed_dates),
        heatmap=heatmap,
    )
