"""Goal Agent — guides users through creating and managing goals."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents.base import BaseAgent
from src.tools.registry import ToolRegistry


class GoalAgent(BaseAgent):
    """Dedicated agent for goal creation and management.

    Scope-limited to annual goals and monthly objectives only.
    Refuses off-topic requests and guides structured goal creation.
    """

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
        return "goal"

    @property
    def skills(self) -> list[str]:
        return [
            "shared/persona_base",
            "shared/tom_ajuste",
            "shared/contexto_usuario",
            "goal_agent/definir_metas",
        ]

    @property
    def available_tools(self) -> list[str]:
        return [
            "list_user_goals",
            "save_annual_goal",
            "save_monthly_objective",
            "update_goal_status",
        ]
