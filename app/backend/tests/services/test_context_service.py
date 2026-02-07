"""Tests for context service.

Tests the build_permanent_context function that assembles
user context for AI agent consumption.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_preferences import ContactFrequency
from src.services.context import build_permanent_context


@pytest.mark.asyncio
async def test_build_permanent_context_basic(db_session: AsyncSession, test_user: User):
    """Test building basic permanent context."""
    context = await build_permanent_context(db_session, test_user.id)

    assert "user" in context
    assert context["user"]["id"] == str(test_user.id)
    assert context["user"]["email"] == test_user.email
    assert context["user"]["full_name"] == test_user.full_name


@pytest.mark.asyncio
async def test_build_permanent_context_includes_preferences(
    db_session: AsyncSession, test_user: User
):
    """Test that context includes user preferences."""
    context = await build_permanent_context(db_session, test_user.id)

    assert "preferences" in context
    assert context["preferences"] is not None
    assert "timezone" in context["preferences"]
    assert "communication_style" in context["preferences"]


@pytest.mark.asyncio
async def test_build_permanent_context_includes_contact_frequency(
    db_session: AsyncSession, test_user: User
):
    """Test that contact_frequency is included in preferences context."""
    context = await build_permanent_context(db_session, test_user.id)

    assert "preferences" in context
    assert context["preferences"] is not None
    assert "contact_frequency" in context["preferences"]
    # Default value should be SOMETIMES
    assert context["preferences"]["contact_frequency"] == ContactFrequency.SOMETIMES.value


@pytest.mark.asyncio
async def test_build_permanent_context_includes_profile(db_session: AsyncSession, test_user: User):
    """Test that context includes user profile."""
    context = await build_permanent_context(db_session, test_user.id)

    assert "profile" in context
    assert context["profile"] is not None
    assert "onboarding_status" in context["profile"]


@pytest.mark.asyncio
async def test_build_permanent_context_includes_preferred_name(
    db_session: AsyncSession, test_user: User
):
    """Test that preferred_name is included in profile context."""
    context = await build_permanent_context(db_session, test_user.id)

    assert "profile" in context
    assert context["profile"] is not None
    assert "preferred_name" in context["profile"]


@pytest.mark.asyncio
async def test_build_permanent_context_includes_onboarding_current_step(
    db_session: AsyncSession, test_user: User
):
    """Test that onboarding_current_step is included in profile context."""
    context = await build_permanent_context(db_session, test_user.id)

    assert "profile" in context
    assert context["profile"] is not None
    assert "onboarding_current_step" in context["profile"]


@pytest.mark.asyncio
async def test_build_permanent_context_user_not_found(db_session: AsyncSession):
    """Test that context building fails for non-existent user."""
    fake_user_id = uuid.uuid4()

    with pytest.raises(ValueError, match="not found"):
        await build_permanent_context(db_session, fake_user_id)


@pytest.mark.asyncio
async def test_build_permanent_context_includes_calendar_integration(
    db_session: AsyncSession, test_user: User
):
    """Test that context includes calendar integration info."""
    context = await build_permanent_context(db_session, test_user.id)

    assert "calendar_integration" in context
    assert "connected" in context["calendar_integration"]


@pytest.mark.asyncio
async def test_build_permanent_context_profile_has_expected_fields(
    db_session: AsyncSession, test_user: User
):
    """Test that profile context has all expected fields."""
    context = await build_permanent_context(db_session, test_user.id)

    profile = context["profile"]
    expected_fields = [
        "onboarding_status",
        "onboarding_current_step",
        "onboarding_completed_at",
        "preferred_name",
        "vision_5_years",
        "vision_5_years_themes",
        "main_obstacle",
        "annual_objectives",
        "strengths",
        "interests",
        "energy_activities",
        "drain_activities",
        "life_satisfaction",
    ]

    for field in expected_fields:
        assert field in profile, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_build_permanent_context_preferences_has_expected_fields(
    db_session: AsyncSession, test_user: User
):
    """Test that preferences context has all expected fields."""
    context = await build_permanent_context(db_session, test_user.id)

    preferences = context["preferences"]
    expected_fields = [
        "timezone",
        "language",
        "communication_style",
        "contact_frequency",
        "coach_name",
        "checkin_settings",
        "weekly_review_day",
        "week_start_day",
    ]

    for field in expected_fields:
        assert field in preferences, f"Missing field: {field}"
