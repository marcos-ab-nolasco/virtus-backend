"""
GetCalendarEvents Skill

Retrieves calendar events for a user within a specified date range.
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.calendar_event import CalendarEvent
from src.db.session import get_async_sessionmaker
from src.skills.base import BaseSkill, SkillResult


class GetCalendarEventsSkill(BaseSkill):
    """
    Skill that retrieves calendar events for a user

    Parameters:
        user_id: UUID of the user
        days_ahead (optional): Number of days ahead to fetch events (default: 7)
        limit (optional): Maximum number of events to return (default: 50)

    Returns:
        List of calendar events
    """

    name = "get_calendar_events"
    description = "Get upcoming calendar events for a user within a specified date range"
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "UUID of the user",
            },
            "days_ahead": {
                "type": "integer",
                "description": "Number of days ahead to fetch events",
                "default": 7,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of events to return",
                "default": 50,
            },
        },
        "required": ["user_id"],
    }

    async def execute(self, args: dict[str, Any]) -> SkillResult:
        """
        Execute the skill to get calendar events

        Args:
            args: Dictionary with "user_id", "days_ahead", and "limit" keys

        Returns:
            SkillResult with calendar events data
        """
        try:
            # Extract and validate user_id
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

            # Extract optional parameters
            days_ahead = args.get("days_ahead", 7)
            limit = args.get("limit", 50)

            # Calculate date range
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=days_ahead)

            # Query calendar events
            session_factory = get_async_sessionmaker()
            async with session_factory() as db:
                stmt = (
                    select(CalendarEvent)
                    .where(
                        CalendarEvent.user_id == user_id,
                        CalendarEvent.start_time >= start_date,
                        CalendarEvent.start_time <= end_date,
                    )
                    .order_by(CalendarEvent.start_time)
                    .limit(limit)
                )

                result = await db.execute(stmt)
                events = result.scalars().all()

                # Serialize events
                events_data = []
                for event in events:
                    events_data.append(
                        {
                            "id": str(event.id),
                            "title": event.title,
                            "description": event.description,
                            "start_time": event.start_time.isoformat() if event.start_time else None,
                            "end_time": event.end_time.isoformat() if event.end_time else None,
                            "location": event.location,
                            "external_id": event.external_id,
                            "is_all_day": event.is_all_day,
                        }
                    )

                return SkillResult(
                    success=True,
                    data={
                        "events": events_data,
                        "count": len(events_data),
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                    error=None,
                )

        except Exception as e:
            return SkillResult(
                success=False,
                data=None,
                error=f"Failed to get calendar events: {type(e).__name__}: {str(e)}",
            )
