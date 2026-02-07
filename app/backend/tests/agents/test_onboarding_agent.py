"""
Tests for OnboardingAgent.

Tests the Express Onboarding flow including step management,
skill loading, and tool invocation.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from src.agents.base import AgentResponse, BaseAgent
from src.agents.onboarding import ONBOARDING_STEPS, OnboardingAgent
from src.services.ai.base import BaseAIService
from src.tools.base import ToolResult
from src.tools.registry import ToolRegistry


def get_onboarding_context(
    step: str | None = None,
    preferred_name: str | None = None,
    user_id: str = "test-user-id",
    full_name: str = "Test User",
) -> dict[str, Any]:
    """Create a mock context for onboarding tests."""
    return {
        "user": {
            "id": user_id,
            "full_name": full_name,
            "email": "test@example.com",
        },
        "profile": {
            "onboarding_status": "IN_PROGRESS",
            "onboarding_current_step": step,
            "preferred_name": preferred_name,
        },
        "preferences": {
            "timezone": "UTC",
            "contact_frequency": "SOMETIMES",
        },
    }


class TestOnboardingAgentBasics:
    """Test basic OnboardingAgent functionality."""

    def setup_method(self) -> None:
        """Setup for each test."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.agent = OnboardingAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
        )

    def test_onboarding_agent_is_base_agent(self) -> None:
        """OnboardingAgent should inherit from BaseAgent."""
        assert isinstance(self.agent, BaseAgent)

    def test_onboarding_agent_has_name(self) -> None:
        """OnboardingAgent should have name 'onboarding'."""
        assert self.agent.name == "onboarding"

    def test_onboarding_agent_has_skills(self) -> None:
        """OnboardingAgent should have required skills."""
        skills = self.agent.skills
        assert "shared/persona_base" in skills
        assert "onboarding/onboarding_express" in skills
        assert "onboarding/extracao_preferencias" in skills

    def test_onboarding_agent_has_available_tools(self) -> None:
        """OnboardingAgent should have the right tools available."""
        tools = self.agent.available_tools
        assert "save_user_profile" in tools
        assert "save_user_preferences" in tools
        assert "complete_onboarding_step" in tools


class TestOnboardingStepManagement:
    """Test step management functionality."""

    def setup_method(self) -> None:
        """Setup for each test."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.agent = OnboardingAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
        )

    def test_get_current_step_default_intro(self) -> None:
        """Should default to 'intro' when no step is set."""
        context = get_onboarding_context(step=None)
        assert self.agent.get_current_step(context) == "intro"

    def test_get_current_step_from_context(self) -> None:
        """Should return the step from context."""
        context = get_onboarding_context(step="frequency")
        assert self.agent.get_current_step(context) == "frequency"

    def test_get_current_step_invalid_defaults_to_intro(self) -> None:
        """Should default to 'intro' for invalid step."""
        context = get_onboarding_context(step="invalid_step")
        assert self.agent.get_current_step(context) == "intro"

    def test_get_next_step_from_intro(self) -> None:
        """Next step after intro should be name."""
        assert self.agent.get_next_step("intro") == "name"

    def test_get_next_step_from_name(self) -> None:
        """Next step after name should be frequency."""
        assert self.agent.get_next_step("name") == "frequency"

    def test_get_next_step_follows_order(self) -> None:
        """Steps should follow the defined order."""
        for i, step in enumerate(ONBOARDING_STEPS[:-1]):
            next_step = self.agent.get_next_step(step)
            assert next_step == ONBOARDING_STEPS[i + 1]

    def test_get_next_step_from_closing_returns_none(self) -> None:
        """Next step after closing should be None."""
        assert self.agent.get_next_step("closing") is None

    def test_get_next_step_invalid_returns_intro(self) -> None:
        """Invalid step should return 'intro'."""
        assert self.agent.get_next_step("invalid") == "intro"


class TestOnboardingUserName:
    """Test user name extraction."""

    def setup_method(self) -> None:
        """Setup for each test."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.agent = OnboardingAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
        )

    def test_get_user_name_preferred(self) -> None:
        """Should return preferred_name when available."""
        context = get_onboarding_context(preferred_name="Zé", full_name="José Silva")
        assert self.agent.get_user_name(context) == "Zé"

    def test_get_user_name_first_name(self) -> None:
        """Should return first name when no preferred_name."""
        context = get_onboarding_context(preferred_name=None, full_name="José Silva")
        assert self.agent.get_user_name(context) == "José"

    def test_get_user_name_empty_when_no_data(self) -> None:
        """Should return empty string when no name data."""
        context = {"user": {}, "profile": {}}
        assert self.agent.get_user_name(context) == ""


class TestOnboardingSkillsLoading:
    """Test that onboarding skills load correctly."""

    def setup_method(self) -> None:
        """Setup for each test."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)

        # Use actual skills path
        skills_path = Path(__file__).parent.parent.parent / "src" / "skills"

        self.agent = OnboardingAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=skills_path,
        )

    def test_can_load_skills(self) -> None:
        """Should load all declared skills."""
        content = self.agent.load_skills()

        assert len(content) > 0
        assert "Virtus" in content  # From persona_base
        assert "INTRO" in content or "intro" in content.lower()  # From onboarding_express

    def test_build_system_prompt_includes_skills(self) -> None:
        """System prompt should include skill content."""
        context = get_onboarding_context()
        prompt = self.agent.build_system_prompt(context)

        assert "Virtus" in prompt
        assert len(prompt) > 100


class TestOnboardingProcess:
    """Test the process method."""

    def setup_method(self) -> None:
        """Setup for each test."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.mock_registry.get_tool.return_value = None

        # Use actual skills path
        skills_path = Path(__file__).parent.parent.parent / "src" / "skills"

        self.agent = OnboardingAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=skills_path,
        )

    @pytest.mark.asyncio
    async def test_process_returns_agent_response(self) -> None:
        """Process should return AgentResponse."""
        self.mock_llm.generate_response_with_tools = AsyncMock(
            return_value={
                "content": "Olá! Bem-vindo ao Virtus!",
                "tool_calls": None,
                "finish_reason": "stop",
            }
        )

        context = get_onboarding_context(step="intro")
        response = await self.agent.process(
            message="Oi",
            user_context=context,
            conversation_history=[],
        )

        assert isinstance(response, AgentResponse)
        assert response.response is not None

    @pytest.mark.asyncio
    async def test_process_includes_current_step_in_metadata(self) -> None:
        """Process should include step info in metadata."""
        self.mock_llm.generate_response_with_tools = AsyncMock(
            return_value={
                "content": "Response",
                "tool_calls": None,
                "finish_reason": "stop",
            }
        )

        context = get_onboarding_context(step="name")
        response = await self.agent.process(
            message="Test",
            user_context=context,
            conversation_history=[],
        )

        assert response.metadata.get("current_step") == "name"
        assert response.metadata.get("next_step") == "frequency"

    @pytest.mark.asyncio
    async def test_process_handles_tool_calls(self) -> None:
        """Process should handle tool calls from LLM."""
        tool = AsyncMock()
        tool.execute = AsyncMock(return_value=ToolResult(success=True, data={"saved": True}))
        self.mock_registry.get_tool.return_value = tool

        self.mock_llm.generate_response_with_tools = AsyncMock(
            side_effect=[
                {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "name": "save_user_profile",
                            "arguments": {"user_id": "test", "preferred_name": "Zé"},
                        }
                    ],
                    "finish_reason": "tool_calls",
                },
                {
                    "content": "Vou salvar seu nome preferido.",
                    "tool_calls": None,
                    "finish_reason": "stop",
                },
            ]
        )

        context = get_onboarding_context(step="name")
        response = await self.agent.process(
            message="Pode me chamar de Zé",
            user_context=context,
            conversation_history=[],
        )

        assert response.response == "Vou salvar seu nome preferido."
        assert response.tool_calls is None
        assert self.mock_llm.generate_response_with_tools.call_count == 2

    @pytest.mark.asyncio
    async def test_process_handles_errors_gracefully(self) -> None:
        """Process should handle errors gracefully."""
        self.mock_llm.generate_response_with_tools = AsyncMock(side_effect=Exception("LLM Error"))

        context = get_onboarding_context(step="intro")
        response = await self.agent.process(
            message="Oi",
            user_context=context,
            conversation_history=[],
        )

        assert isinstance(response, AgentResponse)
        assert response.response is not None
        assert "error" in response.metadata


class TestOnboardingStepInstructions:
    """Test step-specific instruction generation."""

    def setup_method(self) -> None:
        """Setup for each test."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.agent = OnboardingAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
        )

    def test_intro_instructions_mention_first_interaction(self) -> None:
        """Intro instructions should mention first interaction."""
        instructions = self.agent._get_step_instructions("intro", "Test", "user-123")
        assert "primeira" in instructions.lower() or "intro" in instructions.lower()

    def test_name_instructions_mention_preferred_name(self) -> None:
        """Name instructions should mention preferred_name."""
        instructions = self.agent._get_step_instructions("name", "Test", "user-123")
        assert "preferred_name" in instructions or "nome" in instructions.lower()

    def test_frequency_instructions_mention_obligatory(self) -> None:
        """Frequency instructions should mention it's obligatory."""
        instructions = self.agent._get_step_instructions("frequency", "Test", "user-123")
        assert "obrigatóri" in instructions.lower()

    def test_closing_instructions_mention_completed(self) -> None:
        """Closing instructions should mention completing onboarding."""
        instructions = self.agent._get_step_instructions("closing", "Test", "user-123")
        assert "completed" in instructions.lower() or "finaliz" in instructions.lower()
