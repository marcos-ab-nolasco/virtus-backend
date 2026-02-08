"""
Onboarding Agent - Conducts the Express Onboarding flow

The onboarding agent is responsible for:
1. Guiding users through 7 onboarding steps
2. Extracting user preferences from responses
3. Saving data via tools
4. Managing step transitions
"""

import logging
from pathlib import Path
from typing import Any

from src.agents.base import AgentResponse, BaseAgent
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


# Onboarding step definitions
ONBOARDING_STEPS = ["intro", "name", "frequency", "routine", "goals", "calendar", "closing"]

STEP_ORDER = {step: idx for idx, step in enumerate(ONBOARDING_STEPS)}


class OnboardingAgent(BaseAgent):
    """
    Agent that conducts the Express Onboarding flow.

    Guides users through 7 steps to collect minimal data for personalization.
    Uses LLM to generate conversational responses while extracting structured data.
    """

    def __init__(
        self,
        llm_service: Any,
        tool_registry: ToolRegistry,
        skills_path: Path | None = None,
    ) -> None:
        """
        Initialize the onboarding agent.

        Args:
            llm_service: LLM service for generating responses
            tool_registry: Registry with tools for saving data
            skills_path: Optional path to skills folder
        """
        super().__init__(
            llm_service=llm_service,
            tool_registry=tool_registry,
            skills_path=skills_path,
        )

    @property
    def name(self) -> str:
        return "onboarding"

    @property
    def skills(self) -> list[str]:
        return [
            "shared/persona_base",
            "shared/tom_ajuste",
            "shared/contexto_usuario",
            "onboarding/onboarding_express",
            "onboarding/extracao_preferencias",
        ]

    @property
    def available_tools(self) -> list[str]:
        return [
            "save_user_profile",
            "save_user_preferences",
            "complete_onboarding_step",
        ]

    def get_current_step(self, context: dict[str, Any]) -> str:
        """
        Get the current onboarding step from context.

        Args:
            context: User context with profile data

        Returns:
            Current step name, defaults to "intro"
        """
        profile = context.get("profile", {})
        current_step = profile.get("onboarding_current_step")

        if not current_step or current_step not in ONBOARDING_STEPS:
            return "intro"

        return str(current_step)

    def get_next_step(self, current_step: str) -> str | None:
        """
        Get the next step after the current one.

        Args:
            current_step: Current step name

        Returns:
            Next step name or None if at the end
        """
        if current_step not in STEP_ORDER:
            return "intro"

        current_idx = STEP_ORDER[current_step]
        if current_idx >= len(ONBOARDING_STEPS) - 1:
            return None  # At the end

        return ONBOARDING_STEPS[current_idx + 1]

    def get_user_name(self, context: dict[str, Any]) -> str:
        """
        Get the user's preferred name or first name.

        Args:
            context: User context

        Returns:
            Name to use in messages
        """
        profile = context.get("profile", {})
        preferred_name = profile.get("preferred_name")
        if preferred_name:
            return str(preferred_name)

        user_info = context.get("user", {})
        full_name = user_info.get("full_name", "")
        if full_name:
            return str(full_name.split()[0])

        return ""

    async def process(
        self,
        message: str,
        user_context: dict[str, Any],
        conversation_history: list[dict[str, Any]],
    ) -> AgentResponse:
        """
        Process a message in the onboarding flow.

        Args:
            message: User's message
            user_context: Context from build_permanent_context
            conversation_history: Previous messages in conversation

        Returns:
            AgentResponse with response and optional tool calls
        """
        try:
            current_step = self.get_current_step(user_context)
            user_name = self.get_user_name(user_context)
            user_id = user_context.get("user", {}).get("id", "")

            logger.info(f"Processing onboarding message for step: {current_step}")

            # Build system prompt with step-specific instructions
            system_prompt = self._build_onboarding_prompt(
                current_step=current_step,
                user_name=user_name,
                user_id=user_id,
                user_context=user_context,
            )

            # Prepare messages for LLM
            messages = self._build_messages(conversation_history, message)

            # Get tool definitions
            tool_definitions = self._get_tool_definitions()

            response = await self._run_tool_loop(
                messages=messages,
                system_prompt=system_prompt,
                tool_definitions=tool_definitions,
            )

            response.metadata.update(
                {
                    "current_step": current_step,
                    "next_step": self.get_next_step(current_step),
                }
            )

            return response

        except Exception as e:
            logger.error(f"Error in onboarding process: {e}", exc_info=True)
            return AgentResponse(
                response="Desculpe, tive um problema. Vamos tentar novamente?",
                metadata={"error": str(e)},
            )

    def _build_onboarding_prompt(
        self,
        current_step: str,
        user_name: str,
        user_id: str,
        user_context: dict[str, Any],
    ) -> str:
        """
        Build the system prompt for the current onboarding step.

        Args:
            current_step: Current step in the flow
            user_name: User's name to use
            user_id: User's ID for tool calls
            user_context: Full user context

        Returns:
            Complete system prompt
        """
        # Load base skills
        base_prompt = self.build_system_prompt(user_context)

        # Add step-specific instructions
        step_instructions = self._get_step_instructions(current_step, user_name, user_id)

        return f"""{base_prompt}

---

## Situação Atual

Você está conduzindo o onboarding express do usuário.

**Etapa atual**: {current_step}
**Nome do usuário**: {user_name or "(ainda não definido)"}
**User ID para tools**: {user_id}

{step_instructions}

## Instruções Importantes

1. Mantenha um tom acolhedor e conversacional
2. Extraia os dados necessários da resposta do usuário
3. Use as tools disponíveis para salvar os dados extraídos
4. Avance para a próxima etapa após coletar os dados
5. Se o usuário quiser pular, permita (exceto frequency que é obrigatório)
6. Responda em português brasileiro
"""

    def _get_step_instructions(self, step: str, user_name: str, user_id: str) -> str:
        """
        Get specific instructions for each onboarding step.

        Args:
            step: Current step name
            user_name: User's name
            user_id: User's ID

        Returns:
            Step-specific instructions
        """
        instructions = {
            "intro": f"""
## Etapa INTRO

É a primeira interação. Apresente o Virtus e pergunte se o usuário está pronto para começar.

Se o usuário confirmar que quer continuar, chame a tool `complete_onboarding_step` com:
- step: "intro"
- user_id: "{user_id}"

Não precisa extrair dados nesta etapa, apenas obter confirmação.
""",
            "name": f"""
## Etapa NAME

Pergunte como o usuário prefere ser chamado.

Quando o usuário responder, extraia o nome preferido e chame:
1. `save_user_profile` com preferred_name
2. `complete_onboarding_step` com step: "name"

Se o usuário disser "tanto faz" ou similar, use o primeiro nome de "{user_name}".
""",
            "frequency": """
## Etapa FREQUENCY

Pergunte a frequência de contato preferida.

Opções:
- Raramente (RARELY)
- Às vezes (SOMETIMES)
- Frequentemente (FREQUENTLY)

Esta etapa é OBRIGATÓRIA. Não avance sem uma escolha clara.

Quando o usuário escolher, chame:
1. `save_user_preferences` com contact_frequency
2. `complete_onboarding_step` com step: "frequency"
""",
            "routine": """
## Etapa ROUTINE

Pergunte sobre:
1. Fuso horário (onde o usuário está)
2. Contexto de trabalho (freelancer, CLT, estudante, etc.)

Quando o usuário responder, chame:
1. `save_user_preferences` com timezone (se fornecido)
2. `save_user_profile` com work_context em onboarding_data (se fornecido)
3. `complete_onboarding_step` com step: "routine"

Se o usuário não souber o timezone, use UTC como default.
""",
            "goals": """
## Etapa GOALS

Pergunte sobre o momento atual e objetivos do usuário:
- Como está se sentindo em relação à organização/produtividade?
- O que gostaria de conquistar ou melhorar?

Extraia:
- initial_state: descrição do momento atual
- initial_goals: objetivos mencionados

Quando o usuário responder, chame:
1. `save_user_profile` com onboarding_data contendo initial_state e initial_goals
2. `complete_onboarding_step` com step: "goals"

Aceite respostas parciais - não force o usuário a responder tudo.
""",
            "calendar": """
## Etapa CALENDAR

Ofereça a integração de calendário (opcional).

Se o usuário quiser conectar, informe que ele precisará fazer isso pela interface web.
Se o usuário quiser pular, aceite sem insistir.

Chame `complete_onboarding_step` com step: "calendar" após a decisão.
""",
            "closing": """
## Etapa CLOSING

É a última etapa. Finalize o onboarding:

1. Agradeça o usuário por responder
2. Resuma a configuração (frequência escolhida)
3. Mencione que há um onboarding mais profundo disponível (opcional, para o futuro)
4. Deseje uma boa jornada

Chame `complete_onboarding_step` com step: "closing" para finalizar.

A tool vai marcar o onboarding como COMPLETED automaticamente.
""",
        }

        return instructions.get(step, instructions["intro"])
