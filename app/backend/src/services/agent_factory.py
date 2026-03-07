"""Factory for creating agents with their dependencies."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.advisor import AdvisorAgent
from src.agents.onboarding import OnboardingAgent
from src.agents.orchestrator import OrchestratorAgent
from src.agents.setup import SetupAgent
from src.tools.examples.get_calendar_events import GetCalendarEventsTool
from src.tools.examples.get_current_date import GetCurrentDateTool
from src.tools.examples.get_user_preferences import GetUserPreferencesTool
from src.tools.onboarding_tools import (
    AdvancePhaseTool,
    SaveAnnualGoalTool,
    SaveLifeAreaScoresTool,
    SaveMonthlyObjectiveTool,
    SaveOnboardingInsightTool,
    SaveWeeklyPriorityTool,
)
from src.tools.registry import ToolRegistry
from src.tools.setup_tools import CompleteSetupTool, SaveUserPreferencesTool, SaveUserProfileTool


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
        self._registries: dict[str, ToolRegistry] = {}

    def _get_registry(self, agent_name: str) -> ToolRegistry:
        registry = self._registries.get(agent_name)
        if registry is not None:
            return registry

        registry = ToolRegistry()
        if agent_name == "setup":
            registry.register(SaveUserProfileTool(db_session=self._db))
            registry.register(SaveUserPreferencesTool(db_session=self._db))
            registry.register(CompleteSetupTool(db_session=self._db))
        elif agent_name == "onboarding":
            registry.register(SaveLifeAreaScoresTool(db_session=self._db))
            registry.register(SaveOnboardingInsightTool(db_session=self._db))
            registry.register(SaveAnnualGoalTool(db_session=self._db))
            registry.register(SaveMonthlyObjectiveTool(db_session=self._db))
            registry.register(SaveWeeklyPriorityTool(db_session=self._db))
            registry.register(AdvancePhaseTool(db_session=self._db))
        elif agent_name == "advisor":
            registry.register(GetCurrentDateTool())
            registry.register(GetUserPreferencesTool())
            registry.register(GetCalendarEventsTool())

        self._registries[agent_name] = registry
        return registry

    def create_orchestrator(self) -> OrchestratorAgent:
        registry = ToolRegistry()
        return OrchestratorAgent(
            llm_service=self._llm,
            tool_registry=registry,
            context_service=self._context,
        )

    def create_agent(self, agent_name: str) -> SetupAgent | OnboardingAgent | AdvisorAgent:
        if agent_name == "setup":
            registry = self._get_registry(agent_name)
            return SetupAgent(
                llm_service=self._llm,
                tool_registry=registry,
            )

        if agent_name == "onboarding":
            registry = self._get_registry(agent_name)
            return OnboardingAgent(
                llm_service=self._llm,
                tool_registry=registry,
            )

        if agent_name == "advisor":
            registry = self._get_registry(agent_name)
            return AdvisorAgent(
                llm_service=self._llm,
                tool_registry=registry,
            )

        raise ValueError(f"Unknown agent: {agent_name}")
