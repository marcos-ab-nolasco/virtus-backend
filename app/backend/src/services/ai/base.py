"""Abstract base class for AI service providers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseAIService(ABC):
    """Defines the contract for AI providers used by the chat service."""

    @abstractmethod
    async def generate_response(
        self,
        messages: list[dict[str, Any]],
        model: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a response based on the conversation history."""
        raise NotImplementedError

    @abstractmethod
    async def generate_response_with_tools(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        tool_choice: str = "auto",
        model: str = "gpt-4o-mini",
    ) -> dict[str, Any]:
        """
        Generate response with function calling support.

        Args:
            messages: Conversation history
            system_prompt: System instructions
            tools: Tool definitions (function calling schema)
            tool_choice: "auto", "none", or "required"
            model: Model to use

        Returns:
            dict with keys:
            - content: str | None (text response)
            - tool_calls: list[dict] | None (function calls)
            - finish_reason: str (completion reason)
        """
        raise NotImplementedError
