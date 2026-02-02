"""
Tests for Orchestrator Agent with BaseAgent refactoring.

Tests the new skills-based architecture and onboarding detection.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.agents.actions import Action, ActionType
from src.agents.base import BaseAgent
from src.agents.orchestrator import OrchestratorAgent
from src.tools.base import ToolResult
from src.tools.examples.get_current_date import GetCurrentDateTool
from src.tools.executor import ToolExecutor
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


def get_incomplete_onboarding_context(user_id: str = "test-user") -> dict:
    """Return context for user with incomplete onboarding."""
    return {
        "user": {"id": user_id, "full_name": "Test User", "email": "test@example.com"},
        "profile": {
            "onboarding_status": "NOT_STARTED",
            "onboarding_current_step": None,
            "preferred_name": None,
        },
        "preferences": {
            "timezone": "UTC",
            "contact_frequency": "SOMETIMES",
        },
    }


class TestOrchestratorInheritsBaseAgent:
    """Test that OrchestratorAgent properly inherits from BaseAgent."""

    def setup_method(self):
        """Setup orchestrator with mocked dependencies."""
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            tool_executor=self.executor,
            context_service=self.mock_context,
        )

    def test_orchestrator_is_base_agent(self):
        """OrchestratorAgent should inherit from BaseAgent."""
        assert isinstance(self.orchestrator, BaseAgent)

    def test_orchestrator_has_name_property(self):
        """OrchestratorAgent should have name property."""
        assert self.orchestrator.name == "orchestrator"

    def test_orchestrator_has_skills_property(self):
        """OrchestratorAgent should have skills property."""
        skills = self.orchestrator.skills
        assert isinstance(skills, list)
        assert len(skills) > 0
        assert "shared/persona_base" in skills
        assert "orchestrator/classificacao_intencao" in skills

    def test_orchestrator_has_available_tools_property(self):
        """OrchestratorAgent should have available_tools property."""
        tools = self.orchestrator.available_tools
        assert isinstance(tools, list)


class TestOrchestratorOnboardingDetection:
    """Test that orchestrator correctly detects onboarding needs."""

    def setup_method(self):
        """Setup orchestrator with mocked dependencies."""
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            tool_executor=self.executor,
            context_service=self.mock_context,
        )

    def test_should_route_to_onboarding_when_not_started(self):
        """Should return True when onboarding not started."""
        context = get_incomplete_onboarding_context()
        assert self.orchestrator.should_route_to_onboarding(context) is True

    def test_should_route_to_onboarding_when_in_progress(self):
        """Should return True when onboarding in progress."""
        context = get_incomplete_onboarding_context()
        context["profile"]["onboarding_status"] = "IN_PROGRESS"
        assert self.orchestrator.should_route_to_onboarding(context) is True

    def test_should_not_route_to_onboarding_when_completed(self):
        """Should return False when onboarding completed."""
        context = get_completed_onboarding_context()
        assert self.orchestrator.should_route_to_onboarding(context) is False

    def test_should_route_to_onboarding_when_no_profile(self):
        """Should return True when profile is missing."""
        context = {"user": {"id": "test"}}
        assert self.orchestrator.should_route_to_onboarding(context) is True

    @pytest.mark.asyncio
    async def test_process_message_returns_onboarding_message_when_needed(self):
        """Should return onboarding message when user hasn't completed onboarding."""
        self.mock_context.build_permanent_context = AsyncMock(
            return_value=get_incomplete_onboarding_context()
        )

        response = await self.orchestrator.process_message(
            user_id=uuid4(),
            message="Hello",
            conversation_id=uuid4(),
        )

        assert isinstance(response, str)
        assert "perguntas" in response.lower() or "conhecer" in response.lower()
        assert "vamos" in response.lower()

    @pytest.mark.asyncio
    async def test_process_message_uses_preferred_name_in_onboarding(self):
        """Should use preferred_name in onboarding message if available."""
        context = get_incomplete_onboarding_context()
        context["profile"]["preferred_name"] = "Zé"
        self.mock_context.build_permanent_context = AsyncMock(return_value=context)

        response = await self.orchestrator.process_message(
            user_id=uuid4(),
            message="Hello",
            conversation_id=uuid4(),
        )

        assert "Zé" in response


class TestOrchestratorDirectResponse:
    """Test orchestrator direct response (for completed onboarding)."""

    def setup_method(self):
        """Setup orchestrator with mocked dependencies."""
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.registry.register(GetCurrentDateTool())
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            tool_executor=self.executor,
            context_service=self.mock_context,
        )

    @pytest.mark.asyncio
    async def test_process_message_direct_response(self):
        """Should handle direct response when onboarding is complete."""
        self.mock_context.build_permanent_context = AsyncMock(
            return_value=get_completed_onboarding_context()
        )
        self.mock_llm.generate_response = AsyncMock(return_value="I'm doing well, thank you!")

        response = await self.orchestrator.process_message(
            user_id=uuid4(),
            message="Hello, how are you?",
            conversation_id=uuid4(),
        )

        assert isinstance(response, str)
        assert response == "I'm doing well, thank you!"

    @pytest.mark.asyncio
    async def test_process_message_with_tool_invocation(self):
        """Should invoke tool when keyword matches."""
        self.mock_context.build_permanent_context = AsyncMock(
            return_value=get_completed_onboarding_context()
        )
        self.mock_llm.generate_response = AsyncMock(
            return_value="The current time is 2024-01-11T10:30:00+00:00"
        )

        response = await self.orchestrator.process_message(
            user_id=uuid4(),
            message="What time is it?",
            conversation_id=uuid4(),
        )

        assert isinstance(response, str)
        assert len(response) > 0


class TestOrchestratorSkillsLoading:
    """Test that orchestrator loads skills correctly."""

    def setup_method(self):
        """Setup orchestrator with real skills path."""
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        # Use actual skills path
        skills_path = Path(__file__).parent.parent.parent / "src" / "skills"

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            tool_executor=self.executor,
            context_service=self.mock_context,
            skills_path=skills_path,
        )

    def test_can_load_skills(self):
        """Should be able to load all declared skills."""
        content = self.orchestrator.load_skills()

        assert len(content) > 0
        assert "Virtus" in content  # From persona_base
        assert "ContactFrequency" in content or "RARELY" in content  # From tom_ajuste

    def test_build_system_prompt_includes_skills(self):
        """System prompt should include loaded skills."""
        context = get_completed_onboarding_context()
        prompt = self.orchestrator.build_system_prompt(context)

        # Should include skill content
        assert "Virtus" in prompt

        # Should include user context
        assert "test-user" in prompt or "Test User" in prompt


class TestOrchestratorErrorHandling:
    """Test orchestrator error handling."""

    def setup_method(self):
        """Setup orchestrator."""
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            tool_executor=self.executor,
            context_service=self.mock_context,
        )

    @pytest.mark.asyncio
    async def test_handles_llm_failure_gracefully(self):
        """Should handle LLM failure gracefully."""
        self.mock_context.build_permanent_context = AsyncMock(
            return_value=get_completed_onboarding_context()
        )
        self.mock_llm.generate_response = AsyncMock(side_effect=Exception("LLM API error"))

        response = await self.orchestrator.process_message(
            user_id=uuid4(),
            message="Test",
            conversation_id=uuid4(),
        )

        # Should return error message instead of crashing
        assert isinstance(response, str)
        assert "desculpe" in response.lower() or "dificuldade" in response.lower()

    @pytest.mark.asyncio
    async def test_handles_context_failure(self):
        """Should handle context building failure."""
        self.mock_context.build_permanent_context = AsyncMock(
            side_effect=Exception("DB error")
        )

        response = await self.orchestrator.process_message(
            user_id=uuid4(),
            message="Test",
            conversation_id=uuid4(),
        )

        # Should still return a response (onboarding message due to missing context)
        assert isinstance(response, str)


class TestOrchestratorActions:
    """Test orchestrator action decisions."""

    def setup_method(self):
        """Setup orchestrator."""
        self.registry = ToolRegistry()
        self.registry.register(GetCurrentDateTool())
        self.executor = ToolExecutor(self.registry)
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            tool_executor=self.executor,
            context_service=self.mock_context,
        )

    @pytest.mark.asyncio
    async def test_decide_action_returns_action(self):
        """_decide_action should return Action object."""
        action = await self.orchestrator._decide_action(
            message="Test message",
            context=get_completed_onboarding_context(),
        )

        assert isinstance(action, Action)
        assert action.type in [ActionType.DIRECT_RESPONSE, ActionType.SKILL_CALL]

    @pytest.mark.asyncio
    async def test_decide_action_tool_call_for_time(self):
        """Should decide to call tool for time-related queries."""
        action = await self.orchestrator._decide_action(
            message="What time is it?",
            context=get_completed_onboarding_context(),
        )

        assert action.type == ActionType.SKILL_CALL
        assert action.skill_name == "get_current_date"

    @pytest.mark.asyncio
    async def test_execute_tool_action(self):
        """Should execute tool and return result."""
        action = Action(
            type=ActionType.SKILL_CALL,
            skill_name="get_current_date",
            skill_args={"timezone": "UTC"},
        )

        result = await self.orchestrator._execute_tool(action)

        assert isinstance(result, ToolResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool_returns_error(self):
        """Should handle non-existent tool gracefully."""
        action = Action(
            type=ActionType.SKILL_CALL,
            skill_name="nonexistent_tool",
            skill_args={},
        )

        result = await self.orchestrator._execute_tool(action)

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert result.error is not None
