"""Tests for AdvisorAgent (consultor mínimo)."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from src.agents.advisor import AdvisorAgent
from src.agents.base import AgentResponse, BaseAgent
from src.services.ai.base import BaseAIService
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
