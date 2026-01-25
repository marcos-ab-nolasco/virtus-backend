"""Tests for ToolOnboardingShort.

Issue 3.2: Tests for onboarding tool with step validation.
Following TDD - RED phase: write failing tests first.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User


class TestToolOnboardingShortMetadata:
    """Test ToolOnboardingShort metadata and tool definition."""

    def test_tool_has_correct_name(self):
        """Tool should have name 'onboarding_short'."""
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        tool = ToolOnboardingShort()
        assert tool.name == "onboarding_short"

    def test_tool_has_description(self):
        """Tool should have a description."""
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        tool = ToolOnboardingShort()
        assert len(tool.description) > 0

    def test_tool_has_parameters_schema(self):
        """Tool should have JSONSchema parameters."""
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        tool = ToolOnboardingShort()
        assert "type" in tool.parameters
        assert tool.parameters["type"] == "object"
        assert "properties" in tool.parameters

    def test_tool_requires_user_id_and_action(self):
        """Tool should require user_id and action parameters."""
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        tool = ToolOnboardingShort()
        required = tool.parameters.get("required", [])
        assert "user_id" in required
        assert "action" in required

    def test_tool_to_tool_definition(self):
        """Tool should provide LLM-compatible tool definition."""
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        tool = ToolOnboardingShort()
        tool_def = tool.to_tool_definition()

        assert tool_def["type"] == "function"
        assert "function" in tool_def
        assert tool_def["function"]["name"] == "onboarding_short"


class TestToolOnboardingShortStart:
    """Test ToolOnboardingShort start action."""

    @pytest.mark.asyncio
    async def test_start_action_returns_welcome_message(
        self, db_session: AsyncSession, test_user: User
    ):
        """Start action should return welcome message and set status to IN_PROGRESS."""
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        tool = ToolOnboardingShort(db_session=db_session)
        result = await tool.execute({"user_id": str(test_user.id), "action": "start"})

        assert result.success is True
        assert result.data is not None
        assert "message" in result.data
        assert result.data["current_step"] == "welcome"
        assert result.data["status"] == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_start_action_fails_for_completed_user(
        self, db_session: AsyncSession, test_user: User
    ):
        """Start action should fail if user already completed onboarding."""
        from sqlalchemy import select

        from src.db.models.user_profile import OnboardingStatus, UserProfile
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        # Set user as completed
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()
        profile.onboarding_status = OnboardingStatus.COMPLETED
        await db_session.commit()

        tool = ToolOnboardingShort(db_session=db_session)
        result = await tool.execute({"user_id": str(test_user.id), "action": "start"})

        assert result.success is False
        assert "already completed" in result.error.lower()


class TestToolOnboardingShortProcessResponse:
    """Test ToolOnboardingShort process_response action."""

    @pytest.mark.asyncio
    async def test_process_response_validates_name_step(
        self, db_session: AsyncSession, test_user: User
    ):
        """Process response should validate and save name."""
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        tool = ToolOnboardingShort(db_session=db_session)

        # Start onboarding first
        await tool.execute({"user_id": str(test_user.id), "action": "start"})

        # Advance to name step
        await tool.execute(
            {
                "user_id": str(test_user.id),
                "action": "process_response",
                "user_response": "ok",
            }
        )

        # Process name
        result = await tool.execute(
            {
                "user_id": str(test_user.id),
                "action": "process_response",
                "user_response": "João Silva",
            }
        )

        assert result.success is True
        assert result.data["is_valid"] is True
        assert result.data["next_step"] == "goals"

    @pytest.mark.asyncio
    async def test_process_response_rejects_empty_name(
        self, db_session: AsyncSession, test_user: User
    ):
        """Process response should reject empty name."""
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        tool = ToolOnboardingShort(db_session=db_session)

        # Start and advance to name step
        await tool.execute({"user_id": str(test_user.id), "action": "start"})
        await tool.execute(
            {
                "user_id": str(test_user.id),
                "action": "process_response",
                "user_response": "ok",
            }
        )

        # Process empty name
        result = await tool.execute(
            {
                "user_id": str(test_user.id),
                "action": "process_response",
                "user_response": "",
            }
        )

        assert result.success is True
        assert result.data["is_valid"] is False
        assert "validation_error" in result.data

    @pytest.mark.asyncio
    async def test_process_response_extracts_goals(self, db_session: AsyncSession, test_user: User):
        """Process response should extract goals from user response."""
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        tool = ToolOnboardingShort(db_session=db_session)

        # Start and advance to goals step
        await tool.execute({"user_id": str(test_user.id), "action": "start"})
        await tool.execute(
            {
                "user_id": str(test_user.id),
                "action": "process_response",
                "user_response": "ok",
            }
        )
        await tool.execute(
            {
                "user_id": str(test_user.id),
                "action": "process_response",
                "user_response": "João",
            }
        )

        # Process goals
        result = await tool.execute(
            {
                "user_id": str(test_user.id),
                "action": "process_response",
                "user_response": "Crescer na carreira, melhorar saúde",
            }
        )

        assert result.success is True
        assert result.data["is_valid"] is True
        assert "extracted_data" in result.data
        assert "goals" in result.data["extracted_data"]


class TestToolOnboardingShortGetStatus:
    """Test ToolOnboardingShort get_status action."""

    @pytest.mark.asyncio
    async def test_get_status_returns_current_state(
        self, db_session: AsyncSession, test_user: User
    ):
        """Get status should return current onboarding state."""
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        tool = ToolOnboardingShort(db_session=db_session)

        # Start onboarding
        await tool.execute({"user_id": str(test_user.id), "action": "start"})

        # Get status
        result = await tool.execute({"user_id": str(test_user.id), "action": "get_status"})

        assert result.success is True
        assert result.data["status"] == "IN_PROGRESS"
        assert result.data["current_step"] == "welcome"
        assert "progress_percent" in result.data

    @pytest.mark.asyncio
    async def test_get_status_for_new_user(self, db_session: AsyncSession, test_user: User):
        """Get status for new user should show NOT_STARTED."""
        from src.tools.onboarding.skill_onboarding_short import ToolOnboardingShort

        tool = ToolOnboardingShort(db_session=db_session)
        result = await tool.execute({"user_id": str(test_user.id), "action": "get_status"})

        assert result.success is True
        assert result.data["status"] == "NOT_STARTED"


class TestOnboardingStepDefinitions:
    """Test onboarding step definitions and prompts."""

    def test_step_definitions_exist(self):
        """All steps should have definitions with prompts."""
        from src.tools.onboarding.steps import STEP_DEFINITIONS, OnboardingStep

        for step in OnboardingStep:
            assert step in STEP_DEFINITIONS
            assert "prompt" in STEP_DEFINITIONS[step]

    def test_step_sequence_is_correct(self):
        """Steps should be in correct sequence."""
        from src.tools.onboarding.steps import STEP_SEQUENCE, OnboardingStep

        expected = [
            OnboardingStep.WELCOME,
            OnboardingStep.NAME,
            OnboardingStep.GOALS,
            OnboardingStep.PREFERENCES,
            OnboardingStep.CONCLUSION,
        ]
        assert STEP_SEQUENCE == expected

    def test_get_next_step(self):
        """get_next_step should return correct next step."""
        from src.tools.onboarding.steps import OnboardingStep, get_next_step

        assert get_next_step(OnboardingStep.WELCOME) == OnboardingStep.NAME
        assert get_next_step(OnboardingStep.NAME) == OnboardingStep.GOALS
        assert get_next_step(OnboardingStep.GOALS) == OnboardingStep.PREFERENCES
        assert get_next_step(OnboardingStep.PREFERENCES) == OnboardingStep.CONCLUSION
        assert get_next_step(OnboardingStep.CONCLUSION) is None


class TestOnboardingValidators:
    """Test onboarding step validators."""

    def test_validate_name_accepts_valid_name(self):
        """Name validator should accept valid name."""
        from src.tools.onboarding.validators import validate_name

        is_valid, error = validate_name("João Silva")
        assert is_valid is True
        assert error is None

    def test_validate_name_rejects_empty(self):
        """Name validator should reject empty name."""
        from src.tools.onboarding.validators import validate_name

        is_valid, error = validate_name("")
        assert is_valid is False
        assert error is not None

    def test_validate_name_rejects_whitespace_only(self):
        """Name validator should reject whitespace-only name."""
        from src.tools.onboarding.validators import validate_name

        is_valid, error = validate_name("   ")
        assert is_valid is False
        assert error is not None

    def test_validate_goals_accepts_valid_goals(self):
        """Goals validator should accept valid goals text."""
        from src.tools.onboarding.validators import validate_goals

        is_valid, error = validate_goals("Crescer na carreira e cuidar da saúde")
        assert is_valid is True
        assert error is None

    def test_validate_goals_rejects_empty(self):
        """Goals validator should reject empty goals."""
        from src.tools.onboarding.validators import validate_goals

        is_valid, error = validate_goals("")
        assert is_valid is False
        assert error is not None

    def test_extract_goals_from_text(self):
        """extract_goals should extract goals from text."""
        from src.tools.onboarding.validators import extract_goals

        text = "Quero crescer na carreira e melhorar minha saúde"
        goals = extract_goals(text)
        assert isinstance(goals, list)
        assert len(goals) >= 1

    def test_validate_timezone_accepts_valid(self):
        """Timezone validator should accept valid timezone."""
        from src.tools.onboarding.validators import validate_preferences

        is_valid, error = validate_preferences("America/Sao_Paulo, pt-BR")
        assert is_valid is True
        assert error is None

    def test_extract_preferences(self):
        """extract_preferences should extract timezone and language."""
        from src.tools.onboarding.validators import extract_preferences

        text = "America/Sao_Paulo, português"
        prefs = extract_preferences(text)
        assert "timezone" in prefs
