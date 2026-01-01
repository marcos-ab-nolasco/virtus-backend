"""Tests for profile API endpoints.

Following TDD RED-GREEN-REFACTOR cycle.
"""

import pytest
from httpx import AsyncClient

from src.db.models.user import User


@pytest.mark.asyncio
async def test_get_my_profile_success(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test GET /api/v1/me/profile returns user profile."""
    response = await client.get("/api/v1/me/profile", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user.id)
    assert data["onboarding_status"] == "not_started"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_my_profile_unauthenticated(client: AsyncClient):
    """Test GET /api/v1/me/profile without auth returns 401."""
    response = await client.get("/api/v1/me/profile")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_my_profile_update_vision(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/profile updates vision field."""
    payload = {"vision_5_years": "Become a tech leader in AI"}

    response = await client.patch("/api/v1/me/profile", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["vision_5_years"] == "Become a tech leader in AI"
    assert data["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_patch_my_profile_update_annual_objectives(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/profile updates annual_objectives JSONB."""
    payload = {
        "annual_objectives": [
            {
                "id": "obj-1",
                "description": "Complete AWS certification",
                "life_area": "work",
                "priority": 1,
            }
        ]
    }

    response = await client.patch("/api/v1/me/profile", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["annual_objectives"]) == 1
    assert data["annual_objectives"][0]["description"] == "Complete AWS certification"


@pytest.mark.asyncio
async def test_patch_my_profile_invalid_jsonb_structure(client: AsyncClient, auth_headers: dict):
    """Test PATCH /api/v1/me/profile with invalid JSONB raises 422."""
    payload = {
        "annual_objectives": [
            {"id": "obj-1", "description": "Missing required fields"}  # Missing life_area, priority
        ]
    }

    response = await client.patch("/api/v1/me/profile", json=payload, headers=auth_headers)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_patch_my_profile_unauthenticated(client: AsyncClient):
    """Test PATCH /api/v1/me/profile without auth returns 401."""
    payload = {"vision_5_years": "Test"}

    response = await client.patch("/api/v1/me/profile", json=payload)

    assert response.status_code == 401
