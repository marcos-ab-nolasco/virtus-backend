"""
Example skill implementations

Provides reference implementations for common skill patterns.
"""

from src.skills.examples.get_calendar_events import GetCalendarEventsSkill
from src.skills.examples.get_current_date import GetCurrentDateSkill
from src.skills.examples.get_user_preferences import GetUserPreferencesSkill

__all__ = [
    "GetCurrentDateSkill",
    "GetUserPreferencesSkill",
    "GetCalendarEventsSkill",
]
