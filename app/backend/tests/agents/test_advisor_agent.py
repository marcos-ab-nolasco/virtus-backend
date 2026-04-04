"""Tests for AdvisorAgent (consultor mínimo)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.agents.advisor import AdvisorAgent
from src.agents.base import AgentResponse, BaseAgent
from src.services.ai.base import BaseAIService
from src.tools.advisor.get_inferred_values import GetInferredValuesTool
from src.tools.advisor.get_observed_patterns import GetObservedPatternsTool
from src.tools.advisor.get_user_full_history import GetUserFullHistoryTool
from src.tools.registry import ToolRegistry


class TestAdvisorAgentBasics:
    """Basic AdvisorAgent behavior."""

    def setup_method(self) -> None:
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.agent = AdvisorAgent(llm_service=self.mock_llm, tool_registry=self.mock_registry)

    def test_advisor_inherits_base_agent(self) -> None:
        assert isinstance(self.agent, BaseAgent)

    def test_advisor_has_name(self) -> None:
        assert self.agent.name == "advisor"

    def test_advisor_has_skills(self) -> None:
        skills = self.agent.skills
        assert "shared/persona_base" in skills
        assert "shared/tom_ajuste" in skills
        assert "shared/contexto_usuario" in skills
        assert "advisor/conversacao_livre" in skills


class TestAdvisorAgentProcessing:
    """Ensure advisor can call LLM with tools."""

    def setup_method(self) -> None:
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)

        skills_path = Path(__file__).parent.parent.parent / "src" / "skills"

        self.agent = AdvisorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=skills_path,
        )

    @pytest.mark.asyncio
    async def test_process_returns_agent_response(self) -> None:
        self.mock_llm.generate_response_with_tools = AsyncMock(
            return_value={
                "content": "Posso te ajudar com isso.",
                "tool_calls": None,
                "finish_reason": "stop",
            }
        )

        response = await self.agent.process(
            message="Como você funciona?",
            user_context={"user": {"id": "user-1"}},
            conversation_history=[],
        )

        assert isinstance(response, AgentResponse)
        assert response.response is not None


class TestAdvisorAgentProperties:
    """Verify advisor skills and tools include new additions."""

    def setup_method(self) -> None:
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.agent = AdvisorAgent(llm_service=self.mock_llm, tool_registry=self.mock_registry)

    def test_advisor_has_new_skills(self) -> None:
        skills = self.agent.skills
        assert "advisor/metodologias" in skills
        assert "advisor/geracao_insights" in skills
        assert "advisor/reflexao_profunda" in skills
        assert "advisor/suporte_decisao" in skills

    def test_advisor_has_new_tools(self) -> None:
        tools = self.agent.available_tools
        assert "get_user_full_history" in tools
        assert "get_observed_patterns" in tools
        assert "get_inferred_values" in tools


class TestAdvisorNewTools:
    """Unit tests for new advisor tools using mocked DB."""

    @pytest.mark.asyncio
    async def test_get_user_full_history_partial_data(self) -> None:
        """Returns partial data when user has not completed onboarding."""
        tool = GetUserFullHistoryTool()
        user_id = "00000000-0000-0000-0000-000000000001"

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # All queries return empty results
        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        empty_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=empty_result)

        mock_factory = MagicMock()
        mock_factory.return_value = mock_session

        with patch(
            "src.tools.advisor.get_user_full_history.get_async_sessionmaker",
            return_value=mock_factory,
        ):
            result = await tool.execute({"user_id": user_id})

        assert result.success is True
        assert result.data is not None
        assert result.data["life_areas"] == []
        assert result.data["annual_goals"] == []

    @pytest.mark.asyncio
    async def test_get_observed_patterns_returns_empty_list(self) -> None:
        """Returns empty list when observed_patterns is None."""
        tool = GetObservedPatternsTool()
        user_id = "00000000-0000-0000-0000-000000000001"

        mock_profile = MagicMock()
        mock_profile.observed_patterns = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_profile

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_factory = MagicMock()
        mock_factory.return_value = mock_session

        with patch(
            "src.tools.advisor.get_observed_patterns.get_async_sessionmaker",
            return_value=mock_factory,
        ):
            result = await tool.execute({"user_id": user_id})

        assert result.success is True
        assert result.data == []

    @pytest.mark.asyncio
    async def test_get_inferred_values_no_insight(self) -> None:
        """Returns empty top_values when OnboardingInsight does not exist."""
        tool = GetInferredValuesTool()
        user_id = "00000000-0000-0000-0000-000000000001"

        mock_profile = MagicMock()
        mock_profile.moral_profile = None

        mock_profile_result = MagicMock()
        mock_profile_result.scalar_one_or_none.return_value = mock_profile

        mock_insight_result = MagicMock()
        mock_insight_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(side_effect=[mock_insight_result, mock_profile_result])

        mock_factory = MagicMock()
        mock_factory.return_value = mock_session

        with patch(
            "src.tools.advisor.get_inferred_values.get_async_sessionmaker",
            return_value=mock_factory,
        ):
            result = await tool.execute({"user_id": user_id})

        assert result.success is True
        assert result.data["top_values"] == []
        assert result.data["value_behavior_gap"] is None
