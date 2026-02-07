"""Tests for OrchestratorAgent routing decisions."""

from unittest.mock import AsyncMock

import pytest

from src.agents.base import AgentResponse
from src.agents.orchestrator import OrchestratorAgent
from src.tools.registry import ToolRegistry


def get_completed_onboarding_context(user_id: str = "test-user") -> dict:
    """Return context for user with completed onboarding."""
    return {
        "user": {"id": user_id, "full_name": "Test User", "email": "test@example.com"},
        "profile": {
            "onboarding_status": "COMPLETED",
            "onboarding_current_step": None,
            "preferred_name": None,
        },
        "preferences": {
            "timezone": "UTC",
            "contact_frequency": "SOMETIMES",
            "communication_style": "DIRECT",
        },
    }


class TestOrchestratorAgent:
    """Test OrchestratorAgent core routing behavior."""

    def setup_method(self):
        """Setup orchestrator with mocked dependencies."""
        self.registry = ToolRegistry()
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            context_service=self.mock_context,
        )

    @pytest.mark.asyncio
    async def test_process_routes_to_advisor_when_onboarding_complete(self):
        """Should set next_agent to advisor when onboarding is completed."""
        response = await self.orchestrator.process(
            message="Hello",
            user_context=get_completed_onboarding_context(),
            conversation_history=[],
        )

        assert isinstance(response, AgentResponse)
        assert response.next_agent == "advisor"

    @pytest.mark.asyncio
    async def test_process_routes_to_onboarding_when_not_completed(self):
        """Should set next_agent to onboarding when not completed."""
        response = await self.orchestrator.process(
            message="Oi",
            user_context={"profile": {"onboarding_status": "NOT_STARTED"}},
            conversation_history=[],
        )

        assert isinstance(response, AgentResponse)
        assert response.next_agent == "onboarding"
