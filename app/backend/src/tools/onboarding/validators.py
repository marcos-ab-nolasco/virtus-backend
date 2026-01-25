"""Onboarding input validators.

Issue 3.2: Validates and extracts data from user responses.
"""

import re
from collections.abc import Callable
from typing import Any
from zoneinfo import ZoneInfo


def validate_name(name: str) -> tuple[bool, str | None]:
    """Validate user name input.

    Args:
        name: User provided name

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Por favor, me diga seu nome."

    stripped = name.strip()
    if len(stripped) < 2:
        return False, "O nome deve ter pelo menos 2 caracteres."

    if len(stripped) > 100:
        return False, "O nome deve ter no máximo 100 caracteres."

    return True, None


def extract_name(text: str) -> str:
    """Extract name from user response.

    Args:
        text: User response text

    Returns:
        Extracted name
    """
    # Simple extraction - just clean up the text
    return text.strip()


def validate_goals(goals_text: str) -> tuple[bool, str | None]:
    """Validate goals input.

    Args:
        goals_text: User provided goals description

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not goals_text or not goals_text.strip():
        return False, "Por favor, me conte pelo menos um objetivo."

    stripped = goals_text.strip()
    if len(stripped) < 5:
        return False, "Descreva seus objetivos com um pouco mais de detalhe."

    return True, None


def extract_goals(text: str) -> list[str]:
    """Extract goals from user response.

    Splits goals by common separators (comma, 'e', newline).

    Args:
        text: User response text

    Returns:
        List of extracted goals
    """
    # Replace common separators
    normalized = text.strip()

    # Split by various separators
    # Try comma first
    if "," in normalized:
        goals = [g.strip() for g in normalized.split(",") if g.strip()]
    # Try " e " (Portuguese "and")
    elif " e " in normalized:
        goals = [g.strip() for g in normalized.split(" e ") if g.strip()]
    # Try newlines
    elif "\n" in normalized:
        goals = [g.strip() for g in normalized.split("\n") if g.strip()]
    else:
        # Single goal
        goals = [normalized]

    return goals


def validate_preferences(prefs_text: str) -> tuple[bool, str | None]:
    """Validate preferences input.

    Args:
        prefs_text: User provided preferences (timezone, language)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not prefs_text or not prefs_text.strip():
        return False, "Por favor, informe seu fuso horário."

    # Try to extract timezone
    prefs = extract_preferences(prefs_text)

    if not prefs.get("timezone"):
        return False, "Não consegui identificar o fuso horário. Use o formato: America/Sao_Paulo"

    # Validate timezone
    try:
        ZoneInfo(prefs["timezone"])
    except Exception:
        return (
            False,
            f"Fuso horário '{prefs['timezone']}' não reconhecido. "
            "Use o formato: America/Sao_Paulo",
        )

    return True, None


def extract_preferences(text: str) -> dict[str, str]:
    """Extract preferences from user response.

    Args:
        text: User response text

    Returns:
        Dictionary with timezone and language
    """
    result: dict[str, str] = {}

    # Common timezone patterns
    timezone_pattern = r"(America|Europe|Asia|Africa|Pacific|Australia)/[A-Za-z_]+"
    timezone_match = re.search(timezone_pattern, text)

    if timezone_match:
        result["timezone"] = timezone_match.group()
    else:
        # Try common abbreviations
        if "são paulo" in text.lower() or "sao paulo" in text.lower():
            result["timezone"] = "America/Sao_Paulo"
        elif "brasilia" in text.lower() or "brasília" in text.lower():
            result["timezone"] = "America/Sao_Paulo"
        elif "utc" in text.lower():
            result["timezone"] = "UTC"

    # Extract language (default to pt-BR for Brazilian users)
    if "en" in text.lower() or "english" in text.lower() or "inglês" in text.lower():
        result["language"] = "en"
    else:
        result["language"] = "pt-BR"

    return result


def validate_welcome(response: str) -> tuple[bool, str | None]:
    """Validate welcome step response (always valid).

    Args:
        response: User response

    Returns:
        Always (True, None)
    """
    return True, None


def validate_conclusion(response: str) -> tuple[bool, str | None]:
    """Validate conclusion step response (always valid).

    Args:
        response: User response

    Returns:
        Always (True, None)
    """
    return True, None


# Validator mapping by step
STEP_VALIDATORS = {
    "welcome": validate_welcome,
    "name": validate_name,
    "goals": validate_goals,
    "preferences": validate_preferences,
    "conclusion": validate_conclusion,
}

# Extractor mapping by step
STEP_EXTRACTORS: dict[str, Callable[[str], dict[str, Any]]] = {
    "name": lambda text: {"name": extract_name(text)},
    "goals": lambda text: {"goals": extract_goals(text)},
    "preferences": extract_preferences,
}
