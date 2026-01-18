"""Tests for UserProfile onboarding-related fields.

Issue 3.1: Tests for new onboarding fields in UserProfile model.
Following TDD - RED phase: write failing tests first.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_profile import OnboardingStatus, UserProfile


class TestUserProfileOnboardingFields:
    """Test onboarding-related fields in UserProfile."""

    @pytest.mark.asyncio
    async def test_onboarding_started_at_field_exists(
        self, db_session: AsyncSession, test_user: User
    ):
        """UserProfile should have onboarding_started_at field (nullable)."""
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()

        # Field should exist and be nullable
        assert hasattr(profile, "onboarding_started_at")
        assert profile.onboarding_started_at is None

    @pytest.mark.asyncio
    async def test_onboarding_started_at_accepts_datetime(
        self, db_session: AsyncSession, test_user: User
    ):
        """onboarding_started_at should accept datetime values."""
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()

        # Set datetime value
        now = datetime.now(UTC)
        profile.onboarding_started_at = now
        await db_session.commit()
        await db_session.refresh(profile)

        assert profile.onboarding_started_at is not None
        assert isinstance(profile.onboarding_started_at, datetime)

    @pytest.mark.asyncio
    async def test_onboarding_current_step_field_exists(
        self, db_session: AsyncSession, test_user: User
    ):
        """UserProfile should have onboarding_current_step field (nullable string)."""
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()

        # Field should exist and be nullable
        assert hasattr(profile, "onboarding_current_step")
        assert profile.onboarding_current_step is None

    @pytest.mark.asyncio
    async def test_onboarding_current_step_accepts_string(
        self, db_session: AsyncSession, test_user: User
    ):
        """onboarding_current_step should accept string values for step names."""
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()

        # Test all expected step names
        steps = ["welcome", "name", "goals", "preferences", "conclusion"]

        for step in steps:
            profile.onboarding_current_step = step
            await db_session.commit()
            await db_session.refresh(profile)
            assert profile.onboarding_current_step == step

    @pytest.mark.asyncio
    async def test_onboarding_data_field_exists(self, db_session: AsyncSession, test_user: User):
        """UserProfile should have onboarding_data JSONB field (nullable)."""
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()

        # Field should exist and be nullable
        assert hasattr(profile, "onboarding_data")
        assert profile.onboarding_data is None

    @pytest.mark.asyncio
    async def test_onboarding_data_accepts_dict(self, db_session: AsyncSession, test_user: User):
        """onboarding_data should accept dictionary (JSONB) data."""
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()

        # Set JSONB data
        onboarding_data = {
            "name": "Test User Name",
            "goals": ["career growth", "health improvement"],
            "preferences": {
                "timezone": "America/Sao_Paulo",
                "language": "pt-BR",
            },
        }
        profile.onboarding_data = onboarding_data
        await db_session.commit()
        await db_session.refresh(profile)

        assert profile.onboarding_data is not None
        assert profile.onboarding_data["name"] == "Test User Name"
        assert len(profile.onboarding_data["goals"]) == 2
        assert profile.onboarding_data["preferences"]["timezone"] == "America/Sao_Paulo"

    @pytest.mark.asyncio
    async def test_onboarding_data_stores_conversation_history(
        self, db_session: AsyncSession, test_user: User
    ):
        """onboarding_data should store conversation history with timestamps."""
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()

        # Set conversation history
        now = datetime.now(UTC).isoformat()
        onboarding_data = {
            "conversation_history": [
                {"step": "welcome", "timestamp": now, "user_response": "Olá!"},
                {"step": "name", "timestamp": now, "user_response": "João"},
            ]
        }
        profile.onboarding_data = onboarding_data
        await db_session.commit()
        await db_session.refresh(profile)

        assert profile.onboarding_data["conversation_history"] is not None
        assert len(profile.onboarding_data["conversation_history"]) == 2
        assert profile.onboarding_data["conversation_history"][1]["user_response"] == "João"


class TestOnboardingStateTransitions:
    """Test onboarding state management with new fields."""

    @pytest.mark.asyncio
    async def test_start_onboarding_sets_fields_correctly(
        self, db_session: AsyncSession, test_user: User
    ):
        """Starting onboarding should set status, started_at, and current_step."""
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()

        # Initial state
        assert profile.onboarding_status == OnboardingStatus.NOT_STARTED
        assert profile.onboarding_started_at is None
        assert profile.onboarding_current_step is None

        # Start onboarding
        now = datetime.now(UTC)
        profile.onboarding_status = OnboardingStatus.IN_PROGRESS
        profile.onboarding_started_at = now
        profile.onboarding_current_step = "welcome"
        profile.onboarding_data = {}
        await db_session.commit()
        await db_session.refresh(profile)

        assert profile.onboarding_status == OnboardingStatus.IN_PROGRESS
        assert profile.onboarding_started_at is not None
        assert profile.onboarding_current_step == "welcome"
        assert profile.onboarding_data == {}

    @pytest.mark.asyncio
    async def test_complete_onboarding_sets_completed_at(
        self, db_session: AsyncSession, test_user: User
    ):
        """Completing onboarding should set completed_at and update status."""
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()

        # Set up in-progress state
        profile.onboarding_status = OnboardingStatus.IN_PROGRESS
        profile.onboarding_started_at = datetime.now(UTC) - timedelta(minutes=5)
        profile.onboarding_current_step = "conclusion"
        await db_session.commit()

        # Complete onboarding
        now = datetime.now(UTC)
        profile.onboarding_status = OnboardingStatus.COMPLETED
        profile.onboarding_completed_at = now
        await db_session.commit()
        await db_session.refresh(profile)

        assert profile.onboarding_status == OnboardingStatus.COMPLETED
        assert profile.onboarding_completed_at is not None
        assert profile.onboarding_started_at is not None

    @pytest.mark.asyncio
    async def test_reset_onboarding_clears_fields(self, db_session: AsyncSession, test_user: User):
        """Resetting onboarding should clear all onboarding fields."""
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()

        # Set up in-progress state with data
        profile.onboarding_status = OnboardingStatus.IN_PROGRESS
        profile.onboarding_started_at = datetime.now(UTC)
        profile.onboarding_current_step = "goals"
        profile.onboarding_data = {"name": "João", "goals": ["test"]}
        await db_session.commit()

        # Reset onboarding
        profile.onboarding_status = OnboardingStatus.NOT_STARTED
        profile.onboarding_started_at = None
        profile.onboarding_current_step = None
        profile.onboarding_data = None
        await db_session.commit()
        await db_session.refresh(profile)

        assert profile.onboarding_status == OnboardingStatus.NOT_STARTED
        assert profile.onboarding_started_at is None
        assert profile.onboarding_current_step is None
        assert profile.onboarding_data is None


class TestUserProfileResponseSchema:
    """Test that UserProfileResponse schema includes new onboarding fields."""

    def test_schema_includes_onboarding_started_at(self):
        """UserProfileResponse schema should include onboarding_started_at."""
        from src.schemas.user_profile import UserProfileResponse

        # Check field is in schema
        fields = UserProfileResponse.model_fields
        assert "onboarding_started_at" in fields

    def test_schema_includes_onboarding_current_step(self):
        """UserProfileResponse schema should include onboarding_current_step."""
        from src.schemas.user_profile import UserProfileResponse

        fields = UserProfileResponse.model_fields
        assert "onboarding_current_step" in fields

    def test_schema_includes_onboarding_data(self):
        """UserProfileResponse schema should include onboarding_data."""
        from src.schemas.user_profile import UserProfileResponse

        fields = UserProfileResponse.model_fields
        assert "onboarding_data" in fields
