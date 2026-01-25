"""Onboarding tools package.

Issue 3.2: Contains the ToolOnboardingShort and related components.
"""

from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort
from src.tools.onboarding.steps import OnboardingStep, get_next_step

__all__ = ["ToolOnboardingShort", "OnboardingStep", "get_next_step"]
