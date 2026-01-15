"""SkillOnboardingShort - Guides user through short onboarding flow.

Issue 3.2: Deterministic skill for guiding onboarding steps.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_async_sessionmaker
from src.services import onboarding as onboarding_service
from src.skills.base import BaseSkill, SkillResult
from src.skills.onboarding.steps import (
    STEP_DEFINITIONS,
    OnboardingStep,
    get_next_step,
    get_step_from_string,
)
from src.skills.onboarding.validators import STEP_EXTRACTORS, STEP_VALIDATORS


class _SessionWrapper:
    """Wrapper to make an existing session work as async context manager."""

    def __init__(self, session: AsyncSession, owns_session: bool = False):
        self._session = session
        self._owns_session = owns_session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        # Only close the session if we created it
        if self._owns_session:
            await self._session.close()


class SkillOnboardingShort(BaseSkill):
    """Skill that guides users through the short onboarding flow.

    Actions:
        - start: Start the onboarding process
        - process_response: Process user response for current step
        - get_status: Get current onboarding status

    Parameters:
        user_id: UUID of the user
        action: Action to perform (start, process_response, get_status)
        user_response: User's response text (required for process_response)
    """

    name = "onboarding_short"
    description = (
        "Guides user through short onboarding flow to collect name, goals, and preferences"
    )
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "UUID of the user",
            },
            "action": {
                "type": "string",
                "enum": ["start", "process_response", "get_status"],
                "description": "Action to perform",
            },
            "user_response": {
                "type": "string",
                "description": "User's response to current step (for process_response)",
            },
        },
        "required": ["user_id", "action"],
    }

    def __init__(self, db_session: AsyncSession | None = None):
        """Initialize the skill with optional database session.

        Args:
            db_session: Optional database session (for testing)
        """
        self._db_session = db_session

    async def execute(self, args: dict[str, Any]) -> SkillResult:
        """Execute the skill with the given arguments.

        Args:
            args: Dictionary with user_id, action, and optional user_response

        Returns:
            SkillResult with action-specific data
        """
        try:
            # Extract parameters
            user_id_str = args.get("user_id")
            action = args.get("action")

            if not user_id_str:
                return SkillResult(
                    success=False, data=None, error="Missing required field: user_id"
                )

            if not action:
                return SkillResult(success=False, data=None, error="Missing required field: action")

            try:
                user_id = UUID(user_id_str)
            except (ValueError, TypeError):
                return SkillResult(
                    success=False, data=None, error=f"Invalid UUID format: {user_id_str}"
                )

            # Route to appropriate action handler
            if action == "start":
                return await self._handle_start(user_id)
            elif action == "process_response":
                user_response = args.get("user_response", "")
                return await self._handle_process_response(user_id, user_response)
            elif action == "get_status":
                return await self._handle_get_status(user_id)
            else:
                return SkillResult(success=False, data=None, error=f"Unknown action: {action}")

        except Exception as e:
            return SkillResult(
                success=False,
                data=None,
                error=f"Skill execution failed: {type(e).__name__}: {str(e)}",
            )

    async def _get_db_session(self) -> _SessionWrapper:
        """Get database session - use injected session or create new one.

        Returns:
            Database session wrapper (context manager)
        """
        if self._db_session is not None:
            # Return a no-op context manager wrapper for injected session
            return _SessionWrapper(self._db_session, owns_session=False)
        # Create new session using factory
        session_factory = get_async_sessionmaker()
        session = session_factory()
        return _SessionWrapper(session, owns_session=True)

    async def _handle_start(self, user_id: UUID) -> SkillResult:
        """Handle the start action - begin onboarding.

        Args:
            user_id: User's UUID

        Returns:
            SkillResult with welcome message and status
        """
        async with await self._get_db_session() as db:
            try:
                profile = await onboarding_service.start_onboarding(db, user_id)

                # Get welcome step definition
                welcome_step = STEP_DEFINITIONS[OnboardingStep.WELCOME]

                return SkillResult(
                    success=True,
                    data={
                        "status": profile.onboarding_status.value,
                        "current_step": profile.onboarding_current_step,
                        "message": welcome_step["prompt"],
                        "next_step": OnboardingStep.NAME.value,
                    },
                    error=None,
                )
            except Exception as e:
                error_msg = str(e)
                if hasattr(e, "detail"):
                    error_msg = e.detail
                return SkillResult(success=False, data=None, error=error_msg)

    async def _handle_process_response(self, user_id: UUID, user_response: str) -> SkillResult:
        """Handle the process_response action - validate and save user response.

        Args:
            user_id: User's UUID
            user_response: User's text response

        Returns:
            SkillResult with validation result and next step info
        """
        async with await self._get_db_session() as db:
            try:
                # Get current state
                state = await onboarding_service.get_onboarding_state(db, user_id)
                current_step_str = state["current_step"]

                if not current_step_str:
                    return SkillResult(success=False, data=None, error="Onboarding not started")

                current_step = get_step_from_string(current_step_str)
                if not current_step:
                    return SkillResult(
                        success=False, data=None, error=f"Invalid step: {current_step_str}"
                    )

                step_def = STEP_DEFINITIONS[current_step]

                # Validate response if required
                is_valid = True
                validation_error: str | None = None
                extracted_data: dict[str, Any] = {}

                if step_def.get("validation_required", False):
                    validator = STEP_VALIDATORS.get(current_step.value)
                    if validator:
                        is_valid, validation_error = validator(user_response)

                # Extract data if valid and extraction is enabled
                if is_valid and step_def.get("extract_data", False):
                    extractor = STEP_EXTRACTORS.get(current_step.value)
                    if extractor:
                        extracted_data = extractor(user_response)

                        # Save the extracted data
                        await onboarding_service.save_step_response(
                            db,
                            user_id,
                            step=current_step.value,
                            data=extracted_data,
                            user_response=user_response,
                        )

                # Determine next step
                next_step = None
                next_message = None

                if is_valid:
                    # Advance to next step
                    await onboarding_service.advance_step(db, user_id)

                    # Get the next step info
                    next_step_enum = get_next_step(current_step)
                    if next_step_enum:
                        next_step = next_step_enum.value
                        next_message = STEP_DEFINITIONS[next_step_enum]["prompt"]

                        # Personalize message with collected data if available
                        if next_step_enum == OnboardingStep.GOALS:
                            # Get updated state with name
                            updated_state = await onboarding_service.get_onboarding_state(
                                db, user_id
                            )
                            name = updated_state["data"].get("name", "")
                            if name:
                                next_message = f"Prazer em te conhecer, {name}! {next_message}"

                return SkillResult(
                    success=True,
                    data={
                        "is_valid": is_valid,
                        "validation_error": validation_error,
                        "current_step": current_step.value,
                        "next_step": next_step,
                        "next_message": next_message,
                        "extracted_data": extracted_data,
                    },
                    error=None,
                )

            except Exception as e:
                error_msg = str(e)
                if hasattr(e, "detail"):
                    error_msg = e.detail
                return SkillResult(success=False, data=None, error=error_msg)

    async def _handle_get_status(self, user_id: UUID) -> SkillResult:
        """Handle the get_status action - return current onboarding state.

        Args:
            user_id: User's UUID

        Returns:
            SkillResult with current onboarding state
        """
        async with await self._get_db_session() as db:
            try:
                state = await onboarding_service.get_onboarding_state(db, user_id)

                # Get current step message if in progress
                current_message = None
                if state["current_step"]:
                    current_step = get_step_from_string(state["current_step"])
                    if current_step and current_step in STEP_DEFINITIONS:
                        current_message = STEP_DEFINITIONS[current_step]["prompt"]

                return SkillResult(
                    success=True,
                    data={
                        "status": state["status"],
                        "current_step": state["current_step"],
                        "progress_percent": state["progress_percent"],
                        "started_at": state["started_at"],
                        "completed_at": state["completed_at"],
                        "current_message": current_message,
                    },
                    error=None,
                )

            except Exception as e:
                error_msg = str(e)
                if hasattr(e, "detail"):
                    error_msg = e.detail
                return SkillResult(success=False, data=None, error=error_msg)
