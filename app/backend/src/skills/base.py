"""
Base classes for the Skills System

Defines the interface that all skills must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillParameter:
    """
    Represents a skill parameter with metadata

    Attributes:
        name: Parameter name
        type: Parameter type (string, integer, boolean, object, array)
        description: Human-readable description
        required: Whether the parameter is required
        default: Default value if not provided
    """

    name: str
    type: str  # JSONSchema type: string, integer, boolean, object, array
    description: str
    required: bool = False
    default: Any = None

    def to_jsonschema(self) -> dict[str, Any]:
        """Convert parameter to JSONSchema format"""
        schema: dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }

        if self.default is not None:
            schema["default"] = self.default

        return schema


@dataclass
class SkillResult:
    """
    Result of skill execution

    Attributes:
        success: Whether the skill executed successfully
        data: Result data (any JSON-serializable type)
        error: Error message if execution failed
    """

    success: bool
    data: Any | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }


class BaseSkill(ABC):
    """
    Abstract base class for all skills

    All skills must inherit from this class and implement the execute method.

    Attributes:
        name: Unique identifier for the skill
        description: Human-readable description of what the skill does
        parameters: JSONSchema definition of the skill's parameters
    """

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    async def execute(self, args: dict[str, Any]) -> SkillResult:
        """
        Execute the skill with the given arguments

        Args:
            args: Dictionary of arguments matching the parameters schema

        Returns:
            SkillResult indicating success/failure and result data

        Raises:
            Any exceptions should be caught and returned as SkillResult with error
        """
        pass

    def to_tool_definition(self) -> dict[str, Any]:
        """
        Convert skill to LLM tool definition format

        Returns tool definition compatible with OpenAI/Anthropic function calling
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
