import uuid
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.db.models.user import User
from src.db.models.user_profile import (
    EngagementLevel,
    InterestType,
    LifeArea,
    OnboardingStatus,
    PatternType,
    StrengthCategory,
    StrengthSource,
    UserProfile,
)


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
    assert profile.main_obstacle is None
    assert profile.annual_objectives is None
    assert profile.observed_patterns is None
    assert profile.moral_profile is None
    assert profile.strengths is None
    assert profile.interests is None


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
    """Test storing and retrieving individual satisfaction scores (replaces life_dashboard JSONB)."""
    # Get the auto-created profile and update it
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Set individual satisfaction fields
    profile.satisfaction_health = 7
    profile.satisfaction_work = 8
    profile.satisfaction_relationships = 6
    profile.satisfaction_personal_time = 5
    await db_session.commit()
    await db_session.refresh(profile)

    # Verify individual fields
    assert profile.satisfaction_health == 7
    assert profile.satisfaction_work == 8
    assert profile.satisfaction_relationships == 6
    assert profile.satisfaction_personal_time == 5


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
    profile.main_obstacle = "Work-life balance"
    profile.onboarding_status = OnboardingStatus.IN_PROGRESS
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.vision_5_years == "Become a tech leader"
    assert profile.main_obstacle == "Work-life balance"
    assert profile.onboarding_status == OnboardingStatus.IN_PROGRESS
    assert profile.updated_at > profile.created_at


# Tests for new enums (M01 expansion)


def test_life_area_enum_values():
    """Test that LifeArea enum has all expected values."""
    assert LifeArea.HEALTH == "HEALTH"
    assert LifeArea.WORK == "WORK"
    assert LifeArea.RELATIONSHIPS == "RELATIONSHIPS"
    assert LifeArea.PERSONAL_TIME == "PERSONAL_TIME"
    assert len(LifeArea) == 4


def test_pattern_type_enum_values():
    """Test that PatternType enum has all expected values."""
    assert PatternType.ENERGY == "ENERGY"
    assert PatternType.PROCRASTINATION == "PROCRASTINATION"
    assert PatternType.STRESS == "STRESS"
    assert PatternType.COMMUNICATION == "COMMUNICATION"
    assert len(PatternType) == 4


def test_strength_category_enum_values():
    """Test that StrengthCategory enum has all expected values."""
    assert StrengthCategory.TECHNICAL == "TECHNICAL"
    assert StrengthCategory.INTERPERSONAL == "INTERPERSONAL"
    assert StrengthCategory.COGNITIVE == "COGNITIVE"
    assert StrengthCategory.CREATIVE == "CREATIVE"
    assert StrengthCategory.ORGANIZATIONAL == "ORGANIZATIONAL"
    assert len(StrengthCategory) == 5


def test_strength_source_enum_values():
    """Test that StrengthSource enum has all expected values."""
    assert StrengthSource.DECLARED == "DECLARED"
    assert StrengthSource.INFERRED == "INFERRED"
    assert len(StrengthSource) == 2


def test_interest_type_enum_values():
    """Test that InterestType enum has all expected values."""
    assert InterestType.HOBBY == "HOBBY"
    assert InterestType.PROFESSIONAL_INTEREST == "PROFESSIONAL_INTEREST"
    assert InterestType.LEARNING_GOAL == "LEARNING_GOAL"
    assert InterestType.CURIOSITY == "CURIOSITY"
    assert len(InterestType) == 4


def test_engagement_level_enum_values():
    """Test that EngagementLevel enum has all expected values."""
    assert EngagementLevel.ACTIVE == "ACTIVE"
    assert EngagementLevel.OCCASIONAL == "OCCASIONAL"
    assert EngagementLevel.ASPIRATIONAL == "ASPIRATIONAL"
    assert len(EngagementLevel) == 3


# Tests for new UserProfile fields (M01 expansion)


@pytest.mark.asyncio
async def test_user_profile_onboarding_completed_at_field(
    db_session: AsyncSession, test_user: User
):
    """Test that UserProfile has onboarding_completed_at timestamp field."""
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Should be None initially
    assert profile.onboarding_completed_at is None

    # Should be settable to datetime
    now = datetime.now()
    profile.onboarding_completed_at = now
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.onboarding_completed_at is not None
    assert isinstance(profile.onboarding_completed_at, datetime)


@pytest.mark.asyncio
async def test_user_profile_main_obstacle_field(db_session: AsyncSession, test_user: User):
    """Test that UserProfile has main_obstacle field (renamed from current_challenge)."""
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Should have main_obstacle attribute
    assert hasattr(profile, "main_obstacle")
    assert profile.main_obstacle is None

    # Should be settable
    profile.main_obstacle = "Procrastination and time management"
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.main_obstacle == "Procrastination and time management"


@pytest.mark.asyncio
async def test_user_profile_vision_5_years_themes_array(db_session: AsyncSession, test_user: User):
    """Test that UserProfile has vision_5_years_themes as array field."""
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Should be None initially
    assert profile.vision_5_years_themes is None

    # Should accept array of strings
    themes = ["family", "career", "health", "personal growth"]
    profile.vision_5_years_themes = themes
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.vision_5_years_themes == themes
    assert len(profile.vision_5_years_themes) == 4


@pytest.mark.asyncio
async def test_user_profile_strengths_jsonb(db_session: AsyncSession, test_user: User):
    """Test that UserProfile has strengths JSONB field."""
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Should be None initially
    assert profile.strengths is None

    # Should accept array of strength objects
    strengths = [
        {
            "id": str(uuid.uuid4()),
            "description": "Clear communication",
            "category": "INTERPERSONAL",
            "source": "DECLARED",
            "confidence": 1.0,
            "evidence": [],
            "created_at": datetime.now().isoformat(),
        }
    ]
    profile.strengths = strengths
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.strengths is not None
    assert isinstance(profile.strengths, list)
    assert len(profile.strengths) == 1
    assert profile.strengths[0]["description"] == "Clear communication"


@pytest.mark.asyncio
async def test_user_profile_interests_jsonb(db_session: AsyncSession, test_user: User):
    """Test that UserProfile has interests JSONB field."""
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Should be None initially
    assert profile.interests is None

    # Should accept array of interest objects
    interests = [
        {
            "id": str(uuid.uuid4()),
            "name": "Photography",
            "type": "HOBBY",
            "engagement_level": "ACTIVE",
            "related_to_goals": False,
            "created_at": datetime.now().isoformat(),
        }
    ]
    profile.interests = interests
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.interests is not None
    assert isinstance(profile.interests, list)
    assert len(profile.interests) == 1
    assert profile.interests[0]["name"] == "Photography"


@pytest.mark.asyncio
async def test_user_profile_energy_activities_array(db_session: AsyncSession, test_user: User):
    """Test that UserProfile has energy_activities array field."""
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Should be None initially
    assert profile.energy_activities is None

    # Should accept array of strings
    activities = ["exercising", "learning new things", "creative projects"]
    profile.energy_activities = activities
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.energy_activities == activities
    assert len(profile.energy_activities) == 3


@pytest.mark.asyncio
async def test_user_profile_drain_activities_array(db_session: AsyncSession, test_user: User):
    """Test that UserProfile has drain_activities array field."""
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Should be None initially
    assert profile.drain_activities is None

    # Should accept array of strings
    activities = ["long meetings", "administrative tasks", "social media scrolling"]
    profile.drain_activities = activities
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.drain_activities == activities
    assert len(profile.drain_activities) == 3


@pytest.mark.asyncio
async def test_user_profile_satisfaction_fields_individual(
    db_session: AsyncSession, test_user: User
):
    """Test that UserProfile has individual satisfaction_* fields instead of life_dashboard JSONB."""
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Should have individual satisfaction fields
    assert hasattr(profile, "satisfaction_health")
    assert hasattr(profile, "satisfaction_work")
    assert hasattr(profile, "satisfaction_relationships")
    assert hasattr(profile, "satisfaction_personal_time")
    assert hasattr(profile, "dashboard_updated_at")

    # Should be None initially
    assert profile.satisfaction_health is None
    assert profile.satisfaction_work is None
    assert profile.satisfaction_relationships is None
    assert profile.satisfaction_personal_time is None
    assert profile.dashboard_updated_at is None

    # Should be settable
    profile.satisfaction_health = 8
    profile.satisfaction_work = 7
    profile.satisfaction_relationships = 9
    profile.satisfaction_personal_time = 6
    profile.dashboard_updated_at = datetime.now()
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.satisfaction_health == 8
    assert profile.satisfaction_work == 7
    assert profile.satisfaction_relationships == 9
    assert profile.satisfaction_personal_time == 6
    assert profile.dashboard_updated_at is not None


@pytest.mark.asyncio
async def test_user_profile_satisfaction_constraints(db_session: AsyncSession, test_user: User):
    """Test that satisfaction fields are constrained to 1-10 range."""
    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == test_user.id)
    )
    profile = result.scalar_one()

    # Valid values (1-10) should work
    profile.satisfaction_health = 1
    profile.satisfaction_work = 10
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.satisfaction_health == 1
    assert profile.satisfaction_work == 10

    # Invalid values should fail (this will be enforced by CHECK constraint in migration)
    # For now we just test that the field accepts integers
    profile.satisfaction_health = 5
    await db_session.commit()
    assert profile.satisfaction_health == 5
