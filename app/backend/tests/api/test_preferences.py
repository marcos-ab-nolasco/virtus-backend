"""Tests for preferences API endpoints.

Following TDD RED-GREEN-REFACTOR cycle.
"""

import pytest
from httpx import AsyncClient

from src.db.models.user import User


@pytest.mark.asyncio
async def test_get_my_preferences_success(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test GET /api/v1/me/preferences returns user preferences."""
    response = await client.get("/api/v1/me/preferences", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user.id)
    assert data["timezone"] == "UTC"
    assert data["morning_checkin_enabled"] is True
    assert data["communication_style"] == "DIRECT"
    assert data["coach_name"] == "Virtus"


@pytest.mark.asyncio
async def test_get_my_preferences_unauthenticated(client: AsyncClient):
    """Test GET /api/v1/me/preferences without auth returns 401."""
    response = await client.get("/api/v1/me/preferences")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_my_preferences_update_timezone(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/preferences updates timezone."""
    payload = {"timezone": "America/Sao_Paulo"}

    response = await client.patch("/api/v1/me/preferences", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["timezone"] == "America/Sao_Paulo"
    assert data["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_patch_my_preferences_update_checkin_times(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/preferences updates check-in times."""
    payload = {
        "morning_checkin_time": "07:00:00",
        "evening_checkin_time": "22:30:00",
        "morning_checkin_enabled": False,
    }

    response = await client.patch("/api/v1/me/preferences", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["morning_checkin_time"] == "07:00:00"
    assert data["evening_checkin_time"] == "22:30:00"
    assert data["morning_checkin_enabled"] is False


@pytest.mark.asyncio
async def test_patch_my_preferences_invalid_timezone(client: AsyncClient, auth_headers: dict):
    """Test PATCH /api/v1/me/preferences with invalid timezone raises 422."""
    payload = {"timezone": "Invalid/Timezone"}

    response = await client.patch("/api/v1/me/preferences", json=payload, headers=auth_headers)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_patch_my_preferences_update_communication_style(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/preferences updates communication style."""
    payload = {"communication_style": "gentle", "coach_name": "Athena"}

    response = await client.patch("/api/v1/me/preferences", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["communication_style"] == "GENTLE"
    assert data["coach_name"] == "Athena"


@pytest.mark.asyncio
async def test_patch_my_preferences_unauthenticated(client: AsyncClient):
    """Test PATCH /api/v1/me/preferences without auth returns 401."""
    payload = {"timezone": "UTC"}

    response = await client.patch("/api/v1/me/preferences", json=payload)

    assert response.status_code == 401


# Tests for contact_frequency field


@pytest.mark.asyncio
async def test_get_preferences_includes_contact_frequency(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test GET /api/v1/me/preferences includes contact_frequency."""
    response = await client.get("/api/v1/me/preferences", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "contact_frequency" in data
    assert data["contact_frequency"] == "SOMETIMES"


@pytest.mark.asyncio
async def test_patch_preferences_update_contact_frequency(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH /api/v1/me/preferences updates contact_frequency."""
    payload = {"contact_frequency": "frequently"}

    response = await client.patch("/api/v1/me/preferences", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["contact_frequency"] == "FREQUENTLY"


@pytest.mark.asyncio
async def test_patch_preferences_contact_frequency_case_insensitive(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test PATCH accepts case-insensitive contact_frequency."""
    payload = {"contact_frequency": "RaReLy"}

    response = await client.patch("/api/v1/me/preferences", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["contact_frequency"] == "RARELY"


@pytest.mark.asyncio
async def test_patch_preferences_invalid_contact_frequency(client: AsyncClient, auth_headers: dict):
    """Test PATCH with invalid contact_frequency returns 422."""
    payload = {"contact_frequency": "INVALID_VALUE"}

    response = await client.patch("/api/v1/me/preferences", json=payload, headers=auth_headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_preferences_preserves_other_fields_when_updating_contact_frequency(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    """Test updating contact_frequency doesn't affect other fields."""
    setup_payload = {
        "timezone": "America/Sao_Paulo",
        "coach_name": "Athena",
    }
    await client.patch("/api/v1/me/preferences", json=setup_payload, headers=auth_headers)

    payload = {"contact_frequency": "rarely"}
    response = await client.patch("/api/v1/me/preferences", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["contact_frequency"] == "RARELY"
    assert data["timezone"] == "America/Sao_Paulo"
    assert data["coach_name"] == "Athena"
