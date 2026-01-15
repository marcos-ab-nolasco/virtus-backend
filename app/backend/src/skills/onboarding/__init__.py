"""Onboarding skills package.

Issue 3.2: Contains the SkillOnboardingShort and related components.
"""

from src.skills.onboarding.skill_onboarding_short import SkillOnboardingShort
from src.skills.onboarding.steps import OnboardingStep, get_next_step

__all__ = ["SkillOnboardingShort", "OnboardingStep", "get_next_step"]
