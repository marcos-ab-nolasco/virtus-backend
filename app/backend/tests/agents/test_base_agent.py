"""
Tests for BaseAgent abstract class

Following TDD approach:
- RED: Write failing tests first
- GREEN: Implement minimal code to pass
- REFACTOR: Clean up and improve
"""

from abc import ABC
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from src.agents.base import AgentResponse, BaseAgent
from src.services.ai.base import BaseAIService
from src.tools.base import BaseTool, ToolResult
from src.tools.registry import ToolRegistry


class ConcreteAgent(BaseAgent):
    """Implementação concreta para testes."""

    @property
    def name(self) -> str:
        return "test_agent"

    @property
    def skills(self) -> list[str]:
        return ["test_skill"]

    @property
    def available_tools(self) -> list[str]:
        return ["test_tool"]


class DummyTool(BaseTool):
    """Tool simples para testes do loop de tools."""

    name = "test_tool"
    description = "Dummy tool"
    parameters = {"type": "object", "properties": {}, "required": []}

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(success=True, data={"value": "ok"})


class TestAgentAbstractProperties:
    """Testes para verificar que propriedades são abstratas."""

    def test_base_agent_is_abstract(self) -> None:
        """BaseAgent deve ser uma classe abstrata."""
        assert issubclass(BaseAgent, ABC)

    def test_cannot_instantiate_base_agent_directly(self) -> None:
        """Não deve ser possível instanciar BaseAgent diretamente."""
        mock_llm = Mock(spec=BaseAIService)
        mock_registry = Mock(spec=ToolRegistry)

        with pytest.raises(TypeError, match="abstract"):
            BaseAgent(llm_service=mock_llm, tool_registry=mock_registry)  # type: ignore[abstract]

    def test_name_is_abstract_property(self) -> None:
        """Propriedade 'name' deve ser abstrata."""
        assert hasattr(BaseAgent, "name")
        assert getattr(BaseAgent.name, "fget", None) is not None

    def test_skills_is_abstract_property(self) -> None:
        """Propriedade 'skills' deve ser abstrata."""
        assert hasattr(BaseAgent, "skills")
        assert getattr(BaseAgent.skills, "fget", None) is not None

    def test_available_tools_is_abstract_property(self) -> None:
        """Propriedade 'available_tools' deve ser abstrata."""
        assert hasattr(BaseAgent, "available_tools")
        assert getattr(BaseAgent.available_tools, "fget", None) is not None


class TestConcreteAgentProperties:
    """Testes para propriedades do agente concreto."""

    def setup_method(self) -> None:
        """Setup para cada teste."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.agent = ConcreteAgent(llm_service=self.mock_llm, tool_registry=self.mock_registry)

    def test_concrete_agent_has_name(self) -> None:
        """Agente concreto deve ter nome."""
        assert self.agent.name == "test_agent"

    def test_concrete_agent_has_skills(self) -> None:
        """Agente concreto deve ter lista de skills."""
        assert self.agent.skills == ["test_skill"]

    def test_concrete_agent_has_available_tools(self) -> None:
        """Agente concreto deve ter lista de tools disponíveis."""
        assert self.agent.available_tools == ["test_tool"]


class TestLoadSkillFile:
    """Testes para carregamento de arquivos de skill."""

    def setup_method(self) -> None:
        """Setup para cada teste."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.test_skills_path = Path(__file__).parent / "test_skills"

    def test_load_skill_file_success(self, tmp_path: Path) -> None:
        """Deve carregar arquivo .md existente."""
        skills_dir = tmp_path / "skills" / "test_skill"
        skills_dir.mkdir(parents=True)
        skill_file = skills_dir / "instructions.md"
        skill_file.write_text("# Test Skill\n\nInstruções do skill de teste.")

        agent = ConcreteAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=tmp_path / "skills",
        )

        content = agent._load_skill_file("test_skill")
        assert "# Test Skill" in content
        assert "Instruções do skill de teste" in content

    def test_load_skill_file_not_found(self, tmp_path: Path) -> None:
        """Deve lançar FileNotFoundError para skill inexistente."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        agent = ConcreteAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=skills_dir,
        )

        with pytest.raises(FileNotFoundError, match="nonexistent_skill"):
            agent._load_skill_file("nonexistent_skill")


class TestLoadSkills:
    """Testes para carregamento de múltiplas skills."""

    def setup_method(self) -> None:
        """Setup para cada teste."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)

    def test_load_skills_concatenates(self, tmp_path: Path) -> None:
        """Deve concatenar múltiplas skills com separador."""
        skills_dir = tmp_path / "skills"

        # Criar skill 1
        skill1_dir = skills_dir / "skill_one"
        skill1_dir.mkdir(parents=True)
        (skill1_dir / "instructions.md").write_text("# Skill One\nConteúdo um.")

        # Criar skill 2
        skill2_dir = skills_dir / "skill_two"
        skill2_dir.mkdir(parents=True)
        (skill2_dir / "instructions.md").write_text("# Skill Two\nConteúdo dois.")

        class MultiSkillAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "multi_skill_agent"

            @property
            def skills(self) -> list[str]:
                return ["skill_one", "skill_two"]

            @property
            def available_tools(self) -> list[str]:
                return []

        agent = MultiSkillAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=skills_dir,
        )

        result = agent.load_skills()

        assert "# Skill One" in result
        assert "# Skill Two" in result
        assert "---" in result  # separador

    def test_load_skills_empty_list(self, tmp_path: Path) -> None:
        """Deve retornar string vazia quando não há skills."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        class NoSkillsAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "no_skills_agent"

            @property
            def skills(self) -> list[str]:
                return []

            @property
            def available_tools(self) -> list[str]:
                return []

        agent = NoSkillsAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=skills_dir,
        )

        result = agent.load_skills()
        assert result == ""


class TestBuildSystemPrompt:
    """Testes para construção do system prompt."""

    def setup_method(self) -> None:
        """Setup para cada teste."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)

    def test_build_system_prompt_structure(self, tmp_path: Path) -> None:
        """System prompt deve incluir skills + contexto + instruções."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "test_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "instructions.md").write_text("# Test Skill\nInstruções aqui.")

        agent = ConcreteAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=skills_dir,
        )

        user_context = {"user_name": "João", "preference": "formal"}
        prompt = agent.build_system_prompt(user_context)

        # Deve conter o conteúdo da skill
        assert "Test Skill" in prompt
        # Deve conter o contexto
        assert "João" in prompt or "user_name" in prompt

    def test_build_system_prompt_with_empty_context(self, tmp_path: Path) -> None:
        """Deve funcionar com contexto vazio."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "test_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "instructions.md").write_text("# Test Skill")

        agent = ConcreteAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=skills_dir,
        )

        prompt = agent.build_system_prompt({})
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestFormatContext:
    """Testes para formatação de contexto."""

    def setup_method(self) -> None:
        """Setup para cada teste."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.agent = ConcreteAgent(llm_service=self.mock_llm, tool_registry=self.mock_registry)

    def test_format_context_with_data(self) -> None:
        """Deve formatar contexto com dados."""
        context = {"user_name": "Maria", "role": "admin"}
        result = self.agent._format_context(context)

        assert "user_name" in result or "Maria" in result
        assert isinstance(result, str)

    def test_format_context_handles_empty(self) -> None:
        """Contexto vazio deve retornar string apropriada."""
        result = self.agent._format_context({})
        assert isinstance(result, str)


class TestGetToolDefinitions:
    """Testes para obtenção de definições de tools."""

    def setup_method(self) -> None:
        """Setup para cada teste."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = ToolRegistry()

    def test_get_tool_definitions_filters_by_available(self) -> None:
        """Só deve retornar tools do available_tools."""

        # Criar tool mock
        class MockTool(BaseTool):
            name = "test_tool"
            description = "Tool de teste"
            parameters: dict[str, Any] = {"type": "object", "properties": {}}

            async def execute(self, args: dict[str, Any]) -> Any:
                pass

        class AnotherTool(BaseTool):
            name = "another_tool"
            description = "Outra tool"
            parameters: dict[str, Any] = {"type": "object", "properties": {}}

            async def execute(self, args: dict[str, Any]) -> Any:
                pass

        self.mock_registry.register(MockTool())
        self.mock_registry.register(AnotherTool())

        agent = ConcreteAgent(llm_service=self.mock_llm, tool_registry=self.mock_registry)

        definitions = agent._get_tool_definitions()

        # Só deve ter test_tool (que está em available_tools)
        assert len(definitions) == 1
        assert definitions[0]["function"]["name"] == "test_tool"

    def test_get_tool_definitions_empty_when_no_tools(self) -> None:
        """Deve retornar lista vazia quando não há tools disponíveis."""

        class NoToolsAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "no_tools_agent"

            @property
            def skills(self) -> list[str]:
                return []

            @property
            def available_tools(self) -> list[str]:
                return []

        agent = NoToolsAgent(llm_service=self.mock_llm, tool_registry=self.mock_registry)

        definitions = agent._get_tool_definitions()
        assert definitions == []


class TestAgentResponse:
    """Testes para dataclass AgentResponse."""

    def test_create_response_with_text(self) -> None:
        """Deve criar resposta com texto."""
        response = AgentResponse(response="Olá, como posso ajudar?")
        assert response.response == "Olá, como posso ajudar?"
        assert response.tool_calls is None
        assert response.next_agent is None
        assert response.metadata == {}

    def test_create_response_with_tool_calls(self) -> None:
        """Deve criar resposta com tool calls."""
        tool_calls = [{"name": "get_date", "arguments": {"timezone": "UTC"}}]
        response = AgentResponse(response=None, tool_calls=tool_calls)

        assert response.response is None
        assert response.tool_calls == tool_calls

    def test_create_response_with_next_agent(self) -> None:
        """Deve criar resposta com redirecionamento para outro agente."""
        response = AgentResponse(response="Redirecionando...", next_agent="specialist_agent")
        assert response.next_agent == "specialist_agent"

    def test_create_response_with_metadata(self) -> None:
        """Deve criar resposta com metadados."""
        metadata = {"confidence": 0.95, "tokens_used": 150}
        response = AgentResponse(response="Resposta", metadata=metadata)
        assert response.metadata == metadata


class TestProcess:
    """Testes para método process."""

    def setup_method(self) -> None:
        """Setup para cada teste."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)

    @pytest.mark.asyncio
    async def test_process_calls_llm_with_tools(self, tmp_path: Path) -> None:
        """Process deve chamar LLM com tools e retornar AgentResponse."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "test_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "instructions.md").write_text("# Test")

        # Mock LLM response
        self.mock_llm.generate_response_with_tools = AsyncMock(
            return_value={
                "content": "Hello! How can I help you?",
                "tool_calls": None,
                "finish_reason": "stop",
            }
        )

        agent = ConcreteAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=skills_dir,
        )

        response = await agent.process(
            message="Olá", user_context={"user_id": "123"}, conversation_history=[]
        )

        # Verify LLM was called
        self.mock_llm.generate_response_with_tools.assert_called_once()
        call_kwargs = self.mock_llm.generate_response_with_tools.call_args.kwargs

        # Verify system prompt was built
        assert "system_prompt" in call_kwargs
        assert len(call_kwargs["system_prompt"]) > 0

        # Verify messages include user message
        assert "messages" in call_kwargs
        assert call_kwargs["messages"][-1]["content"] == "Olá"

        # Verify tools were passed
        assert "tools" in call_kwargs

        # Verify AgentResponse
        assert response.response == "Hello! How can I help you?"
        assert response.tool_calls is None
        assert response.metadata["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_process_deduplicates_latest_user_message(self, tmp_path: Path) -> None:
        """Process deve evitar duplicar a ultima mensagem do usuario."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "test_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "instructions.md").write_text("# Test")

        captured: dict[str, Any] = {}

        async def capture_call(*, messages, system_prompt, tools):
            captured["messages"] = messages
            return {
                "content": "Ok",
                "tool_calls": None,
                "finish_reason": "stop",
            }

        self.mock_llm.generate_response_with_tools = AsyncMock(side_effect=capture_call)

        agent = ConcreteAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_path=skills_dir,
        )

        history = [
            {"role": "assistant", "content": "Oi!"},
            {"role": "user", "content": "Olá"},
        ]

        await agent.process(
            message="Olá",
            user_context={"user_id": "123"},
            conversation_history=history,
        )

        assert captured["messages"] == history

    @pytest.mark.asyncio
    async def test_process_runs_tool_loop_and_calls_llm_twice(self, tmp_path: Path) -> None:
        """Process deve executar tools e gerar resposta final."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "test_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "instructions.md").write_text("# Test")

        registry = ToolRegistry()
        registry.register(DummyTool())

        agent = ConcreteAgent(
            llm_service=self.mock_llm,
            tool_registry=registry,
            skills_path=skills_dir,
        )

        calls: list[dict[str, Any]] = []

        async def side_effect(*, messages, system_prompt, tools):
            calls.append({"messages": messages, "tools": tools})
            if len(calls) == 1:
                return {
                    "content": None,
                    "tool_calls": [{"id": "call_1", "name": "test_tool", "arguments": {}}],
                    "finish_reason": "tool_calls",
                }
            return {
                "content": "Resultado final",
                "tool_calls": None,
                "finish_reason": "stop",
            }

        self.mock_llm.generate_response_with_tools = AsyncMock(side_effect=side_effect)

        response = await agent.process(
            message="Teste",
            user_context={"user_id": "123"},
            conversation_history=[],
        )

        assert response.response == "Resultado final"
        assert self.mock_llm.generate_response_with_tools.call_count == 2

        second_call = calls[1]["messages"]
        assistant_calls = [msg for msg in second_call if msg.get("role") == "assistant"]
        tool_messages = [msg for msg in second_call if msg.get("role") == "tool"]

        assert assistant_calls, "Expected assistant tool-call message in second call"
        assert tool_messages, "Expected tool result messages in second call"
        assert tool_messages[-1].get("tool_call_id") == "call_1"
        assert "ok" in (tool_messages[-1].get("content") or "")


class TestMultiRoundToolLoop:
    """Tests for multi-round tool calling loop."""

    def setup_method(self) -> None:
        """Setup for each test."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.registry = ToolRegistry()
        self.registry.register(DummyTool())

    def _make_agent(self, tmp_path: Path) -> ConcreteAgent:
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "test_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "instructions.md").write_text("# Test")
        return ConcreteAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            skills_path=skills_dir,
        )

    @pytest.mark.asyncio
    async def test_tool_loop_multi_round_chains_calls(self, tmp_path: Path) -> None:
        """LLM returns tool_calls in rounds 1-2, text in round 3."""
        agent = self._make_agent(tmp_path)
        call_count = 0

        async def side_effect(*, messages: Any, system_prompt: Any, tools: Any) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return {
                    "content": None,
                    "tool_calls": [
                        {"id": f"call_{call_count}", "name": "test_tool", "arguments": {}}
                    ],
                    "finish_reason": "tool_calls",
                }
            return {
                "content": "Final answer",
                "tool_calls": None,
                "finish_reason": "stop",
            }

        self.mock_llm.generate_response_with_tools = AsyncMock(side_effect=side_effect)

        response = await agent.process(message="Test", user_context={}, conversation_history=[])

        assert response.response == "Final answer"
        assert call_count == 3
        assert response.metadata.get("tool_rounds") == 2

    @pytest.mark.asyncio
    async def test_tool_loop_stops_at_max_rounds(self, tmp_path: Path) -> None:
        """LLM always returns tool_calls → max_rounds+1 calls total (last forced text)."""
        agent = self._make_agent(tmp_path)
        call_count = 0

        async def side_effect(*, messages: Any, system_prompt: Any, tools: Any) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if tools:  # Has tools available → return tool calls
                return {
                    "content": None,
                    "tool_calls": [
                        {"id": f"call_{call_count}", "name": "test_tool", "arguments": {}}
                    ],
                    "finish_reason": "tool_calls",
                }
            # Forced text (tools=[])
            return {
                "content": "Forced text",
                "tool_calls": None,
                "finish_reason": "stop",
            }

        self.mock_llm.generate_response_with_tools = AsyncMock(side_effect=side_effect)

        response = await agent.process(message="Test", user_context={}, conversation_history=[])

        assert response.response == "Forced text"
        # 3 rounds of tools + 1 forced text = 4 calls
        assert call_count == 4
        assert response.metadata.get("tool_rounds") == 3

    @pytest.mark.asyncio
    async def test_tool_loop_single_round_backward_compatible(self, tmp_path: Path) -> None:
        """Single round tools + text (current behavior still works)."""
        agent = self._make_agent(tmp_path)
        calls: list[dict[str, Any]] = []

        async def side_effect(*, messages: Any, system_prompt: Any, tools: Any) -> dict[str, Any]:
            calls.append({"tools": tools})
            if len(calls) == 1:
                return {
                    "content": None,
                    "tool_calls": [{"id": "call_1", "name": "test_tool", "arguments": {}}],
                    "finish_reason": "tool_calls",
                }
            return {
                "content": "Done",
                "tool_calls": None,
                "finish_reason": "stop",
            }

        self.mock_llm.generate_response_with_tools = AsyncMock(side_effect=side_effect)

        response = await agent.process(message="Test", user_context={}, conversation_history=[])

        assert response.response == "Done"
        assert len(calls) == 2
        assert response.metadata.get("tool_rounds") == 1

    @pytest.mark.asyncio
    async def test_tool_loop_failed_tool_visible_in_next_round(self, tmp_path: Path) -> None:
        """Tool error in round 1 is visible to LLM in round 2."""

        # Register a failing tool
        class FailingTool(BaseTool):
            name = "test_tool"
            description = "Fails"
            parameters = {"type": "object", "properties": {}, "required": []}

            async def execute(self, args: dict[str, Any]) -> ToolResult:
                return ToolResult(success=False, data=None, error="DB connection failed")

        registry = ToolRegistry()
        registry.register(FailingTool())

        skills_dir = tmp_path / "skills" / "test_skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "instructions.md").write_text("# Test")

        agent = ConcreteAgent(
            llm_service=self.mock_llm,
            tool_registry=registry,
            skills_path=tmp_path / "skills",
        )

        captured_messages: list[Any] = []

        async def side_effect(*, messages: Any, system_prompt: Any, tools: Any) -> dict[str, Any]:
            captured_messages.append(messages)
            if len(captured_messages) == 1:
                return {
                    "content": None,
                    "tool_calls": [{"id": "call_1", "name": "test_tool", "arguments": {}}],
                    "finish_reason": "tool_calls",
                }
            return {
                "content": "Tool failed, sorry",
                "tool_calls": None,
                "finish_reason": "stop",
            }

        self.mock_llm.generate_response_with_tools = AsyncMock(side_effect=side_effect)

        response = await agent.process(message="Test", user_context={}, conversation_history=[])

        assert response.response == "Tool failed, sorry"
        # Second call should have tool messages with error
        second_call_msgs = captured_messages[1]
        tool_msgs = [m for m in second_call_msgs if m.get("role") == "tool"]
        assert any("DB connection failed" in (m.get("content") or "") for m in tool_msgs)

    @pytest.mark.asyncio
    async def test_metadata_tracks_tool_rounds(self, tmp_path: Path) -> None:
        """metadata['tool_rounds'] should reflect number of tool execution rounds."""
        agent = self._make_agent(tmp_path)

        # No tool calls at all
        self.mock_llm.generate_response_with_tools = AsyncMock(
            return_value={
                "content": "No tools needed",
                "tool_calls": None,
                "finish_reason": "stop",
            }
        )

        response = await agent.process(message="Hi", user_context={}, conversation_history=[])

        assert response.metadata.get("tool_rounds") == 0


class TestValidateToolUsage:
    """Tests for post-execution validation."""

    def setup_method(self) -> None:
        """Setup for each test."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.registry = ToolRegistry()
        self.registry.register(DummyTool())

    def _make_agent(self, tmp_path: Path) -> ConcreteAgent:
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "test_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "instructions.md").write_text("# Test")
        return ConcreteAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            skills_path=skills_dir,
        )

    def test_validate_default_returns_none(self, tmp_path: Path) -> None:
        """Default validate_tool_usage should return None (no validation)."""
        agent = self._make_agent(tmp_path)
        result = agent.validate_tool_usage(tool_calls_made=[], user_context={}, message="hello")
        assert result is None

    @pytest.mark.asyncio
    async def test_process_retries_on_validation_failure(self, tmp_path: Path) -> None:
        """When validate returns correction, loop should be called again."""

        class ValidatingAgent(ConcreteAgent):
            validation_call_count = 0

            def validate_tool_usage(
                self,
                tool_calls_made: list[dict[str, Any]],
                user_context: dict[str, Any],
                message: str,
            ) -> str | None:
                self.validation_call_count += 1
                if self.validation_call_count == 1:
                    return "You must call test_tool"
                return None

        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "test_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "instructions.md").write_text("# Test")

        agent = ValidatingAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            skills_path=skills_dir,
        )

        call_count = 0

        async def side_effect(*, messages: Any, system_prompt: Any, tools: Any) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {
                "content": f"Response {call_count}",
                "tool_calls": None,
                "finish_reason": "stop",
            }

        self.mock_llm.generate_response_with_tools = AsyncMock(side_effect=side_effect)

        await agent.process(message="Test", user_context={}, conversation_history=[])

        # Validation called once (initial); retry does NOT re-validate (avoids infinite loop)
        assert agent.validation_call_count == 1
        # LLM called at least twice (initial + retry)
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_process_no_retry_on_validation_pass(self, tmp_path: Path) -> None:
        """When validate returns None, no retry happens."""
        agent = self._make_agent(tmp_path)

        self.mock_llm.generate_response_with_tools = AsyncMock(
            return_value={
                "content": "All good",
                "tool_calls": None,
                "finish_reason": "stop",
            }
        )

        response = await agent.process(message="Test", user_context={}, conversation_history=[])

        assert response.response == "All good"
        assert self.mock_llm.generate_response_with_tools.call_count == 1
