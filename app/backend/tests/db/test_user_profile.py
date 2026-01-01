import uuid
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.db.models.user import User
from src.db.models.user_profile import OnboardingStatus, UserProfile


@pytest.mark.asyncio
async def test_user_has_auto_created_profile(db_session: AsyncSession, test_user: User):
    """Test that UserProfile is automatically created when User is created."""
    # Query for the auto-created profile
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    assert profile.id is not None
    assert isinstance(profile.id, uuid.UUID)
    assert profile.user_id == test_user.id
    assert profile.onboarding_status == OnboardingStatus.NOT_STARTED
    assert isinstance(profile.created_at, datetime)
    assert isinstance(profile.updated_at, datetime)


@pytest.mark.asyncio
async def test_user_profile_requires_user_id(db_session: AsyncSession):
    """Test that UserProfile requires a user_id."""
    profile = UserProfile(
        onboarding_status=OnboardingStatus.NOT_STARTED,
    )

    db_session.add(profile)

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_user_profile_unique_constraint_on_user_id(db_session: AsyncSession, test_user: User):
    """Test that only one UserProfile can exist per user."""
    # test_user already has an auto-created profile
    # Try to create a second profile for the same user
    profile2 = UserProfile(
        user_id=test_user.id,
        onboarding_status=OnboardingStatus.IN_PROGRESS,
    )
    db_session.add(profile2)

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_user_profile_relationship_with_user(db_session: AsyncSession, test_user: User):
    """Test that UserProfile has a relationship with User."""
    # Get the auto-created profile
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Access relationship
    assert profile.user is not None
    assert profile.user.id == test_user.id
    assert profile.user.email == test_user.email


@pytest.mark.asyncio
async def test_user_profile_cascade_delete_with_user(db_session: AsyncSession, test_user: User):
    """Test that deleting a User cascades to UserProfile."""
    # Get the auto-created profile
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()
    profile_id = profile.id

    # Delete the user
    await db_session.delete(test_user)
    await db_session.commit()

    # Verify profile was also deleted
    result = await db_session.execute(select(UserProfile).where(UserProfile.id == profile_id))
    deleted_profile = result.scalar_one_or_none()
    assert deleted_profile is None


@pytest.mark.asyncio
async def test_user_profile_jsonb_fields_nullable(db_session: AsyncSession, test_user: User):
    """Test that JSONB fields are null by default in auto-created profile."""
    # Get the auto-created profile
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Verify JSONB fields are null
    assert profile.vision_5_years is None
    assert profile.current_challenge is None
    assert profile.annual_objectives is None
    assert profile.life_dashboard is None
    assert profile.observed_patterns is None
    assert profile.moral_profile is None


@pytest.mark.asyncio
async def test_annual_objectives_jsonb_structure(db_session: AsyncSession, test_user: User):
    """Test storing and retrieving annual_objectives JSONB data."""
    annual_objectives = [
        {
            "id": "obj-1",
            "description": "Complete professional certification",
            "life_area": "work",
            "priority": 1,
        },
        {
            "id": "obj-2",
            "description": "Run a marathon",
            "life_area": "health",
            "priority": 2,
        },
    ]

    # Get the auto-created profile and update it
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    profile.onboarding_status = OnboardingStatus.IN_PROGRESS
    profile.annual_objectives = annual_objectives
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.annual_objectives is not None
    assert len(profile.annual_objectives) == 2
    assert profile.annual_objectives[0]["description"] == "Complete professional certification"
    assert profile.annual_objectives[1]["life_area"] == "health"


@pytest.mark.asyncio
async def test_life_dashboard_jsonb_structure(db_session: AsyncSession, test_user: User):
    """Test storing and retrieving life_dashboard JSONB data."""
    life_dashboard = {
        "health": 7,
        "work": 8,
        "relationships": 6,
        "personal_time": 5,
    }

    # Get the auto-created profile and update it
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    profile.life_dashboard = life_dashboard
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.life_dashboard is not None
    assert profile.life_dashboard["health"] == 7
    assert profile.life_dashboard["work"] == 8
    assert profile.life_dashboard["relationships"] == 6
    assert profile.life_dashboard["personal_time"] == 5


@pytest.mark.asyncio
async def test_moral_profile_jsonb_structure(db_session: AsyncSession, test_user: User):
    """Test storing and retrieving moral_profile JSONB data."""
    moral_profile = {
        "care": 0.8,
        "fairness": 0.7,
        "loyalty": 0.6,
        "authority": 0.4,
        "purity": 0.5,
        "liberty": 0.9,
    }

    # Get the auto-created profile and update it
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    profile.onboarding_status = OnboardingStatus.COMPLETED
    profile.moral_profile = moral_profile
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.moral_profile is not None
    assert profile.moral_profile["care"] == 0.8
    assert profile.moral_profile["liberty"] == 0.9


@pytest.mark.asyncio
async def test_onboarding_status_enum_validation(db_session: AsyncSession):
    """Test that onboarding_status uses valid enum values."""
    # Test all valid enum values by creating different users and updating their profiles
    for status in [
        OnboardingStatus.NOT_STARTED,
        OnboardingStatus.IN_PROGRESS,
        OnboardingStatus.COMPLETED,
    ]:
        # Create a new user (which auto-creates profile)
        user = User(
            email=f"test_{status.value}@example.com",
            hashed_password=hash_password("testpassword123"),
            full_name=f"Test User {status.value}",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Get the auto-created profile
        result = await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        profile = result.scalar_one()

        # Update the status
        profile.onboarding_status = status
        await db_session.commit()
        await db_session.refresh(profile)

        assert profile.onboarding_status == status


@pytest.mark.asyncio
async def test_observed_patterns_jsonb_structure(db_session: AsyncSession, test_user: User):
    """Test storing and retrieving observed_patterns JSONB data."""
    observed_patterns = [
        {
            "pattern_type": "productivity",
            "description": "Most productive in morning hours",
            "confidence": 0.85,
        },
        {
            "pattern_type": "energy",
            "description": "Energy drops after lunch",
            "confidence": 0.72,
        },
    ]

    # Get the auto-created profile and update it
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    profile.observed_patterns = observed_patterns
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.observed_patterns is not None
    assert len(profile.observed_patterns) == 2
    assert profile.observed_patterns[0]["pattern_type"] == "productivity"
    assert profile.observed_patterns[1]["confidence"] == 0.72


@pytest.mark.asyncio
async def test_user_profile_update_fields(db_session: AsyncSession, test_user: User):
    """Test updating UserProfile fields."""
    # Get the auto-created profile
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Update fields
    profile.vision_5_years = "Become a tech leader"
    profile.current_challenge = "Work-life balance"
    profile.onboarding_status = OnboardingStatus.IN_PROGRESS
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.vision_5_years == "Become a tech leader"
    assert profile.current_challenge == "Work-life balance"
    assert profile.onboarding_status == OnboardingStatus.IN_PROGRESS
    assert profile.updated_at > profile.created_at
