"""
Example tool implementations

Provides reference implementations for common tool patterns.
"""

from src.tools.examples.get_calendar_events import GetCalendarEventsTool
from src.tools.examples.get_current_date import GetCurrentDateTool
from src.tools.examples.get_user_preferences import GetUserPreferencesTool

__all__ = [
    "GetCurrentDateTool",
    "GetUserPreferencesTool",
    "GetCalendarEventsTool",
]
