"""
Tests for Orchestrator Agent with BaseAgent refactoring.

Tests the new skills-based architecture and onboarding detection.
"""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.agents.base import AgentResponse, BaseAgent
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
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
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
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
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
    async def test_process_sets_next_agent_onboarding_when_needed(self):
        """Should set next_agent to onboarding when onboarding not complete."""
        self.mock_context.build_permanent_context = AsyncMock(
            return_value=get_incomplete_onboarding_context()
        )

        response = await self.orchestrator.process(
            message="Hello",
            user_context=get_incomplete_onboarding_context(),
            conversation_history=[],
        )

        assert isinstance(response, AgentResponse)
        assert response.next_agent == "onboarding"


class TestOrchestratorSkillsLoading:
    """Test that orchestrator loads skills correctly."""

    def setup_method(self):
        """Setup orchestrator with real skills path."""
        self.registry = ToolRegistry()
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        # Use actual skills path
        skills_path = Path(__file__).parent.parent.parent / "src" / "skills"

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
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


class TestOrchestratorRoutingDecision:
    """Test orchestrator routing decisions."""

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
    async def test_process_sets_next_agent_advisor_when_completed(self):
        """Should set next_agent to advisor when onboarding is complete."""
        response = await self.orchestrator.process(
            message="Hello",
            user_context=get_completed_onboarding_context(),
            conversation_history=[],
        )

        assert isinstance(response, AgentResponse)
        assert response.next_agent == "advisor"
