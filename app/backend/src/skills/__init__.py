"""
Skills System for Milestone 2 (Issue 2.5)

The skills system allows agents to execute deterministic actions
by invoking registered skills with validated parameters.
"""

from src.skills.base import BaseSkill, SkillParameter, SkillResult
from src.skills.executor import SkillExecutionError, SkillExecutor
from src.skills.registry import SkillRegistry

__all__ = [
    "BaseSkill",
    "SkillResult",
    "SkillParameter",
    "SkillRegistry",
    "SkillExecutor",
    "SkillExecutionError",
]
