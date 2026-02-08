"""
Base Agent - Classe base abstrata para todos os agentes

Define a interface comum que todos os agentes do sistema devem implementar.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.tools.executor import ToolExecutionError, ToolExecutor


@dataclass
class AgentResponse:
    """
    Resposta de um agente após processar uma mensagem.

    Attributes:
        response: Texto de resposta para o usuário (pode ser None se houver tool_calls)
        tool_calls: Lista de chamadas de tools a serem executadas
        next_agent: Nome do próximo agente para delegar (handoff)
        metadata: Metadados adicionais (tokens, confidence, etc.)
    """

    response: str | None
    tool_calls: list[dict[str, Any]] | None = None
    next_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base abstrata para todos os agentes.

    Fornece funcionalidade comum como:
    - Carregamento de skills (arquivos markdown)
    - Construção de system prompts
    - Filtragem de tools disponíveis
    - Interface padrão para processamento

    Subclasses devem implementar as propriedades abstratas:
    - name: Identificador único do agente
    - skills: Lista de skills que o agente utiliza
    - available_tools: Lista de tools que o agente pode usar
    """

    def __init__(
        self,
        llm_service: Any,  # BaseAIService
        tool_registry: Any,  # ToolRegistry
        skills_path: Path | None = None,
    ) -> None:
        """
        Inicializa o agente.

        Args:
            llm_service: Serviço de LLM para geração de respostas
            tool_registry: Registry com tools disponíveis
            skills_path: Caminho para pasta de skills (default: src/skills)
        """
        self.llm = llm_service
        self.tools = tool_registry
        self._skills_path = skills_path or Path(__file__).parent.parent / "skills"

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador único do agente."""
        ...

    @property
    @abstractmethod
    def skills(self) -> list[str]:
        """Lista de skills que o agente utiliza."""
        ...

    @property
    @abstractmethod
    def available_tools(self) -> list[str]:
        """Lista de nomes de tools que o agente pode usar."""
        ...

    def _load_skill_file(self, skill_name: str) -> str:
        """
        Carrega o arquivo de instruções de uma skill.

        Args:
            skill_name: Nome da skill (deve existir como pasta em skills_path)

        Returns:
            Conteúdo do arquivo instructions.md da skill

        Raises:
            FileNotFoundError: Se a skill não existir
        """
        skill_file = self._skills_path / skill_name / "instructions.md"
        if not skill_file.exists():
            raise FileNotFoundError(f"Skill '{skill_name}' não encontrada em {skill_file}")
        return skill_file.read_text(encoding="utf-8")

    def load_skills(self) -> str:
        """
        Carrega e concatena todas as skills do agente.

        Returns:
            String com todas as skills concatenadas, separadas por '---'
        """
        if not self.skills:
            return ""

        skill_contents = []
        for skill_name in self.skills:
            content = self._load_skill_file(skill_name)
            skill_contents.append(content)

        return "\n\n---\n\n".join(skill_contents)

    def _format_context(self, user_context: dict[str, Any]) -> str:
        """
        Formata o contexto do usuário para inclusão no prompt.

        Args:
            user_context: Dicionário com informações do usuário

        Returns:
            String formatada com o contexto
        """
        if not user_context:
            return "Nenhum contexto adicional disponível."

        lines = ["Contexto do usuário:"]
        for key, value in user_context.items():
            lines.append(f"- {key}: {value}")

        return "\n".join(lines)

    def _get_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Obtém definições de tools filtradas pelo available_tools.

        Returns:
            Lista de definições de tools no formato LLM
        """
        if not self.available_tools:
            return []

        definitions = []
        for tool_name in self.available_tools:
            tool = self.tools.get_tool(tool_name)
            if tool:
                definitions.append(tool.to_tool_definition())

        return definitions

    def build_system_prompt(self, user_context: dict[str, Any]) -> str:
        """
        Constrói o system prompt completo para o agente.

        Args:
            user_context: Contexto do usuário atual

        Returns:
            System prompt formatado com skills + contexto
        """
        parts = []

        # Carregar skills
        skills_content = self.load_skills()
        if skills_content:
            parts.append(skills_content)

        # Adicionar contexto
        context_formatted = self._format_context(user_context)
        parts.append(context_formatted)

        return "\n\n".join(parts)

    def _build_messages(
        self, conversation_history: list[dict[str, Any]], message: str
    ) -> list[dict[str, Any]]:
        """Build message list with deduplication of the latest user message."""
        messages = list(conversation_history)
        if (
            not messages
            or messages[-1].get("role") != "user"
            or messages[-1].get("content") != message
        ):
            messages.append({"role": "user", "content": message})
        return messages

    async def process(
        self,
        message: str,
        user_context: dict[str, Any],
        conversation_history: list[dict[str, Any]],
    ) -> AgentResponse:
        """
        Processa uma mensagem e retorna a resposta do agente.

        Args:
            message: Mensagem do usuário
            user_context: Contexto do usuário (preferências, dados, etc.)
            conversation_history: Histórico da conversa

        Returns:
            AgentResponse com resposta e/ou tool calls
        """
        system_prompt = self.build_system_prompt(user_context)
        tool_definitions = self._get_tool_definitions()
        messages = self._build_messages(conversation_history, message)

        response = await self._run_tool_loop(
            messages=messages,
            system_prompt=system_prompt,
            tool_definitions=tool_definitions,
        )

        # Post-execution validation
        tool_calls_made = response.metadata.get("tool_calls", [])
        correction = self.validate_tool_usage(
            tool_calls_made=tool_calls_made,
            user_context=user_context,
            message=message,
        )
        if correction:
            corrective_messages = [
                *messages,
                {"role": "assistant", "content": response.response},
                {"role": "user", "content": correction},
            ]
            response = await self._run_tool_loop(
                messages=corrective_messages,
                system_prompt=system_prompt,
                tool_definitions=tool_definitions,
                max_rounds=2,
            )

        return response

    def validate_tool_usage(
        self,
        tool_calls_made: list[dict[str, Any]],
        user_context: dict[str, Any],
        message: str,
    ) -> str | None:
        """Return corrective prompt if expected tools were missed, else None."""
        return None

    async def _execute_tool_calls(
        self,
        executor: ToolExecutor,
        tool_calls: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Execute tool calls and return assistant message + tool result messages."""
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        }
        tool_messages: list[dict[str, Any]] = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("arguments", {})
            tool_call_id = tool_call.get("id")

            if not tool_name:
                payload = {"success": False, "data": None, "error": "Missing tool name"}
            else:
                try:
                    tool_result = await executor.execute(tool_name, tool_args)
                    payload = tool_result.to_dict()
                except ToolExecutionError as exc:
                    payload = {"success": False, "data": None, "error": str(exc)}

            content = json.dumps(payload, ensure_ascii=False)
            tool_message: dict[str, Any] = {"role": "tool", "content": content}
            if tool_call_id:
                tool_message["tool_call_id"] = tool_call_id
            tool_messages.append(tool_message)

        return assistant_msg, tool_messages

    async def _run_tool_loop(
        self,
        *,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tool_definitions: list[dict[str, Any]],
        max_rounds: int = 3,
    ) -> AgentResponse:
        """Execute multi-round tool-calling loop and return final response."""
        current_messages = list(messages)
        executor = ToolExecutor(self.tools)
        all_tool_calls: list[dict[str, Any]] = []
        tool_rounds = 0

        for _round in range(max_rounds):
            result = await self.llm.generate_response_with_tools(
                messages=current_messages,
                system_prompt=system_prompt,
                tools=tool_definitions,
            )

            tool_calls = result.get("tool_calls")
            if not tool_calls:
                return AgentResponse(
                    response=result.get("content"),
                    tool_calls=None,
                    metadata={
                        "finish_reason": result.get("finish_reason"),
                        "tool_rounds": tool_rounds,
                        **({"tool_calls": all_tool_calls} if all_tool_calls else {}),
                    },
                )

            tool_rounds += 1
            all_tool_calls.extend(tool_calls)
            assistant_msg, tool_messages = await self._execute_tool_calls(
                executor, tool_calls
            )
            current_messages = [*current_messages, assistant_msg, *tool_messages]

        # max_rounds exhausted — force text response with tools=[]
        followup = await self.llm.generate_response_with_tools(
            messages=current_messages,
            system_prompt=system_prompt,
            tools=[],
        )

        return AgentResponse(
            response=followup.get("content"),
            tool_calls=None,
            metadata={
                "finish_reason": followup.get("finish_reason"),
                "tool_rounds": tool_rounds,
                **({"tool_calls": all_tool_calls} if all_tool_calls else {}),
            },
        )
