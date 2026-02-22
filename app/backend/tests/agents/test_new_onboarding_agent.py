"""Tests for the new deep OnboardingAgent (5-phase conversational flow)."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from src.agents.base import AgentResponse, BaseAgent
from src.agents.onboarding import ONBOARDING_PHASES, OnboardingAgent
from src.services.ai.base import BaseAIService
from src.tools.registry import ToolRegistry


def make_context(
    current_step: str | None = None,
    preferred_name: str | None = None,
    user_id: str = "test-user-id",
    onboarding_status: str = "IN_PROGRESS",
) -> dict[str, Any]:
    return {
        "user": {
            "id": user_id,
            "full_name": "Test User",
            "email": "test@example.com",
        },
        "profile": {
            "onboarding_status": onboarding_status,
            "onboarding_current_step": current_step,
            "preferred_name": preferred_name,
            "onboarding_data": {},
        },
        "preferences": {
            "timezone": "America/Sao_Paulo",
        },
    }


class TestNewOnboardingAgentPhaseManagement:
    """Test phase management in the new OnboardingAgent."""

    def setup_method(self) -> None:
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.agent = OnboardingAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
        )

    def test_get_current_phase_defaults_to_phase_1(self) -> None:
        """Should return 'phase_1' when no step is set."""
        context = make_context(current_step=None)
        assert self.agent.get_current_phase(context) == "phase_1"

    def test_get_current_phase_reads_from_context(self) -> None:
        """Should return the phase stored in context."""
        for phase in ONBOARDING_PHASES:
            context = make_context(current_step=phase)
            assert self.agent.get_current_phase(context) == phase

    def test_get_current_phase_defaults_for_invalid_step(self) -> None:
        """Should return 'phase_1' for unknown step values."""
        context = make_context(current_step="intro")  # old-style step
        assert self.agent.get_current_phase(context) == "phase_1"

    def test_agent_is_base_agent(self) -> None:
        assert isinstance(self.agent, BaseAgent)

    def test_agent_name_is_onboarding(self) -> None:
        assert self.agent.name == "onboarding"

    def test_agent_has_6_tools(self) -> None:
        tools = self.agent.available_tools
        assert "save_life_area_scores" in tools
        assert "save_onboarding_insight" in tools
        assert "save_annual_goal" in tools
        assert "save_monthly_objective" in tools
        assert "save_weekly_priority" in tools
        assert "advance_phase" in tools

    def test_agent_has_deep_onboarding_skill(self) -> None:
        assert "onboarding/deep_onboarding" in self.agent.skills


class TestNewOnboardingAgentProcess:
    """Test the process method of the new OnboardingAgent."""

    def setup_method(self) -> None:
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.mock_registry.get_tool.return_value = None

        skills_path = Path(__file__).parent.parent.parent / "src" / "skills"
        self.agent = OnboardingAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=skills_path,
        )

    @pytest.mark.asyncio
    async def test_process_returns_phase_metadata(self) -> None:
        """Process should include current_phase and phase_name in metadata."""
        self.mock_llm.generate_response_with_tools = AsyncMock(
            return_value={
                "content": "Vamos começar pelo diagnóstico!",
                "tool_calls": None,
                "finish_reason": "stop",
            }
        )

        context = make_context(current_step="phase_1")
        response = await self.agent.process(
            message="Olá, quero começar",
            user_context=context,
            conversation_history=[],
        )

        assert isinstance(response, AgentResponse)
        assert response.metadata.get("current_phase") == "phase_1"
        assert response.metadata.get("phase_name") == "Diagnóstico"

    @pytest.mark.asyncio
    async def test_process_returns_correct_phase_name_for_phase_2(self) -> None:
        """Metadata should reflect phase 2 name."""
        self.mock_llm.generate_response_with_tools = AsyncMock(
            return_value={
                "content": "O que te energiza?",
                "tool_calls": None,
                "finish_reason": "stop",
            }
        )

        context = make_context(current_step="phase_2")
        response = await self.agent.process(
            message="Fase 2",
            user_context=context,
            conversation_history=[],
        )

        assert response.metadata.get("phase_name") == "Direção e propósito"

    @pytest.mark.asyncio
    async def test_process_handles_errors_gracefully(self) -> None:
        """Should return a user-friendly message on LLM errors."""
        self.mock_llm.generate_response_with_tools = AsyncMock(side_effect=Exception("LLM failure"))

        context = make_context(current_step="phase_1")
        response = await self.agent.process(
            message="Teste",
            user_context=context,
            conversation_history=[],
        )

        assert isinstance(response, AgentResponse)
        assert "error" in response.metadata
        assert response.response is not None

    @pytest.mark.asyncio
    async def test_process_defaults_to_phase_1_when_no_step(self) -> None:
        """Should operate in phase_1 when step is not set."""
        self.mock_llm.generate_response_with_tools = AsyncMock(
            return_value={
                "content": "Bem-vindo!",
                "tool_calls": None,
                "finish_reason": "stop",
            }
        )

        context = make_context(current_step=None, onboarding_status="NOT_STARTED")
        response = await self.agent.process(
            message="START",
            user_context=context,
            conversation_history=[],
        )

        assert response.metadata.get("current_phase") == "phase_1"
