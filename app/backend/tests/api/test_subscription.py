"""Tests for subscription API endpoints.

Following TDD RED-GREEN-REFACTOR cycle.
"""

import pytest
from httpx import AsyncClient

from src.db.models.user import User


@pytest.mark.asyncio
async def test_get_my_subscription_success(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test GET /api/v1/me/subscription returns user subscription."""
    response = await client.get("/api/v1/me/subscription", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user.id)
    assert data["tier"] == "FREE"
    assert data["status"] == "ACTIVE"
    assert data["start_date"] is not None
    assert data["end_date"] is None  # FREE tier has no end date
    assert data["trial_ends_at"] is None


@pytest.mark.asyncio
async def test_get_my_subscription_unauthenticated(client: AsyncClient):
    """Test GET /api/v1/me/subscription without auth returns 401."""
    response = await client.get("/api/v1/me/subscription")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_my_subscription_update_tier(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/subscription updates tier."""
    payload = {"tier": "PAID"}

    response = await client.patch("/api/v1/me/subscription", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "PAID"
    assert data["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_patch_my_subscription_update_status(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/subscription updates status."""
    payload = {"status": "CANCELLED"}

    response = await client.patch("/api/v1/me/subscription", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"
    assert data["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_patch_my_subscription_update_tier_and_status(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/subscription updates both tier and status."""
    payload = {"tier": "TRIAL", "status": "ACTIVE"}

    response = await client.patch("/api/v1/me/subscription", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "TRIAL"
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_patch_my_subscription_invalid_tier(client: AsyncClient, auth_headers: dict):
    """Test PATCH /api/v1/me/subscription with invalid tier raises 422."""
    payload = {"tier": "INVALID_TIER"}

    response = await client.patch("/api/v1/me/subscription", json=payload, headers=auth_headers)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_patch_my_subscription_invalid_status(client: AsyncClient, auth_headers: dict):
    """Test PATCH /api/v1/me/subscription with invalid status raises 422."""
    payload = {"status": "INVALID_STATUS"}

    response = await client.patch("/api/v1/me/subscription", json=payload, headers=auth_headers)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_patch_my_subscription_case_insensitive_tier(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/subscription accepts case-insensitive tier values."""
    payload = {"tier": "paid"}  # lowercase

    response = await client.patch("/api/v1/me/subscription", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "PAID"  # Should be normalized to uppercase


@pytest.mark.asyncio
async def test_patch_my_subscription_case_insensitive_status(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/subscription accepts case-insensitive status values."""
    payload = {"status": "cancelled"}  # lowercase

    response = await client.patch("/api/v1/me/subscription", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"  # Should be normalized to uppercase


@pytest.mark.asyncio
async def test_patch_my_subscription_partial_update(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/subscription supports partial updates."""
    # Update only tier
    payload = {"tier": "TRIAL"}
    response = await client.patch("/api/v1/me/subscription", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "TRIAL"
    assert data["status"] == "ACTIVE"  # Status should remain unchanged

    # Update only status
    payload = {"status": "TRIAL_ENDED"}
    response = await client.patch("/api/v1/me/subscription", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "TRIAL"  # Tier should remain unchanged
    assert data["status"] == "TRIAL_ENDED"


@pytest.mark.asyncio
async def test_patch_my_subscription_unauthenticated(client: AsyncClient):
    """Test PATCH /api/v1/me/subscription without auth returns 401."""
    payload = {"tier": "PAID"}
    response = await client.patch("/api/v1/me/subscription", json=payload)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_subscription_persists_across_requests(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test that subscription updates persist across multiple requests."""
    # Update to PAID
    payload = {"tier": "PAID", "status": "ACTIVE"}
    response = await client.patch("/api/v1/me/subscription", json=payload, headers=auth_headers)
    assert response.status_code == 200

    # Fetch again and verify
    response = await client.get("/api/v1/me/subscription", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "PAID"
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_get_subscription_response_includes_all_fields(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test that GET /api/v1/me/subscription returns all expected fields."""
    response = await client.get("/api/v1/me/subscription", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Verify all fields are present
    expected_fields = [
        "id",
        "user_id",
        "tier",
        "status",
        "start_date",
        "end_date",
        "trial_ends_at",
        "created_at",
        "updated_at",
    ]
    for field in expected_fields:
        assert field in data, f"Field {field} missing from response"
