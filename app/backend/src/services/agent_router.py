"""AgentRouter for delegating messages to the appropriate agent."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.agents.base import AgentResponse
from src.db.models.conversation import ConversationContext
from src.db.models.user_profile import OnboardingStatus
from src.services.agent_factory import AgentFactory

logger = logging.getLogger(__name__)


class AgentRouter:
    """Routes messages based on conversation context_type and user onboarding status."""

    def __init__(self, *, agent_factory: AgentFactory) -> None:
        self._factory = agent_factory

    async def route(
        self,
        *,
        user_id: UUID,
        message: str,
        conversation_id: UUID,
        conversation_history: list[dict[str, Any]],
        context_type: ConversationContext | str | None = None,
    ) -> AgentResponse:
        # 1. Module conversations always go to OnboardingAgent
        if (
            context_type == ConversationContext.ONBOARDING_MODULE
            or context_type == "ONBOARDING_MODULE"
        ):
            agent = self._factory.create_agent("onboarding")
            agent.set_trace_context(user_id=str(user_id), conversation_id=str(conversation_id))
            logger.info(
                "Agent routing: onboarding module conv user_id=%s conv_id=%s",
                user_id,
                conversation_id,
            )

            orchestrator = self._factory.create_orchestrator()
            orchestrator.set_trace_context(
                user_id=str(user_id), conversation_id=str(conversation_id)
            )
            user_context = await orchestrator._build_context(user_id)

            agent_response: AgentResponse = await agent.process(
                message=message,
                user_context=user_context,
                conversation_history=conversation_history,
            )
            agent_response.response = agent_response.response or "Desculpe, tive um problema."
            return agent_response

        # 2. Build user context for status-based routing
        orchestrator = self._factory.create_orchestrator()
        orchestrator.set_trace_context(user_id=str(user_id), conversation_id=str(conversation_id))
        user_context = await orchestrator._build_context(user_id)

        onboarding_status = (user_context.get("profile") or {}).get("onboarding_status")

        # 3. Users in setup flow (NOT_STARTED or IN_PROGRESS) → SetupAgent
        if onboarding_status in (
            OnboardingStatus.NOT_STARTED,
            OnboardingStatus.IN_PROGRESS,
            "NOT_STARTED",
            "IN_PROGRESS",
        ):
            agent = self._factory.create_agent("setup")
            agent.set_trace_context(user_id=str(user_id), conversation_id=str(conversation_id))
            logger.info(
                "Agent routing: setup agent user_id=%s conv_id=%s status=%s",
                user_id,
                conversation_id,
                onboarding_status,
            )

            agent_response = await agent.process(
                message=message,
                user_context=user_context,
                conversation_history=conversation_history,
            )
            agent_response.response = agent_response.response or "Desculpe, tive um problema."
            return agent_response

        # 4. Default: consult orchestrator for routing decision (advisor etc.)
        decision: AgentResponse = await orchestrator.process(
            message=message,
            user_context=user_context,
            conversation_history=conversation_history,
        )

        if decision.next_agent is None:
            decision.response = decision.response or "Desculpe, tive um problema."
            return decision

        agent = self._factory.create_agent(decision.next_agent)
        agent.set_trace_context(user_id=str(user_id), conversation_id=str(conversation_id))
        logger.info(
            "Agent routing decision: next_agent=%s user_id=%s conv_id=%s",
            decision.next_agent,
            user_id,
            conversation_id,
        )
        agent_response = await agent.process(
            message=message,
            user_context=user_context,
            conversation_history=conversation_history,
        )

        agent_response.response = agent_response.response or "Desculpe, tive um problema."
        return agent_response
