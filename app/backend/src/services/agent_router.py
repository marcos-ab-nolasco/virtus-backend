"""AgentRouter for delegating messages to the appropriate agent."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.agents.base import AgentResponse
from src.services.agent_factory import AgentFactory


class AgentRouter:
    """Routes messages by consulting OrchestratorAgent and delegating to agents."""

    def __init__(self, *, agent_factory: AgentFactory) -> None:
        self._factory = agent_factory

    async def route(
        self,
        *,
        user_id: UUID,
        message: str,
        conversation_id: UUID,
        conversation_history: list[dict[str, Any]],
    ) -> str:
        orchestrator = self._factory.create_orchestrator()
        user_context = await orchestrator._build_context(user_id)

        decision: AgentResponse = await orchestrator.process(
            message=message,
            user_context=user_context,
            conversation_history=conversation_history,
        )

        if decision.next_agent is None:
            return decision.response or "Desculpe, tive um problema."

        agent = self._factory.create_agent(decision.next_agent)
        agent_response: AgentResponse = await agent.process(
            message=message,
            user_context=user_context,
            conversation_history=conversation_history,
        )

        return agent_response.response or "Desculpe, tive um problema."
