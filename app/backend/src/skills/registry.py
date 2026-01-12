"""
Skill Registry for managing and discovering skills

The registry maintains a collection of available skills and provides
methods for registration, discovery, and metadata access.
"""

from typing import Any

from src.skills.base import BaseSkill


class SkillRegistry:
    """
    Registry for managing skills

    Maintains a collection of skills and provides methods for:
    - Registering new skills
    - Retrieving skills by name
    - Listing all available skills
    - Unregistering skills
    """

    def __init__(self) -> None:
        """Initialize empty skill registry"""
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """
        Register a skill in the registry

        Args:
            skill: The skill to register

        Raises:
            ValueError: If a skill with the same name is already registered
        """
        if skill.name in self._skills:
            raise ValueError(
                f"Skill '{skill.name}' is already registered. "
                f"Use unregister() first to replace it."
            )

        self._skills[skill.name] = skill

    def unregister(self, skill_name: str) -> None:
        """
        Remove a skill from the registry

        Args:
            skill_name: Name of the skill to remove

        Note:
            Does not raise an error if skill doesn't exist (idempotent)
        """
        self._skills.pop(skill_name, None)

    def get_skill(self, skill_name: str) -> BaseSkill | None:
        """
        Retrieve a skill by name

        Args:
            skill_name: Name of the skill to retrieve

        Returns:
            The skill instance, or None if not found
        """
        return self._skills.get(skill_name)

    def list_skills(self) -> list[dict[str, Any]]:
        """
        List all registered skills with their metadata

        Returns:
            List of skill metadata dictionaries containing:
            - name: Skill name
            - description: Skill description
            - parameters: Parameter schema
        """
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "parameters": skill.parameters,
            }
            for skill in self._skills.values()
        ]

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Get all skills as LLM tool definitions

        Returns:
            List of tool definitions for function calling
        """
        return [skill.to_tool_definition() for skill in self._skills.values()]

    def __len__(self) -> int:
        """Return number of registered skills"""
        return len(self._skills)

    def __contains__(self, skill_name: str) -> bool:
        """Check if skill is registered"""
        return skill_name in self._skills
