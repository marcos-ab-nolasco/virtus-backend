import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.db.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier
from src.db.models.user import User
from src.db.models.user_preferences import CommunicationStyle, UserPreferences, WeekDay
from src.db.models.user_profile import OnboardingStatus, UserProfile


@pytest.mark.asyncio
async def test_user_registration_creates_profile(db_session: AsyncSession):
    """Test that creating a User automatically creates a UserProfile."""
    # Create user
    user = User(
        email="newuser@example.com",
        hashed_password=hash_password("password123"),
        full_name="New User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Check that profile was created automatically
    result = await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()

    assert profile is not None
    assert profile.user_id == user.id
    assert profile.onboarding_status == OnboardingStatus.NOT_STARTED


@pytest.mark.asyncio
async def test_user_registration_creates_preferences(db_session: AsyncSession):
    """Test that creating a User automatically creates UserPreferences."""
    # Create user
    user = User(
        email="anotheruser@example.com",
        hashed_password=hash_password("password123"),
        full_name="Another User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Check that preferences were created automatically
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    preferences = result.scalar_one_or_none()

    assert preferences is not None
    assert preferences.user_id == user.id


@pytest.mark.asyncio
async def test_profile_has_default_onboarding_status(db_session: AsyncSession):
    """Test that auto-created profile has NOT_STARTED onboarding status."""
    user = User(
        email="statustest@example.com",
        hashed_password=hash_password("password123"),
        full_name="Status Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    result = await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one()

    assert profile.onboarding_status == OnboardingStatus.NOT_STARTED
    assert profile.vision_5_years is None
    assert profile.main_obstacle is None
    assert profile.annual_objectives is None


@pytest.mark.asyncio
async def test_preferences_have_default_values(db_session: AsyncSession):
    """Test that auto-created preferences have correct default values."""
    user = User(
        email="defaultstest@example.com",
        hashed_password=hash_password("password123"),
        full_name="Defaults Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    preferences = result.scalar_one()

    assert preferences.timezone == "UTC"
    assert preferences.morning_checkin_enabled is True
    assert preferences.evening_checkin_enabled is True
    assert preferences.weekly_review_day == WeekDay.SUNDAY
    assert preferences.communication_style == CommunicationStyle.DIRECT
    assert preferences.coach_name == "Virtus"


@pytest.mark.asyncio
async def test_transaction_rollback_prevents_orphans(db_session: AsyncSession):
    """Test that rolling back user creation doesn't leave orphaned profile/preferences."""
    user = User(
        email="rollbacktest@example.com",
        hashed_password=hash_password("password123"),
        full_name="Rollback Test",
    )
    db_session.add(user)
    await db_session.flush()  # Trigger auto-creation

    user_id = user.id

    # Rollback the transaction
    await db_session.rollback()

    # Verify no orphaned records exist
    result_profile = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result_profile.scalar_one_or_none()

    result_prefs = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    preferences = result_prefs.scalar_one_or_none()

    assert profile is None
    assert preferences is None


@pytest.mark.asyncio
async def test_auto_creation_via_relationship_access(db_session: AsyncSession):
    """Test that profile and preferences can be accessed via User relationship."""
    user = User(
        email="reltest@example.com",
        hashed_password=hash_password("password123"),
        full_name="Relationship Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Access via relationship (should be loaded)
    # Need to explicitly load relationships
    await db_session.refresh(user, ["profile", "preferences"])

    assert user.profile is not None
    assert user.preferences is not None
    assert user.profile.user_id == user.id
    assert user.preferences.user_id == user.id


@pytest.mark.asyncio
async def test_multiple_users_each_get_own_profile_and_preferences(db_session: AsyncSession):
    """Test that multiple users each get their own profile and preferences."""
    users = []
    for i in range(3):
        user = User(
            email=f"multiuser{i}@example.com",
            hashed_password=hash_password("password123"),
            full_name=f"Multi User {i}",
        )
        db_session.add(user)
        users.append(user)

    await db_session.commit()

    # Verify each user has their own profile and preferences
    for user in users:
        await db_session.refresh(user)

        result_profile = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        profile = result_profile.scalar_one()

        result_prefs = await db_session.execute(
            select(UserPreferences).where(UserPreferences.user_id == user.id)
        )
        preferences = result_prefs.scalar_one()

        assert profile.user_id == user.id
        assert preferences.user_id == user.id


@pytest.mark.asyncio
async def test_auto_creation_does_not_duplicate(db_session: AsyncSession):
    """Test that auto-creation doesn't create duplicates on user update."""
    user = User(
        email="duptest@example.com",
        hashed_password=hash_password("password123"),
        full_name="Duplicate Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Count initial profile and preferences
    result_profile = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profiles_before = result_profile.all()

    result_prefs = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    prefs_before = result_prefs.all()

    assert len(profiles_before) == 1
    assert len(prefs_before) == 1

    # Update user and commit again
    user.full_name = "Updated Name"
    await db_session.commit()

    # Verify no duplicates were created
    result_profile_after = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profiles_after = result_profile_after.all()

    result_prefs_after = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    prefs_after = result_prefs_after.all()

    assert len(profiles_after) == 1
    assert len(prefs_after) == 1


@pytest.mark.asyncio
async def test_user_registration_creates_subscription(db_session: AsyncSession):
    """Test that creating a User automatically creates a Subscription."""
    # Create user
    user = User(
        email="subscriptiontest@example.com",
        hashed_password=hash_password("password123"),
        full_name="Subscription Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Check that subscription was created automatically
    result = await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    subscription = result.scalar_one_or_none()

    assert subscription is not None
    assert subscription.user_id == user.id
    assert subscription.tier == SubscriptionTier.FREE
    assert subscription.status == SubscriptionStatus.ACTIVE


@pytest.mark.asyncio
async def test_user_registration_creates_profile_preferences_and_subscription(
    db_session: AsyncSession,
):
    """Test that creating a User automatically creates Profile, Preferences, AND Subscription."""
    # Create user
    user = User(
        email="completetest@example.com",
        hashed_password=hash_password("password123"),
        full_name="Complete Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Check that all three were created automatically
    result_profile = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result_profile.scalar_one_or_none()

    result_prefs = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    preferences = result_prefs.scalar_one_or_none()

    result_sub = await db_session.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = result_sub.scalar_one_or_none()

    assert profile is not None
    assert preferences is not None
    assert subscription is not None
    assert profile.user_id == user.id
    assert preferences.user_id == user.id
    assert subscription.user_id == user.id


@pytest.mark.asyncio
async def test_transaction_rollback_prevents_orphaned_subscription(db_session: AsyncSession):
    """Test that rolling back user creation doesn't leave orphaned subscription."""
    user = User(
        email="subrollback@example.com",
        hashed_password=hash_password("password123"),
        full_name="Sub Rollback Test",
    )
    db_session.add(user)
    await db_session.flush()  # Trigger auto-creation

    user_id = user.id

    # Rollback the transaction
    await db_session.rollback()

    # Verify no orphaned subscription exists
    result_sub = await db_session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result_sub.scalar_one_or_none()

    assert subscription is None
