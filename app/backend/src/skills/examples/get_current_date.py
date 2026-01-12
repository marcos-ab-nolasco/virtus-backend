"""
GetCurrentDate Skill

Returns the current date and time, optionally with timezone support.
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.skills.base import BaseSkill, SkillResult


class GetCurrentDateSkill(BaseSkill):
    """
    Skill that returns the current date and time

    Parameters:
        timezone (optional): Timezone name (e.g., "UTC", "America/New_York")
        format (optional): Output format - "iso" (default) or "human"

    Returns:
        Current date/time information
    """

    name = "get_current_date"
    description = "Get the current date and time, optionally in a specific timezone"
    parameters = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone name (e.g., 'UTC', 'America/New_York', 'Europe/London')",
                "default": "UTC",
            },
            "format": {
                "type": "string",
                "description": "Output format: 'iso' for ISO 8601 or 'human' for readable format",
                "enum": ["iso", "human"],
                "default": "iso",
            },
        },
        "required": [],
    }

    async def execute(self, args: dict[str, Any]) -> SkillResult:
        """
        Execute the skill to get current date/time

        Args:
            args: Dictionary with optional "timezone" and "format" keys

        Returns:
            SkillResult with current date/time information
        """
        try:
            # Extract arguments with defaults
            timezone_str = args.get("timezone", "UTC")
            output_format = args.get("format", "iso")

            # Parse timezone
            try:
                tz = ZoneInfo(timezone_str)
            except ZoneInfoNotFoundError:
                # Invalid timezone, fallback to UTC
                tz = ZoneInfo("UTC")
                timezone_str = "UTC"  # Update to reflect actual used timezone

            # Get current time in specified timezone
            now = datetime.now(tz)

            # Format output
            if output_format == "human":
                formatted_date = now.strftime("%A, %B %d, %Y at %I:%M %p %Z")
            else:  # iso
                formatted_date = now.isoformat()

            return SkillResult(
                success=True,
                data={
                    "datetime": formatted_date,
                    "timestamp": now.timestamp(),
                    "timezone": timezone_str,
                    "iso_format": now.isoformat(),
                    "date": now.strftime("%Y-%m-%d"),
                    "time": now.strftime("%H:%M:%S"),
                    "day_of_week": now.strftime("%A"),
                },
                error=None,
            )

        except Exception as e:
            return SkillResult(
                success=False, data=None, error=f"Failed to get current date: {str(e)}"
            )
