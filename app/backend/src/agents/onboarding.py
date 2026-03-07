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

LIFE_AREAS_CONFIG = [
    {"id": "HEALTH", "label": "Saúde"},
    {"id": "WORK", "label": "Trabalho"},
    {"id": "RELATIONSHIPS", "label": "Relacionamentos"},
    {"id": "FINANCE", "label": "Finanças"},
    {"id": "PERSONAL_GROWTH", "label": "Crescimento pessoal"},
    {"id": "LEISURE", "label": "Lazer"},
    {"id": "PERSONAL_TIME", "label": "Tempo livre"},
    {"id": "SPIRITUALITY", "label": "Espiritualidade"},
]

VALUES_OPTIONS = [
    {"id": "autonomia", "label": "Autonomia"},
    {"id": "criatividade", "label": "Criatividade"},
    {"id": "equilibrio", "label": "Equilíbrio"},
    {"id": "familia", "label": "Família"},
    {"id": "saude", "label": "Saúde"},
    {"id": "impacto", "label": "Impacto"},
    {"id": "aprendizado", "label": "Aprendizado"},
    {"id": "integridade", "label": "Integridade"},
    {"id": "liberdade", "label": "Liberdade"},
    {"id": "conexao", "label": "Conexão"},
    {"id": "reconhecimento", "label": "Reconhecimento"},
    {"id": "proposito", "label": "Propósito"},
    {"id": "seguranca", "label": "Segurança financeira"},
    {"id": "lideranca", "label": "Liderança"},
]

OBSTACLE_OPTIONS = [
    {"id": "procrastinacao", "label": "Procrastinação"},
    {"id": "sobrecarga", "label": "Sobrecarga / muitas tarefas"},
    {"id": "falta_clareza", "label": "Falta de clareza"},
    {"id": "medo_falhar", "label": "Medo de falhar"},
    {"id": "falta_disciplina", "label": "Falta de consistência"},
    {"id": "distracoes", "label": "Distrações"},
    {"id": "burnout", "label": "Cansaço / burnout"},
    {"id": "perfeccionismo", "label": "Perfeccionismo"},
    {"id": "falta_suporte", "label": "Falta de suporte"},
]

FUTURE_SELF_HINTS = [
    "Como você se sente ao acordar de manhã?",
    "O que você realiza profissionalmente?",
    "Como são seus relacionamentos mais próximos?",
]


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

    def _determine_structured_input(
        self, phase: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Return structured_input config for the current phase, or None if not applicable."""
        data = (context.get("profile") or {}).get("onboarding_data") or {}

        if phase == "phase_1" and not data.get("life_areas_submitted"):
            return {
                "type": "slider_grid",
                "config": {
                    "areas": LIFE_AREAS_CONFIG,
                    "min": 1,
                    "max": 10,
                    "submit_label": "Confirmar avaliação",
                },
            }

        if phase == "phase_2" and not data.get("values_submitted"):
            return {
                "type": "chip_selector",
                "subtype": "chip_selector_values",
                "config": {
                    "options": VALUES_OPTIONS,
                    "multi": True,
                    "max_selections": 5,
                    "include_other": True,
                    "submit_label": "Confirmar valores",
                },
            }

        if phase == "phase_3":
            return {
                "type": "short_prompts",
                "config": {
                    "placeholder": "Descreva como será sua vida em 12 meses...",
                    "hints": FUTURE_SELF_HINTS,
                    "hints_label": "Se travar, clique aqui",
                    "submit_label": "Enviar",
                },
            }

        if phase == "phase_4" and not data.get("obstacle_submitted"):
            return {
                "type": "chip_selector",
                "subtype": "chip_selector_obstacles",
                "config": {
                    "options": OBSTACLE_OPTIONS,
                    "multi": False,
                    "include_other": True,
                    "submit_label": "Confirmar obstáculo",
                },
            }

        return None

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
        life_areas: list[dict[str, Any]] = context.get("life_areas") or []
        deep_insights: dict[str, Any] | None = context.get("deep_insights")
        annual_goals: list[dict[str, Any]] = context.get("annual_goals") or []

        lines = [
            "## Estado do Onboarding",
            f"- Fase atual: {current_phase} ({PHASE_NAMES.get(current_phase, '')})",
            f"- Status: {profile.get('onboarding_status', 'NOT_STARTED')}",
            "",
            "Dados já coletados (não repita perguntas sobre estes):",
        ]

        preferred_name = profile.get("preferred_name")
        if preferred_name:
            lines.append(f"- Nome preferido: {preferred_name}")

        # Life area scores (from DB via context)
        if life_areas:
            areas_summary = ", ".join(
                f"{a['area']}: {a['current']}/10 (desejado: {a['desired']})" for a in life_areas
            )
            lines.append(f"- Áreas de vida avaliadas: {areas_summary}")
            priority_areas = [a["area"] for a in life_areas if a.get("priority")]
            if priority_areas:
                lines.append(f"- Áreas prioritárias: {', '.join(priority_areas)}")

        # Deep insights (from DB via context)
        if deep_insights:
            if deep_insights.get("energizing_activities"):
                lines.append(f"- Atividades energizantes: {deep_insights['energizing_activities']}")
            if deep_insights.get("top_values"):
                lines.append(f"- Valores: {deep_insights['top_values']}")
            if deep_insights.get("future_self_description"):
                lines.append(
                    f"- Visão de futuro: {deep_insights['future_self_description'][:200]}..."
                    if len(deep_insights["future_self_description"]) > 200
                    else f"- Visão de futuro: {deep_insights['future_self_description']}"
                )
            if deep_insights.get("internal_obstacle"):
                lines.append(f"- Obstáculo interno: {deep_insights['internal_obstacle']}")
            if deep_insights.get("if_then_plan"):
                lines.append(f"- Plano if-then: {deep_insights['if_then_plan']}")

        # Annual goals
        if annual_goals:
            goals_summary = "; ".join(f"{g['title']} ({g['life_area']})" for g in annual_goals)
            lines.append(f"- Objetivos anuais: {goals_summary}")

        return "\n".join(lines)

    def _build_prompt(
        self, phase: str, context: dict[str, Any], is_enrichment: bool = False
    ) -> str:
        """Build the system prompt: base skills + current phase injection."""
        base_prompt = self.build_system_prompt(context)
        state_summary = self._build_state_summary(context)

        user_info = context.get("user", {})
        profile = context.get("profile", {})
        user_name = profile.get("preferred_name") or (user_info.get("full_name") or "").split()[0]
        user_id = user_info.get("id", "")

        phase_name = PHASE_NAMES.get(phase, phase)

        enrichment_section = ""
        if is_enrichment:
            enrichment_section = """
## Modo Enriquecimento

Esta é uma REVISITA a um módulo já concluído. Siga as instruções da seção "Modo Enriquecimento"
da skill `deep_onboarding`:
- Reconheça os dados anteriores com naturalidade
- Pergunte o que mudou ou o que o usuário quer aprofundar
- NÃO refaça o módulo do zero
- Permita refinar dados existentes via tools

"""

        return f"""{base_prompt}

---

## Situação Atual do Onboarding

**Fase atual**: {phase} — {phase_name}
**Nome do usuário**: {user_name or "(ainda não definido)"}
**User ID para tools**: {user_id}
{"**Modo**: Enriquecimento (revisita)" if is_enrichment else ""}

{state_summary}
{enrichment_section}
## Instruções da Fase Atual

Consulte a seção correspondente à fase **{phase}** nas instruções da skill `deep_onboarding`
e conduza a conversa conforme descrito. Lembre-se:

- Empatia antes de avançar.
- Máximo 2 perguntas por resposta (prefira 1).
- Salve dados via tools assim que coletados.
- Chame `advance_phase` ao concluir a fase atual (somente se NÃO for enriquecimento).
- Responda sempre em português brasileiro.
"""

    async def process(
        self,
        message: str,
        user_context: dict[str, Any],
        conversation_history: list[dict[str, Any]],
        is_enrichment: bool = False,
    ) -> AgentResponse:
        """Process a message in the deep onboarding flow."""
        try:
            current_phase = self.get_current_phase(user_context)
            logger.info(
                f"Processing deep onboarding message, phase: {current_phase}, "
                f"enrichment: {is_enrichment}"
            )

            system_prompt = self._build_prompt(current_phase, user_context, is_enrichment)
            messages = self._build_messages(conversation_history, message)
            tool_definitions = self._get_tool_definitions()

            response = await self._run_tool_loop(
                messages=messages,
                system_prompt=system_prompt,
                tool_definitions=tool_definitions,
                max_rounds=5,
            )

            # Detect advance_phase called during tool loop
            tool_calls = response.metadata.get("tool_calls") or []
            if any(tc.get("name") == "advance_phase" for tc in tool_calls):
                try:
                    idx = ONBOARDING_PHASES.index(current_phase)
                    if idx + 1 < len(ONBOARDING_PHASES):
                        current_phase = ONBOARDING_PHASES[idx + 1]
                except ValueError:
                    pass

            structured_input = self._determine_structured_input(current_phase, user_context)
            response.metadata.update(
                {
                    "current_phase": current_phase,
                    "phase_name": PHASE_NAMES.get(current_phase, current_phase),
                    **({"structured_input": structured_input} if structured_input else {}),
                }
            )

            return response

        except Exception as e:
            logger.error(f"Error in deep onboarding process: {e}", exc_info=True)
            return AgentResponse(
                response="Desculpe, tive um problema. Podemos continuar de onde paramos?",
                metadata={"error": str(e)},
            )
