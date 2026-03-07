"""
Tests for shared skills loading.

Verifies that skills can be loaded correctly by agents.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

from src.agents.base import BaseAgent
from src.services.ai.base import BaseAIService
from src.tools.registry import ToolRegistry


class SkillTestAgent(BaseAgent):
    """Test agent for skill loading tests."""

    def __init__(
        self,
        llm_service: Any,
        tool_registry: Any,
        skills_list: list[str],
        skills_path: Path | None = None,
    ) -> None:
        super().__init__(llm_service, tool_registry, skills_path)
        self._skills_list = skills_list

    @property
    def name(self) -> str:
        return "skill_test_agent"

    @property
    def skills(self) -> list[str]:
        return self._skills_list

    @property
    def available_tools(self) -> list[str]:
        return []


class TestSharedSkillsExist:
    """Test that shared skills files exist and can be loaded."""

    def setup_method(self) -> None:
        """Setup for each test."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.skills_path = Path(__file__).parent.parent.parent / "src" / "skills"

    def test_persona_base_skill_exists(self) -> None:
        """persona_base skill should exist and be loadable."""
        agent = SkillTestAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_list=["shared/persona_base"],
            skills_path=self.skills_path,
        )

        content = agent.load_skills()

        assert len(content) > 0
        assert "Virtus" in content
        assert "mentor" in content.lower() or "Mentor" in content
        assert "Pilares de Personalidade" in content or "pilares" in content.lower()

    def test_tom_ajuste_skill_exists(self) -> None:
        """tom_ajuste skill should exist and be loadable."""
        agent = SkillTestAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_list=["shared/tom_ajuste"],
            skills_path=self.skills_path,
        )

        content = agent.load_skills()

        assert len(content) > 0
        assert "ContactFrequency" in content or "contact_frequency" in content
        assert "RARELY" in content
        assert "SOMETIMES" in content
        assert "FREQUENTLY" in content

    def test_contexto_usuario_skill_exists(self) -> None:
        """contexto_usuario skill should exist and be loadable."""
        agent = SkillTestAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_list=["shared/contexto_usuario"],
            skills_path=self.skills_path,
        )

        content = agent.load_skills()

        assert len(content) > 0
        assert "preferred_name" in content
        assert "onboarding_status" in content

    def test_load_multiple_shared_skills(self) -> None:
        """Should be able to load all shared skills together."""
        agent = SkillTestAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_list=[
                "shared/persona_base",
                "shared/tom_ajuste",
                "shared/contexto_usuario",
            ],
            skills_path=self.skills_path,
        )

        content = agent.load_skills()

        # Should contain content from all skills
        assert "Virtus" in content  # persona_base
        assert "ContactFrequency" in content or "RARELY" in content  # tom_ajuste
        assert "preferred_name" in content  # contexto_usuario

        # Should have separators between skills
        assert content.count("---") >= 2


class TestSkillContentQuality:
    """Test that skill content meets quality requirements."""

    def setup_method(self) -> None:
        """Setup for each test."""
        self.mock_llm = Mock(spec=BaseAIService)
        self.mock_registry = Mock(spec=ToolRegistry)
        self.skills_path = Path(__file__).parent.parent.parent / "src" / "skills"

    def test_persona_base_has_required_sections(self) -> None:
        """persona_base should have all required sections."""
        agent = SkillTestAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_list=["shared/persona_base"],
            skills_path=self.skills_path,
        )

        content = agent.load_skills()

        # Required sections
        assert "Identidade" in content
        assert "Pilares" in content or "pilares" in content.lower()
        assert "Princípios" in content or "principios" in content.lower()
        assert "Limites" in content or "limites" in content.lower()

    def test_persona_base_has_anti_patterns(self) -> None:
        """persona_base should document what NOT to do."""
        agent = SkillTestAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_list=["shared/persona_base"],
            skills_path=self.skills_path,
        )

        content = agent.load_skills()

        # Should have "Não Faz" or similar negative patterns
        assert "Não Faz" in content or "NUNCA" in content or "Evitar" in content

    def test_tom_ajuste_has_contact_frequency_matrix(self) -> None:
        """tom_ajuste should have contact frequency behavioral matrix."""
        agent = SkillTestAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_list=["shared/tom_ajuste"],
            skills_path=self.skills_path,
        )

        content = agent.load_skills()

        # Should have all three frequency levels documented
        assert "RARELY" in content or "Rarely" in content or "Raramente" in content
        assert "SOMETIMES" in content or "Sometimes" in content or "Às vezes" in content
        assert "FREQUENTLY" in content or "Frequently" in content or "Frequentemente" in content

    def test_contexto_usuario_documents_structure(self) -> None:
        """contexto_usuario should document the context structure."""
        agent = SkillTestAgent(
            llm_service=self.mock_llm,
            tool_registry=self.mock_registry,
            skills_list=["shared/contexto_usuario"],
            skills_path=self.skills_path,
        )

        content = agent.load_skills()

        # Should document main context sections
        assert "user" in content.lower()
        assert "preferences" in content.lower() or "preferências" in content.lower()
        assert "profile" in content.lower() or "perfil" in content.lower()
