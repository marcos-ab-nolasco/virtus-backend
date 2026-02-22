"""Deep OnboardingAgent — conducts the 5-phase conversational onboarding.

Applies Wheel of Life, Ikigai, ACT, Future Self, Working Backwards, and WOOP
frameworks invisibly across 5 phases (15-20 min conversation).
"""

import logging
from pathlib import Path
from typing import Any

from src.agents.base import AgentResponse, BaseAgent
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

ONBOARDING_PHASES = ["phase_1", "phase_2", "phase_3", "phase_4", "phase_5"]

PHASE_NAMES: dict[str, str] = {
    "phase_1": "Diagnóstico",
    "phase_2": "Direção e propósito",
    "phase_3": "Visão de futuro",
    "phase_4": "Realidade e obstáculos",
    "phase_5": "Cristalização",
}


class OnboardingAgent(BaseAgent):
    """Agent that conducts the deep 5-phase onboarding conversation.

    The LLM decides when enough data has been collected per phase and
    calls the appropriate tools before advancing. No rigid step validation —
    the conversation is fluid by design.
    """

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
        return "onboarding"

    @property
    def skills(self) -> list[str]:
        return [
            "shared/persona_base",
            "shared/tom_ajuste",
            "shared/contexto_usuario",
            "onboarding/deep_onboarding",
        ]

    @property
    def available_tools(self) -> list[str]:
        return [
            "save_life_area_scores",
            "save_onboarding_insight",
            "save_annual_goal",
            "save_monthly_objective",
            "save_weekly_priority",
            "advance_phase",
        ]

    def get_current_phase(self, context: dict[str, Any]) -> str:
        """Get the current onboarding phase from context.

        Returns 'phase_1' by default if no valid phase is stored.
        """
        profile = context.get("profile", {})
        current = profile.get("onboarding_current_step")

        if not current or current not in ONBOARDING_PHASES:
            return "phase_1"

        return str(current)

    def _build_state_summary(self, context: dict[str, Any]) -> str:
        """Summarise what data has already been collected so the LLM avoids re-asking."""
        profile = context.get("profile", {})
        current_phase = self.get_current_phase(context)

        lines = [
            "## Estado do Onboarding",
            f"- Fase atual: {current_phase} ({PHASE_NAMES.get(current_phase, '')})",
            f"- Status: {profile.get('onboarding_status', 'NOT_STARTED')}",
            "",
            "Dados já coletados (não repita perguntas sobre estes):",
        ]

        # Check what's been saved via the raw profile / onboarding_data
        onboarding_data = profile.get("onboarding_data") or {}
        preferred_name = profile.get("preferred_name")

        if preferred_name:
            lines.append(f"- Nome preferido: {preferred_name}")

        # We can't query the new tables from context easily, so we flag
        # the phase index as a proxy for what's been collected.
        phase_idx = (
            ONBOARDING_PHASES.index(current_phase) if current_phase in ONBOARDING_PHASES else 0
        )

        if phase_idx >= 1:
            lines.append("- Fase 1 concluída: scores de área de vida salvos")
        if phase_idx >= 2:
            lines.append("- Fase 2 concluída: atividades energizantes, habilidades, valores salvos")
        if phase_idx >= 3:
            lines.append("- Fase 3 concluída: visão de futuro e milestones salvos")
        if phase_idx >= 4:
            lines.append("- Fase 4 concluída: melhor resultado, obstáculo e plano if-then salvos")

        if onboarding_data:
            for key, value in onboarding_data.items():
                if key != "conversation_history" and value:
                    lines.append(f"- {key}: {value}")

        return "\n".join(lines)

    def _build_prompt(self, phase: str, context: dict[str, Any]) -> str:
        """Build the system prompt: base skills + current phase injection."""
        base_prompt = self.build_system_prompt(context)
        state_summary = self._build_state_summary(context)

        user_info = context.get("user", {})
        profile = context.get("profile", {})
        user_name = profile.get("preferred_name") or (user_info.get("full_name") or "").split()[0]
        user_id = user_info.get("id", "")

        phase_name = PHASE_NAMES.get(phase, phase)

        return f"""{base_prompt}

---

## Situação Atual do Onboarding

**Fase atual**: {phase} — {phase_name}
**Nome do usuário**: {user_name or "(ainda não definido)"}
**User ID para tools**: {user_id}

{state_summary}

## Instruções da Fase Atual

Consulte a seção correspondente à fase **{phase}** nas instruções da skill `deep_onboarding`
e conduza a conversa conforme descrito. Lembre-se:

- Empatia antes de avançar.
- Máximo 2 perguntas por resposta (prefira 1).
- Salve dados via tools assim que coletados.
- Chame `advance_phase` ao concluir a fase atual.
- Responda sempre em português brasileiro.
"""

    async def process(
        self,
        message: str,
        user_context: dict[str, Any],
        conversation_history: list[dict[str, Any]],
    ) -> AgentResponse:
        """Process a message in the deep onboarding flow."""
        try:
            current_phase = self.get_current_phase(user_context)
            logger.info(f"Processing deep onboarding message, phase: {current_phase}")

            system_prompt = self._build_prompt(current_phase, user_context)
            messages = self._build_messages(conversation_history, message)
            tool_definitions = self._get_tool_definitions()

            response = await self._run_tool_loop(
                messages=messages,
                system_prompt=system_prompt,
                tool_definitions=tool_definitions,
                max_rounds=5,
            )

            response.metadata.update(
                {
                    "current_phase": current_phase,
                    "phase_name": PHASE_NAMES.get(current_phase, current_phase),
                }
            )

            return response

        except Exception as e:
            logger.error(f"Error in deep onboarding process: {e}", exc_info=True)
            return AgentResponse(
                response="Desculpe, tive um problema. Podemos continuar de onde paramos?",
                metadata={"error": str(e)},
            )
