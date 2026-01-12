"""
Action types and data structures for the Orchestrator Agent

Defines the possible actions the orchestrator can take.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ActionType(Enum):
    """Types of actions the orchestrator can take"""

    DIRECT_RESPONSE = "direct_response"  # Respond directly without skill
    SKILL_CALL = "skill_call"  # Invoke a skill


@dataclass
class Action:
    """
    Represents an action to be taken by the orchestrator

    Attributes:
        type: The type of action (DIRECT_RESPONSE or SKILL_CALL)
        skill_name: Name of skill to invoke (only for SKILL_CALL)
        skill_args: Arguments to pass to skill (only for SKILL_CALL)
        reasoning: Optional reasoning for the action (for logging/debugging)
    """

    type: ActionType
    skill_name: str | None = None
    skill_args: dict[str, Any] | None = None
    reasoning: str | None = None
