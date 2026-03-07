"""SetupAgent — conducts the lightweight initial setup conversation.

Collects preferred_name, timezone, and contact_frequency, then asks whether
the user wants to explore the dashboard or deepen into onboarding modules.
"""

import logging
from pathlib import Path
from typing import Any

from src.agents.base import AgentResponse, BaseAgent
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class SetupAgent(BaseAgent):
    """Agent that conducts the initial setup conversation (3 data points + choice)."""

    def __init__(
        self,
        llm_service: Any,
        tool_registry: ToolRegistry,
        skills_path: Path | None = None,
    ) -> None:
        super().__init__(
            llm_service=llm_service,
            tool_registry=tool_registry,
            skills_path=skills_path,
        )

    @property
    def name(self) -> str:
        return "setup"

    @property
    def skills(self) -> list[str]:
        return [
            "shared/persona_base",
            "shared/tom_ajuste",
            "setup/initial_setup",
        ]

    @property
    def available_tools(self) -> list[str]:
        return [
            "save_user_profile",
            "save_user_preferences",
            "complete_setup",
        ]

    def _build_prompt(self, context: dict[str, Any]) -> str:
        """Build the system prompt injecting user context."""
        base_prompt = self.build_system_prompt(context)

        user_info = context.get("user", {})
        profile = context.get("profile", {})
        preferences = context.get("preferences", {})

        user_id = user_info.get("id", "")
        full_name = user_info.get("full_name", "")
        preferred_name = profile.get("preferred_name")
        timezone = preferences.get("timezone") if preferences else None
        contact_frequency = preferences.get("contact_frequency") if preferences else None

        already_collected = []
        if preferred_name:
            already_collected.append(f"- Nome preferido: {preferred_name}")
        if timezone:
            already_collected.append(f"- Timezone: {timezone}")
        if contact_frequency:
            already_collected.append(f"- Frequência de contato: {contact_frequency}")

        collected_section = (
            "\n".join(already_collected) if already_collected else "- Nenhum dado coletado ainda"
        )

        return f"""{base_prompt}

---

## Contexto do Setup

**User ID para tools**: {user_id}
**Nome completo (para referência)**: {full_name or "(não informado)"}

**Dados já coletados (não repita perguntas sobre estes):**
{collected_section}

## Instruções

- Conduza a conversa de setup conforme a skill `initial_setup`.
- Salve cada dado via tool assim que coletado.
- Após coletar os 3 dados (nome, timezone, frequência), pergunte se o usuário quer explorar o produto ou se aprofundar.
- Após a resposta do usuário à pergunta de escolha, chame `complete_setup` com o `next_action` correto.
- Responda sempre em português brasileiro.
"""

    async def process(
        self,
        message: str,
        user_context: dict[str, Any],
        conversation_history: list[dict[str, Any]],
    ) -> AgentResponse:
        """Process a setup conversation message."""
        try:
            logger.info("Processing setup conversation message")

            system_prompt = self._build_prompt(user_context)
            messages = self._build_messages(conversation_history, message)
            tool_definitions = self._get_tool_definitions()

            response = await self._run_tool_loop(
                messages=messages,
                system_prompt=system_prompt,
                tool_definitions=tool_definitions,
                max_rounds=5,
            )

            # Extract next_action from complete_setup tool result if called
            tool_calls = response.metadata.get("tool_calls") or []
            next_action = None
            for tc in tool_calls:
                if tc.get("name") == "complete_setup":
                    result_data = tc.get("result", {})
                    if isinstance(result_data, dict):
                        next_action = result_data.get("next_action")

            if next_action:
                response.metadata["next_action"] = next_action
                response.metadata["setup_completed"] = True

            return response

        except Exception as e:
            logger.error(f"Error in setup process: {e}", exc_info=True)
            return AgentResponse(
                response="Desculpe, tive um problema. Podemos continuar o setup?",
                metadata={"error": str(e)},
            )
