"""
Skill Executor for executing skills from the registry

Handles skill invocation, error handling, and result formatting.
"""

import logging
from typing import Any

from src.skills.base import SkillResult
from src.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillExecutionError(Exception):
    """Raised when skill execution fails"""

    pass


class SkillExecutor:
    """
    Executes skills from the registry

    Provides a safe interface for executing skills with:
    - Error handling
    - Logging
    - Result formatting
    """

    def __init__(self, registry: SkillRegistry) -> None:
        """
        Initialize executor with a skill registry

        Args:
            registry: The skill registry to use for skill lookup
        """
        self.registry = registry

    async def execute(self, skill_name: str, args: dict[str, Any]) -> SkillResult:
        """
        Execute a skill by name with the given arguments

        Args:
            skill_name: Name of the skill to execute
            args: Dictionary of arguments to pass to the skill

        Returns:
            SkillResult with success status, data, and/or error message

        Raises:
            SkillExecutionError: If the skill is not found in the registry
        """
        # Get skill from registry
        skill = self.registry.get_skill(skill_name)
        if skill is None:
            error_msg = f"Skill '{skill_name}' not found in registry"
            logger.error(error_msg)
            raise SkillExecutionError(error_msg)

        # Execute skill with error handling
        try:
            logger.info(f"Executing skill: {skill_name} with args: {args}")
            result = await skill.execute(args)
            logger.info(f"Skill {skill_name} completed: success={result.success}")
            return result

        except Exception as e:
            # Catch any errors during execution and return as error result
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Skill {skill_name} failed: {error_msg}", exc_info=True)

            return SkillResult(success=False, data=None, error=error_msg)

    async def execute_with_fallback(
        self, skill_name: str, args: dict[str, Any], fallback_message: str | None = None
    ) -> SkillResult:
        """
        Execute skill with fallback message if skill not found

        Args:
            skill_name: Name of the skill to execute
            args: Arguments to pass to the skill
            fallback_message: Message to return if skill not found

        Returns:
            SkillResult (always succeeds, uses fallback if skill not found)
        """
        try:
            return await self.execute(skill_name, args)
        except SkillExecutionError as e:
            if fallback_message is None:
                fallback_message = f"Skill '{skill_name}' is not available"

            logger.warning(f"Using fallback for {skill_name}: {e}")
            return SkillResult(success=False, data=None, error=fallback_message)
