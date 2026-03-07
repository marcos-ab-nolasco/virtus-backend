"""Tests for setup and module-based onboarding service functions."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_profile import OnboardingStatus


class TestCompleteSetup:
    """Tests for complete_setup()."""

    @pytest.mark.asyncio
    async def test_complete_setup_transitions_to_setup_completed(
        self, db_session: AsyncSession, test_user: User
    ):
        """complete_setup should set status to SETUP_COMPLETED."""
        from src.services.onboarding import complete_setup

        profile = await complete_setup(db_session, test_user.id)
        assert profile.onboarding_status == OnboardingStatus.SETUP_COMPLETED

    @pytest.mark.asyncio
    async def test_complete_setup_initialises_modules(
        self, db_session: AsyncSession, test_user: User
    ):
        """complete_setup should initialise 5 modules in onboarding_data."""
        from src.services.onboarding import complete_setup

        profile = await complete_setup(db_session, test_user.id)
        modules = (profile.onboarding_data or {}).get("modules", {})
        assert len(modules) == 5
        for phase in ["phase_1", "phase_2", "phase_3", "phase_4", "phase_5"]:
            assert modules[phase]["status"] == "not_started"

    @pytest.mark.asyncio
    async def test_complete_setup_is_idempotent(self, db_session: AsyncSession, test_user: User):
        """Calling complete_setup twice should not raise."""
        from src.services.onboarding import complete_setup

        await complete_setup(db_session, test_user.id)
        profile = await complete_setup(db_session, test_user.id)
        assert profile.onboarding_status == OnboardingStatus.SETUP_COMPLETED


class TestGetModuleProgress:
    """Tests for get_module_progress()."""

    @pytest.mark.asyncio
    async def test_returns_5_modules_when_no_setup(self, db_session: AsyncSession, test_user: User):
        """Should return 5 not_started modules even when setup not done."""
        from src.services.onboarding import get_module_progress

        modules = await get_module_progress(db_session, test_user.id)
        assert len(modules) == 5
        assert all(m["status"] == "not_started" for m in modules)

    @pytest.mark.asyncio
    async def test_returns_phases_in_order(self, db_session: AsyncSession, test_user: User):
        """Should return phases phase_1 through phase_5 in order."""
        from src.services.onboarding import get_module_progress

        modules = await get_module_progress(db_session, test_user.id)
        phases = [m["phase"] for m in modules]
        assert phases == ["phase_1", "phase_2", "phase_3", "phase_4", "phase_5"]


class TestStartModule:
    """Tests for start_module()."""

    @pytest.mark.asyncio
    async def test_start_module_creates_conversation(
        self, db_session: AsyncSession, test_user: User
    ):
        """start_module should return a conversation_id."""
        from src.services.onboarding import complete_setup, start_module

        await complete_setup(db_session, test_user.id)
        result = await start_module(db_session, test_user.id, 0)

        assert "conversation_id" in result
        assert result["conversation_id"] is not None

    @pytest.mark.asyncio
    async def test_start_module_marks_in_progress(self, db_session: AsyncSession, test_user: User):
        """start_module should mark the module as in_progress."""
        from src.services.onboarding import complete_setup, start_module

        await complete_setup(db_session, test_user.id)
        result = await start_module(db_session, test_user.id, 0)

        modules = result["modules"]
        phase_1 = next(m for m in modules if m["phase"] == "phase_1")
        assert phase_1["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_start_module_enrichment_for_completed_module(
        self, db_session: AsyncSession, test_user: User
    ):
        """Revisiting a completed module should set is_enrichment=True."""
        from src.services.onboarding import complete_module, complete_setup, start_module

        await complete_setup(db_session, test_user.id)
        await start_module(db_session, test_user.id, 0)
        await complete_module(db_session, test_user.id, "phase_1")

        # Revisit
        result = await start_module(db_session, test_user.id, 0)
        assert result["is_enrichment"] is True

    @pytest.mark.asyncio
    async def test_start_module_reuses_existing_conversation(
        self, db_session: AsyncSession, test_user: User
    ):
        """Calling start_module twice for same in_progress module reuses conversation."""
        from src.services.onboarding import complete_setup, start_module

        await complete_setup(db_session, test_user.id)
        result1 = await start_module(db_session, test_user.id, 1)
        result2 = await start_module(db_session, test_user.id, 1)

        assert result1["conversation_id"] == result2["conversation_id"]

    @pytest.mark.asyncio
    async def test_start_module_invalid_index_raises(
        self, db_session: AsyncSession, test_user: User
    ):
        """Invalid module index should raise HTTPException."""
        from fastapi import HTTPException

        from src.services.onboarding import start_module

        with pytest.raises(HTTPException):
            await start_module(db_session, test_user.id, 5)


class TestCompleteModule:
    """Tests for complete_module()."""

    @pytest.mark.asyncio
    async def test_complete_module_marks_completed(self, db_session: AsyncSession, test_user: User):
        """complete_module should mark the phase as completed."""
        from src.services.onboarding import (
            complete_module,
            complete_setup,
            get_module_progress,
            start_module,
        )

        await complete_setup(db_session, test_user.id)
        await start_module(db_session, test_user.id, 0)
        await complete_module(db_session, test_user.id, "phase_1")

        modules = await get_module_progress(db_session, test_user.id)
        phase_1 = next(m for m in modules if m["phase"] == "phase_1")
        assert phase_1["status"] == "completed"

    @pytest.mark.asyncio
    async def test_all_modules_complete_triggers_completed_status(
        self, db_session: AsyncSession, test_user: User
    ):
        """Completing all 5 modules should transition status to COMPLETED."""
        from src.services.onboarding import complete_module, complete_setup, start_module

        await complete_setup(db_session, test_user.id)

        for i, phase in enumerate(["phase_1", "phase_2", "phase_3", "phase_4", "phase_5"]):
            await start_module(db_session, test_user.id, i)
            profile = await complete_module(db_session, test_user.id, phase)

        assert profile.onboarding_status == OnboardingStatus.COMPLETED
