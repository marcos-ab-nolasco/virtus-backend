"""Tests for onboarding tools.

Tests SaveUserProfileTool, SaveUserPreferencesTool, and CompleteOnboardingStepTool
with real database sessions.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_preferences import ContactFrequency, UserPreferences
from src.db.models.user_profile import UserProfile
from src.tools.onboarding_tools_legacy import (
    CompleteOnboardingStepTool,
    SaveUserPreferencesTool,
    SaveUserProfileTool,
)


class TestSaveUserProfileTool:
    """Test SaveUserProfileTool."""

    @pytest.mark.asyncio
    async def test_save_user_profile_saves_preferred_name(
        self, db_session: AsyncSession, test_user: User
    ):
        """Should save preferred_name to UserProfile."""
        tool = SaveUserProfileTool(db_session=db_session)

        result = await tool.execute({"user_id": str(test_user.id), "preferred_name": "Zé"})

        assert result.success is True

        # Verify in DB
        db_result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = db_result.scalar_one()
        assert profile.preferred_name == "Zé"

    @pytest.mark.asyncio
    async def test_save_user_profile_saves_onboarding_data(
        self, db_session: AsyncSession, test_user: User
    ):
        """Should merge onboarding_data into UserProfile."""
        # Initialize onboarding_data
        db_result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = db_result.scalar_one()
        profile.onboarding_data = {"existing_key": "value"}
        await db_session.commit()

        tool = SaveUserProfileTool(db_session=db_session)
        result = await tool.execute(
            {
                "user_id": str(test_user.id),
                "onboarding_data": {"work_context": "freelancer"},
            }
        )

        assert result.success is True

        await db_session.refresh(profile)
        assert profile.onboarding_data["work_context"] == "freelancer"
        assert profile.onboarding_data["existing_key"] == "value"


class TestSaveUserPreferencesTool:
    """Test SaveUserPreferencesTool."""

    @pytest.mark.asyncio
    async def test_save_user_preferences_saves_contact_frequency(
        self, db_session: AsyncSession, test_user: User
    ):
        """Should save contact_frequency to UserPreferences."""
        tool = SaveUserPreferencesTool(db_session=db_session)

        result = await tool.execute(
            {"user_id": str(test_user.id), "contact_frequency": "FREQUENTLY"}
        )

        assert result.success is True

        # Verify in DB
        db_result = await db_session.execute(
            select(UserPreferences).where(UserPreferences.user_id == test_user.id)
        )
        prefs = db_result.scalar_one()
        assert prefs.contact_frequency == ContactFrequency.FREQUENTLY

    @pytest.mark.asyncio
    async def test_save_user_preferences_saves_timezone(
        self, db_session: AsyncSession, test_user: User
    ):
        """Should save timezone to UserPreferences."""
        tool = SaveUserPreferencesTool(db_session=db_session)

        result = await tool.execute({"user_id": str(test_user.id), "timezone": "America/Sao_Paulo"})

        assert result.success is True

        db_result = await db_session.execute(
            select(UserPreferences).where(UserPreferences.user_id == test_user.id)
        )
        prefs = db_result.scalar_one()
        assert prefs.timezone == "America/Sao_Paulo"

    @pytest.mark.asyncio
    async def test_save_user_preferences_rejects_invalid_frequency(
        self, db_session: AsyncSession, test_user: User
    ):
        """Should reject invalid contact_frequency values."""
        tool = SaveUserPreferencesTool(db_session=db_session)

        result = await tool.execute({"user_id": str(test_user.id), "contact_frequency": "INVALID"})

        assert result.success is False
        assert "Invalid contact_frequency" in (result.error or "")


class TestCompleteOnboardingStepTool:
    """Test CompleteOnboardingStepTool."""

    @pytest.mark.asyncio
    async def test_complete_onboarding_step_advances_step(
        self, db_session: AsyncSession, test_user: User
    ):
        """Should advance to next onboarding step."""
        from src.services.onboarding import start_onboarding

        await start_onboarding(db_session, test_user.id)

        tool = CompleteOnboardingStepTool(db_session=db_session)
        result = await tool.execute({"user_id": str(test_user.id), "step": "intro"})

        assert result.success is True
        assert result.data is not None
        assert result.data["completed_step"] == "intro"
        assert result.data["current_step"] == "name"

    @pytest.mark.asyncio
    async def test_complete_onboarding_step_auto_starts(
        self, db_session: AsyncSession, test_user: User
    ):
        """Should auto-start onboarding if NOT_STARTED."""
        tool = CompleteOnboardingStepTool(db_session=db_session)
        result = await tool.execute({"user_id": str(test_user.id), "step": "intro"})

        assert result.success is True
        # After auto-start (intro) + advance, should be at "name"
        assert result.data is not None
        assert result.data["current_step"] == "name"

    @pytest.mark.asyncio
    async def test_complete_onboarding_step_at_closing_completes(
        self, db_session: AsyncSession, test_user: User
    ):
        """Should complete onboarding when closing step is reached."""
        from src.services.onboarding import advance_step, start_onboarding

        await start_onboarding(db_session, test_user.id)

        # Advance to closing: intro->name->freq->routine->goals->calendar->closing
        for _ in range(6):
            await advance_step(db_session, test_user.id)

        tool = CompleteOnboardingStepTool(db_session=db_session)
        result = await tool.execute({"user_id": str(test_user.id), "step": "closing"})

        assert result.success is True
        assert result.data is not None
        assert result.data["status"] == "COMPLETED"
