"""AgentRouter for delegating messages to the appropriate agent."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.agents.base import AgentResponse
from src.services.agent_factory import AgentFactory

logger = logging.getLogger(__name__)


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
        orchestrator.set_trace_context(user_id=str(user_id), conversation_id=str(conversation_id))
        user_context = await orchestrator._build_context(user_id)

        decision: AgentResponse = await orchestrator.process(
            message=message,
            user_context=user_context,
            conversation_history=conversation_history,
        )

        if decision.next_agent is None:
            return decision.response or "Desculpe, tive um problema."

        agent = self._factory.create_agent(decision.next_agent)
        agent.set_trace_context(user_id=str(user_id), conversation_id=str(conversation_id))
        logger.info(
            "Agent routing decision: next_agent=%s user_id=%s conv_id=%s",
            decision.next_agent,
            user_id,
            conversation_id,
        )
        agent_response: AgentResponse = await agent.process(
            message=message,
            user_context=user_context,
            conversation_history=conversation_history,
        )

        return agent_response.response or "Desculpe, tive um problema."
