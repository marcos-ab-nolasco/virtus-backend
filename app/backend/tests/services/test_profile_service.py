"""Tests for profile service layer.

Following TDD RED-GREEN-REFACTOR cycle:
- RED: Write failing tests first
- GREEN: Implement minimal code to pass
- REFACTOR: Clean up and improve
"""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.schemas.user_profile import UserProfileUpdate
from src.services import profile as profile_service


@pytest.mark.asyncio
async def test_get_user_profile_success(db_session: AsyncSession, test_user: User):
    """Test getting user profile successfully."""
    profile = await profile_service.get_user_profile(db_session, test_user.id)

    assert profile is not None
    assert profile.user_id == test_user.id


@pytest.mark.asyncio
async def test_get_user_profile_not_found(db_session: AsyncSession):
    """Test getting profile for non-existent user raises 404."""
    fake_user_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await profile_service.get_user_profile(db_session, fake_user_id)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_update_user_profile_success(db_session: AsyncSession, test_user: User):
    """Test updating user profile successfully."""
    update_data = UserProfileUpdate(
        vision_5_years="Become a tech leader in 5 years",
        current_challenge="Work-life balance",
    )

    updated_profile = await profile_service.update_user_profile(
        db_session, test_user.id, update_data
    )

    assert updated_profile.vision_5_years == "Become a tech leader in 5 years"
    assert updated_profile.current_challenge == "Work-life balance"
    assert updated_profile.user_id == test_user.id


@pytest.mark.asyncio
async def test_update_user_profile_partial(db_session: AsyncSession, test_user: User):
    """Test partial update of user profile (only some fields)."""
    # First set some data
    update_data_1 = UserProfileUpdate(
        vision_5_years="Initial vision",
        current_challenge="Initial challenge",
    )
    await profile_service.update_user_profile(db_session, test_user.id, update_data_1)

    # Now update only one field
    update_data_2 = UserProfileUpdate(
        vision_5_years="Updated vision",
    )
    updated_profile = await profile_service.update_user_profile(
        db_session, test_user.id, update_data_2
    )

    assert updated_profile.vision_5_years == "Updated vision"
    assert updated_profile.current_challenge == "Initial challenge"  # Unchanged


@pytest.mark.asyncio
async def test_update_user_profile_with_jsonb_fields(db_session: AsyncSession, test_user: User):
    """Test updating profile with JSONB fields."""
    update_data = UserProfileUpdate(
        annual_objectives=[
            {
                "id": "obj-1",
                "description": "Complete certification",
                "life_area": "work",
                "priority": 1,
            }
        ],
        life_dashboard={"health": 7, "work": 8, "relationships": 6, "personal_time": 5},
    )

    updated_profile = await profile_service.update_user_profile(
        db_session, test_user.id, update_data
    )

    assert updated_profile.annual_objectives is not None
    assert len(updated_profile.annual_objectives) == 1
    assert updated_profile.annual_objectives[0]["description"] == "Complete certification"
    assert updated_profile.life_dashboard is not None
    assert updated_profile.life_dashboard["health"] == 7


@pytest.mark.asyncio
async def test_update_user_profile_not_found(db_session: AsyncSession):
    """Test updating profile for non-existent user raises 404."""
    fake_user_id = uuid.uuid4()
    update_data = UserProfileUpdate(vision_5_years="Test vision")

    with pytest.raises(HTTPException) as exc_info:
        await profile_service.update_user_profile(db_session, fake_user_id, update_data)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_user_profile_empty_update(db_session: AsyncSession, test_user: User):
    """Test updating with no fields provided returns profile unchanged."""
    # Get initial profile
    initial_profile = await profile_service.get_user_profile(db_session, test_user.id)
    initial_vision = initial_profile.vision_5_years

    # Update with empty data
    update_data = UserProfileUpdate()
    updated_profile = await profile_service.update_user_profile(
        db_session, test_user.id, update_data
    )

    assert updated_profile.vision_5_years == initial_vision
    assert updated_profile.user_id == test_user.id


@pytest.mark.asyncio
async def test_get_user_profile_returns_fresh_data(db_session: AsyncSession, test_user: User):
    """Test that get_user_profile returns fresh data after update."""
    # Update profile
    update_data = UserProfileUpdate(vision_5_years="Fresh vision")
    await profile_service.update_user_profile(db_session, test_user.id, update_data)

    # Get profile again
    profile = await profile_service.get_user_profile(db_session, test_user.id)

    assert profile.vision_5_years == "Fresh vision"
