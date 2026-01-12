"""Tests for Subscription model."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.db.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier
from src.db.models.user import User


@pytest.mark.asyncio
async def test_user_has_auto_created_subscription_with_defaults(
    db_session: AsyncSession, test_user: User
):
    """Test that Subscription is automatically created with FREE tier when User is created."""
    # Query for the auto-created subscription
    result = await db_session.execute(
        select(Subscription).where(Subscription.user_id == test_user.id)
    )
    subscription = result.scalar_one()

    assert subscription.id is not None
    assert isinstance(subscription.id, uuid.UUID)
    assert subscription.user_id == test_user.id
    assert subscription.tier == SubscriptionTier.FREE
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert isinstance(subscription.start_date, datetime)
    assert subscription.end_date is None  # FREE tier has no end date
    assert subscription.trial_ends_at is None
    assert isinstance(subscription.created_at, datetime)
    assert isinstance(subscription.updated_at, datetime)


@pytest.mark.asyncio
async def test_subscription_unique_constraint(db_session: AsyncSession, test_user: User):
    """Test that only one Subscription can exist per user."""
    # test_user already has auto-created subscription
    # Try to create a second subscription for the same user
    subscription2 = Subscription(user_id=test_user.id)
    db_session.add(subscription2)

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_subscription_relationship_with_user(db_session: AsyncSession, test_user: User):
    """Test that Subscription has a relationship with User."""
    # Get the auto-created subscription
    result = await db_session.execute(
        select(Subscription).where(Subscription.user_id == test_user.id)
    )
    subscription = result.scalar_one()

    # Access relationship
    assert subscription.user is not None
    assert subscription.user.id == test_user.id
    assert subscription.user.email == test_user.email


@pytest.mark.asyncio
async def test_subscription_cascade_delete(db_session: AsyncSession, test_user: User):
    """Test that deleting a User cascades to Subscription."""
    # Get the auto-created subscription
    result = await db_session.execute(
        select(Subscription).where(Subscription.user_id == test_user.id)
    )
    subscription = result.scalar_one()
    subscription_id = subscription.id

    # Delete the user
    await db_session.delete(test_user)
    await db_session.commit()

    # Verify subscription was also deleted
    result = await db_session.execute(select(Subscription).where(Subscription.id == subscription_id))
    deleted_subscription = result.scalar_one_or_none()
    assert deleted_subscription is None


@pytest.mark.asyncio
async def test_subscription_tier_enum_values(db_session: AsyncSession, test_user: User):
    """Test that subscription tier can be updated to different values."""
    # Get the auto-created subscription
    result = await db_session.execute(
        select(Subscription).where(Subscription.user_id == test_user.id)
    )
    subscription = result.scalar_one()

    # Test updating to TRIAL
    subscription.tier = SubscriptionTier.TRIAL
    await db_session.commit()
    await db_session.refresh(subscription)
    assert subscription.tier == SubscriptionTier.TRIAL

    # Test updating to PAID
    subscription.tier = SubscriptionTier.PAID
    await db_session.commit()
    await db_session.refresh(subscription)
    assert subscription.tier == SubscriptionTier.PAID


@pytest.mark.asyncio
async def test_subscription_status_enum_values(db_session: AsyncSession, test_user: User):
    """Test that subscription status can be updated to different values."""
    # Get the auto-created subscription
    result = await db_session.execute(
        select(Subscription).where(Subscription.user_id == test_user.id)
    )
    subscription = result.scalar_one()

    # Test different status values
    for status in [
        SubscriptionStatus.CANCELLED,
        SubscriptionStatus.EXPIRED,
        SubscriptionStatus.TRIAL_ENDED,
        SubscriptionStatus.ACTIVE,
    ]:
        subscription.status = status
        await db_session.commit()
        await db_session.refresh(subscription)
        assert subscription.status == status


@pytest.mark.asyncio
async def test_subscription_tier_comparison(db_session: AsyncSession):
    """Test that subscription tier comparison works correctly."""
    # Test tier hierarchy: FREE < TRIAL < PAID
    assert SubscriptionTier.FREE < SubscriptionTier.TRIAL
    assert SubscriptionTier.TRIAL < SubscriptionTier.PAID
    assert SubscriptionTier.FREE < SubscriptionTier.PAID

    # Test greater than
    assert SubscriptionTier.PAID > SubscriptionTier.TRIAL
    assert SubscriptionTier.TRIAL > SubscriptionTier.FREE
    assert SubscriptionTier.PAID > SubscriptionTier.FREE

    # Test greater than or equal
    assert SubscriptionTier.FREE >= SubscriptionTier.FREE
    assert SubscriptionTier.TRIAL >= SubscriptionTier.FREE
    assert SubscriptionTier.PAID >= SubscriptionTier.TRIAL

    # Test less than or equal
    assert SubscriptionTier.FREE <= SubscriptionTier.FREE
    assert SubscriptionTier.FREE <= SubscriptionTier.TRIAL
    assert SubscriptionTier.TRIAL <= SubscriptionTier.PAID


@pytest.mark.asyncio
async def test_multiple_users_each_get_own_subscription(db_session: AsyncSession):
    """Test that multiple users each get their own subscription."""
    users = []
    for i in range(3):
        user = User(
            email=f"subuser{i}@example.com",
            hashed_password=hash_password("password123"),
            full_name=f"Sub User {i}",
        )
        db_session.add(user)
        users.append(user)

    await db_session.commit()

    # Verify each user has their own subscription
    for user in users:
        await db_session.refresh(user)

        result = await db_session.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subscription = result.scalar_one()

        assert subscription.user_id == user.id
        assert subscription.tier == SubscriptionTier.FREE
        assert subscription.status == SubscriptionStatus.ACTIVE


@pytest.mark.asyncio
async def test_subscription_auto_creation_does_not_duplicate(db_session: AsyncSession):
    """Test that auto-creation doesn't create duplicates on user update."""
    user = User(
        email="subduptest@example.com",
        hashed_password=hash_password("password123"),
        full_name="Sub Duplicate Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Count initial subscriptions
    result = await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    subscriptions_before = result.all()
    assert len(subscriptions_before) == 1

    # Update user and commit again
    user.full_name = "Updated Name"
    await db_session.commit()

    # Verify no duplicates were created
    result_after = await db_session.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscriptions_after = result_after.all()
    assert len(subscriptions_after) == 1


@pytest.mark.asyncio
async def test_subscription_auto_creation_via_relationship_access(db_session: AsyncSession):
    """Test that subscription can be accessed via User relationship."""
    user = User(
        email="subreltest@example.com",
        hashed_password=hash_password("password123"),
        full_name="Sub Relationship Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Access via relationship (should be loaded)
    # Need to explicitly load relationship
    await db_session.refresh(user, ["subscription"])

    assert user.subscription is not None
    assert user.subscription.user_id == user.id
    assert user.subscription.tier == SubscriptionTier.FREE


@pytest.mark.asyncio
async def test_subscription_transaction_rollback_prevents_orphans(db_session: AsyncSession):
    """Test that rolling back user creation doesn't leave orphaned subscription."""
    user = User(
        email="subrollbacktest@example.com",
        hashed_password=hash_password("password123"),
        full_name="Sub Rollback Test",
    )
    db_session.add(user)
    await db_session.flush()  # Trigger auto-creation

    user_id = user.id

    # Rollback the transaction
    await db_session.rollback()

    # Verify no orphaned subscription exists
    result = await db_session.execute(select(Subscription).where(Subscription.user_id == user_id))
    subscription = result.scalar_one_or_none()

    assert subscription is None
