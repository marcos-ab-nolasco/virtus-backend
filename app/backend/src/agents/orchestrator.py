"""
Orchestrator Agent - Routes user messages to tools or direct responses

The orchestrator is responsible for:
1. Building user context
2. Checking if onboarding is needed
3. Deciding whether to invoke a tool or respond directly
4. Executing tools when needed
5. Formatting responses

Refactored to inherit from BaseAgent and use skills.
"""

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from src.agents.base import AgentResponse, BaseAgent
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator agent that routes messages and invokes tools.

    Inherits from BaseAgent to use skills-based system prompts.
    Maintains backward compatibility with process_message() API.
    """

    def __init__(
        self,
        llm_service: Any,
        tool_registry: ToolRegistry,
        context_service: Any,
        skills_path: Path | None = None,
    ):
        """
        Initialize orchestrator with dependencies.

        Args:
            llm_service: LLM service for generating responses
            tool_registry: Registry of available tools
            context_service: Service for building user context
            skills_path: Optional path to skills folder
        """
        super().__init__(
            llm_service=llm_service,
            tool_registry=tool_registry,
            skills_path=skills_path,
        )
        self.context_service = context_service

        # Keep references with original names for backward compatibility
        self.llm_service = llm_service
        self.tool_registry = tool_registry

    @property
    def name(self) -> str:
        return "orchestrator"

    @property
    def skills(self) -> list[str]:
        return [
            "shared/persona_base",
            "shared/tom_ajuste",
            "shared/contexto_usuario",
            "orchestrator/classificacao_intencao",
            "orchestrator/roteamento",
        ]

    @property
    def available_tools(self) -> list[str]:
        # Orchestrator should not execute tools directly
        return []

    def should_route_to_onboarding(self, context: dict[str, Any]) -> bool:
        """
        Check if user needs to be routed to onboarding.

        Args:
            context: User context with profile data

        Returns:
            True if onboarding is needed
        """
        profile = context.get("profile")
        if not profile:
            return True

        onboarding_status = profile.get("onboarding_status")
        return onboarding_status != "COMPLETED"

    async def process_message(
        self,
        user_id: UUID,
        message: str,
        conversation_id: UUID,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Backward-compatible entrypoint for callers expecting a string response.

        This method now returns the direct orchestrator response when available,
        otherwise it falls back to a generic message. Prefer using AgentRouter.
        """
        logger.warning(
            "process_message() is deprecated; use AgentRouter for routing. "
            "Returning a fallback response."
        )
        return self._get_fallback_error_message()

    async def _build_context(self, user_id: UUID) -> dict[str, Any]:
        """
        Build user context for the conversation.

        Args:
            user_id: UUID of the user

        Returns:
            Context dictionary
        """
        try:
            if hasattr(self.context_service, "build_permanent_context"):
                context: dict[str, Any] = await self.context_service.build_permanent_context(
                    user_id
                )
                return context
            else:
                return {"user": {"id": str(user_id)}}
        except Exception as e:
            logger.warning(f"Failed to build context: {e}")
            return {"user": {"id": str(user_id)}}

    def _get_fallback_error_message(self) -> str:
        """
        Get fallback error message for critical failures.

        Returns:
            Generic error message
        """
        return "Desculpe, estou com dificuldades técnicas. Por favor, tente novamente mais tarde."

    async def process(
        self,
        message: str,
        user_context: dict[str, Any],
        conversation_history: list[dict[str, Any]],
    ):
        """
        Decide the next agent based on user context.

        Returns an AgentResponse with next_agent set.
        """
        if self.should_route_to_onboarding(user_context):
            return AgentResponse(response=None, next_agent="onboarding")
        return AgentResponse(response=None, next_agent="advisor")
