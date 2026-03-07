"""Tests for setup tools (SaveUserProfileTool, SaveUserPreferencesTool).

Tests the tools used by SetupAgent during the initial setup conversation.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_preferences import ContactFrequency, UserPreferences
from src.db.models.user_profile import UserProfile
from src.tools.setup_tools import SaveUserPreferencesTool, SaveUserProfileTool


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
    async def test_save_user_profile_missing_user_fails(self, db_session: AsyncSession):
        """Should fail gracefully when user does not exist."""
        tool = SaveUserProfileTool(db_session=db_session)
        result = await tool.execute(
            {"user_id": "00000000-0000-0000-0000-000000000000", "preferred_name": "X"}
        )
        assert result.success is False


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
