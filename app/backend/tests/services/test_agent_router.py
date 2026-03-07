"""Tests for AgentRouter service.

Validates orchestration between OrchestratorAgent and delegated agents.
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.agents.base import AgentResponse
from src.services.agent_router import AgentRouter


class TestAgentRouter:
    """Unit tests for AgentRouter routing behavior."""

    @pytest.mark.asyncio
    async def test_route_delegates_to_next_agent(self) -> None:
        """Router should delegate to the agent indicated by orchestrator."""
        mock_factory = Mock()
        orchestrator = AsyncMock()
        orchestrator.set_trace_context = Mock()
        orchestrator._build_context = AsyncMock(
            return_value={"profile": {"onboarding_status": "COMPLETED"}}
        )
        onboarding_agent = AsyncMock()
        onboarding_agent.set_trace_context = Mock()

        orchestrator.process = AsyncMock(
            return_value=AgentResponse(response=None, next_agent="onboarding")
        )
        onboarding_agent.process = AsyncMock(
            return_value=AgentResponse(response="Resposta do onboarding")
        )

        mock_factory.create_orchestrator.return_value = orchestrator
        mock_factory.create_agent.return_value = onboarding_agent

        router = AgentRouter(agent_factory=mock_factory)

        response = await router.route(
            user_id=uuid4(),
            message="Oi",
            conversation_id=uuid4(),
            conversation_history=[{"role": "user", "content": "Oi"}],
        )

        assert response == AgentResponse(response="Resposta do onboarding")
        mock_factory.create_agent.assert_called_once_with("onboarding")
        onboarding_agent.process.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_route_returns_orchestrator_response_when_no_next_agent(self) -> None:
        """Router should return orchestrator response if next_agent is None."""
        mock_factory = Mock()
        orchestrator = AsyncMock()
        orchestrator.set_trace_context = Mock()
        orchestrator._build_context = AsyncMock(
            return_value={"profile": {"onboarding_status": "COMPLETED"}}
        )

        orchestrator.process = AsyncMock(
            return_value=AgentResponse(response="Resposta direta", next_agent=None)
        )

        mock_factory.create_orchestrator.return_value = orchestrator

        router = AgentRouter(agent_factory=mock_factory)

        response = await router.route(
            user_id=uuid4(),
            message="Olá",
            conversation_id=uuid4(),
            conversation_history=[],
        )

        assert response == AgentResponse(response="Resposta direta", next_agent=None)
        mock_factory.create_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_route_passes_conversation_history_to_agent(self) -> None:
        """Router should pass conversation_history to delegated agent."""
        mock_factory = Mock()
        orchestrator = AsyncMock()
        orchestrator.set_trace_context = Mock()
        orchestrator._build_context = AsyncMock(
            return_value={"profile": {"onboarding_status": "COMPLETED"}}
        )
        advisor_agent = AsyncMock()
        advisor_agent.set_trace_context = Mock()

        orchestrator.process = AsyncMock(
            return_value=AgentResponse(response=None, next_agent="advisor")
        )
        advisor_agent.process = AsyncMock(return_value=AgentResponse(response="Ok"))

        mock_factory.create_orchestrator.return_value = orchestrator
        mock_factory.create_agent.return_value = advisor_agent

        router = AgentRouter(agent_factory=mock_factory)

        history = [
            {"role": "assistant", "content": "Oi!"},
            {"role": "user", "content": "Tudo bem?"},
        ]

        await router.route(
            user_id=uuid4(),
            message="Me ajuda?",
            conversation_id=uuid4(),
            conversation_history=history,
        )

        call_kwargs = advisor_agent.process.call_args.kwargs
        assert call_kwargs["conversation_history"] == history
