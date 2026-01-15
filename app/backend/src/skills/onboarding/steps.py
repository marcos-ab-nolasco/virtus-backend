"""Onboarding step definitions.

Issue 3.2: Defines the onboarding flow steps and their prompts.
"""

from enum import Enum


class OnboardingStep(str, Enum):
    """Onboarding steps in sequence."""

    WELCOME = "welcome"
    NAME = "name"
    GOALS = "goals"
    PREFERENCES = "preferences"
    CONCLUSION = "conclusion"


# Step sequence for navigation
STEP_SEQUENCE = [
    OnboardingStep.WELCOME,
    OnboardingStep.NAME,
    OnboardingStep.GOALS,
    OnboardingStep.PREFERENCES,
    OnboardingStep.CONCLUSION,
]

# Step definitions with prompts and metadata
STEP_DEFINITIONS = {
    OnboardingStep.WELCOME: {
        "prompt": (
            "Olá! Sou o Virtus, seu assistente pessoal de produtividade e bem-estar. "
            "Vou te ajudar a organizar sua vida, definir objetivos e manter o foco no que importa. "
            "Antes de começarmos, preciso te conhecer um pouco melhor. Vamos lá?"
        ),
        "validation_required": False,
        "extract_data": False,
    },
    OnboardingStep.NAME: {
        "prompt": "Para começar, como você gostaria de ser chamado(a)?",
        "validation_required": True,
        "extract_data": True,
        "data_key": "name",
    },
    OnboardingStep.GOALS: {
        "prompt": (
            "Prazer em te conhecer! Me conta: quais são seus principais objetivos atualmente? "
            "Pode ser na carreira, saúde, relacionamentos, ou qualquer área da sua vida."
        ),
        "validation_required": True,
        "extract_data": True,
        "data_key": "goals",
    },
    OnboardingStep.PREFERENCES: {
        "prompt": (
            "Ótimo! Agora preciso saber algumas preferências para te ajudar melhor. "
            "Qual é seu fuso horário? (ex: America/Sao_Paulo)"
        ),
        "validation_required": True,
        "extract_data": True,
        "data_key": "preferences",
    },
    OnboardingStep.CONCLUSION: {
        "prompt": (
            "Perfeito! Seu perfil está configurado. Estou pronto para te ajudar a alcançar "
            "seus objetivos. Vamos começar seu primeiro planejamento?"
        ),
        "validation_required": False,
        "extract_data": False,
    },
}


def get_next_step(current_step: OnboardingStep) -> OnboardingStep | None:
    """Get the next step in the onboarding sequence.

    Args:
        current_step: Current onboarding step

    Returns:
        Next step or None if at the end
    """
    try:
        current_index = STEP_SEQUENCE.index(current_step)
        next_index = current_index + 1
        if next_index < len(STEP_SEQUENCE):
            return STEP_SEQUENCE[next_index]
        return None
    except ValueError:
        return None


def get_step_from_string(step_str: str | None) -> OnboardingStep | None:
    """Convert string to OnboardingStep enum.

    Args:
        step_str: Step name string

    Returns:
        OnboardingStep enum or None if invalid
    """
    if step_str is None:
        return None
    try:
        return OnboardingStep(step_str)
    except ValueError:
        return None
