"""Advisor (Consultor) Agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents.base import BaseAgent
from src.tools.registry import ToolRegistry


class AdvisorAgent(BaseAgent):
    """Consultor agent for open-ended questions and exploratory guidance."""

    def __init__(
        self,
        llm_service: Any,
        tool_registry: ToolRegistry,
        skills_path: Path | None = None,
    ) -> None:
        super().__init__(
            llm_service=llm_service, tool_registry=tool_registry, skills_path=skills_path
        )

    @property
    def name(self) -> str:
        return "advisor"

    @property
    def skills(self) -> list[str]:
        return [
            "shared/persona_base",
            "shared/tom_ajuste",
            "shared/contexto_usuario",
            "advisor/conversacao_livre",
        ]

    @property
    def available_tools(self) -> list[str]:
        return [
            "get_current_date",
            "get_user_preferences",
            "get_calendar_events",
        ]
