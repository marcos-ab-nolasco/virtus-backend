"""Factory for creating agents with their dependencies."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.advisor import AdvisorAgent
from src.agents.onboarding import OnboardingAgent
from src.agents.orchestrator import OrchestratorAgent
from src.tools.examples.get_calendar_events import GetCalendarEventsTool
from src.tools.examples.get_current_date import GetCurrentDateTool
from src.tools.examples.get_user_preferences import GetUserPreferencesTool
from src.tools.onboarding_tools import (
    CompleteOnboardingStepTool,
    SaveUserPreferencesTool,
    SaveUserProfileTool,
)
from src.tools.registry import ToolRegistry


class AgentFactory:
    """Creates agents and ensures their tool registries are configured."""

    def __init__(
        self,
        *,
        db_session: AsyncSession,
        llm_service: Any,
        context_service: Any,
    ) -> None:
        self._db = db_session
        self._llm = llm_service
        self._context = context_service

    def _build_registry_for_onboarding(self) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(SaveUserProfileTool(db_session=self._db))
        registry.register(SaveUserPreferencesTool(db_session=self._db))
        registry.register(CompleteOnboardingStepTool(db_session=self._db))
        return registry

    def _build_registry_for_advisor(self) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(GetCurrentDateTool())
        registry.register(GetUserPreferencesTool())
        registry.register(GetCalendarEventsTool())
        return registry

    def create_orchestrator(self) -> OrchestratorAgent:
        registry = ToolRegistry()
        return OrchestratorAgent(
            llm_service=self._llm,
            tool_registry=registry,
            context_service=self._context,
        )

    def create_agent(self, agent_name: str):
        if agent_name == "onboarding":
            registry = self._build_registry_for_onboarding()
            return OnboardingAgent(
                llm_service=self._llm,
                tool_registry=registry,
            )

        if agent_name == "advisor":
            registry = self._build_registry_for_advisor()
            return AdvisorAgent(
                llm_service=self._llm,
                tool_registry=registry,
            )

        raise ValueError(f"Unknown agent: {agent_name}")
