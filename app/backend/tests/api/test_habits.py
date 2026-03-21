"""Tests for habits API endpoints."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, hash_password
from src.db.models.user import User


@pytest.fixture
async def second_user(db_session: AsyncSession) -> User:
    """Create a second test user for ownership tests."""
    user = User(
        email="other@example.com",
        hashed_password=hash_password("otherpassword123"),
        full_name="Other User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def second_user_headers(second_user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": str(second_user.id)})
    return {"Authorization": f"Bearer {token}"}


# ===== CRUD =====


@pytest.mark.asyncio
async def test_create_habit(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.post(
        "/api/v1/me/habits",
        json={"name": "Meditar", "description": "10 min diários", "color": "#14B8A6"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Meditar"
    assert data["description"] == "10 min diários"
    assert data["color"] == "#14B8A6"
    assert data["frequency_type"] == "DAILY"
    assert data["is_active"] is True
    assert data["is_archived"] is False


@pytest.mark.asyncio
async def test_list_habits(client: AsyncClient, auth_headers: dict) -> None:
    await client.post("/api/v1/me/habits", json={"name": "Habit 1"}, headers=auth_headers)
    await client.post("/api/v1/me/habits", json={"name": "Habit 2"}, headers=auth_headers)

    response = await client.get("/api/v1/me/habits", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_habit(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post("/api/v1/me/habits", json={"name": "Ler"}, headers=auth_headers)
    habit_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/me/habits/{habit_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Ler"


@pytest.mark.asyncio
async def test_update_habit(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post(
        "/api/v1/me/habits", json={"name": "Correr"}, headers=auth_headers
    )
    habit_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/me/habits/{habit_id}",
        json={"name": "Correr 5km", "target_per_period": 3},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Correr 5km"
    assert data["target_per_period"] == 3


@pytest.mark.asyncio
async def test_delete_habit(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post(
        "/api/v1/me/habits", json={"name": "Temp"}, headers=auth_headers
    )
    habit_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/me/habits/{habit_id}", headers=auth_headers)
    assert response.status_code == 204

    get_resp = await client.get(f"/api/v1/me/habits/{habit_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_archive_habit(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post(
        "/api/v1/me/habits", json={"name": "Archive me"}, headers=auth_headers
    )
    habit_id = create_resp.json()["id"]

    response = await client.post(f"/api/v1/me/habits/{habit_id}/archive", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_archived"] is True
    assert data["is_active"] is False
    assert data["archived_at"] is not None


# ===== Ownership =====


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_habit(
    client: AsyncClient, auth_headers: dict, second_user_headers: dict
) -> None:
    create_resp = await client.post(
        "/api/v1/me/habits", json={"name": "Private"}, headers=auth_headers
    )
    habit_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/me/habits/{habit_id}", headers=second_user_headers)
    assert response.status_code == 404


# ===== Logs =====


@pytest.mark.asyncio
async def test_toggle_habit_log_creates(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post(
        "/api/v1/me/habits", json={"name": "Log test"}, headers=auth_headers
    )
    habit_id = create_resp.json()["id"]
    today = date.today().isoformat()

    response = await client.post(
        f"/api/v1/me/habits/{habit_id}/logs",
        json={"date": today, "completed": True},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["completed"] is True
    assert data["date"] == today


@pytest.mark.asyncio
async def test_toggle_habit_log_upsert(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post(
        "/api/v1/me/habits", json={"name": "Upsert test"}, headers=auth_headers
    )
    habit_id = create_resp.json()["id"]
    today = date.today().isoformat()

    # First toggle
    resp1 = await client.post(
        f"/api/v1/me/habits/{habit_id}/logs",
        json={"date": today, "completed": True},
        headers=auth_headers,
    )
    assert resp1.status_code == 201
    log_id_1 = resp1.json()["id"]

    # Second toggle (upsert)
    resp2 = await client.post(
        f"/api/v1/me/habits/{habit_id}/logs",
        json={"date": today, "completed": False, "notes": "Skipped today"},
        headers=auth_headers,
    )
    assert resp2.status_code == 201
    data = resp2.json()
    assert data["id"] == log_id_1  # Same log updated
    assert data["completed"] is False
    assert data["notes"] == "Skipped today"


@pytest.mark.asyncio
async def test_list_habit_logs(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post(
        "/api/v1/me/habits", json={"name": "Logs list"}, headers=auth_headers
    )
    habit_id = create_resp.json()["id"]

    today = date.today()
    for i in range(3):
        d = (today - timedelta(days=i)).isoformat()
        await client.post(
            f"/api/v1/me/habits/{habit_id}/logs",
            json={"date": d, "completed": True},
            headers=auth_headers,
        )

    response = await client.get(f"/api/v1/me/habits/{habit_id}/logs", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["logs"]) == 3


# ===== Stats =====


@pytest.mark.asyncio
async def test_habit_stats(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post(
        "/api/v1/me/habits", json={"name": "Stats test"}, headers=auth_headers
    )
    habit_id = create_resp.json()["id"]

    today = date.today()
    # Create a 5-day streak ending today
    for i in range(5):
        d = (today - timedelta(days=i)).isoformat()
        await client.post(
            f"/api/v1/me/habits/{habit_id}/logs",
            json={"date": d, "completed": True},
            headers=auth_headers,
        )

    response = await client.get(f"/api/v1/me/habits/{habit_id}/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["current_streak"] == 5
    assert data["longest_streak"] == 5
    assert data["total_completions"] == 5
    assert data["completion_rate_7d"] > 0
    assert len(data["heatmap"]) == 90


# ===== Today Log =====


@pytest.mark.asyncio
async def test_list_habits_includes_today_log(client: AsyncClient, auth_headers: dict) -> None:
    create_resp = await client.post(
        "/api/v1/me/habits", json={"name": "Today Log Test"}, headers=auth_headers
    )
    assert create_resp.status_code == 201
    habit_id = create_resp.json()["id"]
    today = date.today().isoformat()

    log_resp = await client.post(
        f"/api/v1/me/habits/{habit_id}/logs",
        json={"date": today, "completed": True},
        headers=auth_headers,
    )
    assert log_resp.status_code == 201

    list_resp = await client.get("/api/v1/me/habits", headers=auth_headers)
    assert list_resp.status_code == 200
    habits = list_resp.json()
    habit = next(h for h in habits if h["id"] == habit_id)
    assert habit["today_log"] is not None
    assert habit["today_log"]["completed"] is True
    assert habit["today_log"]["date"] == today


@pytest.mark.asyncio
async def test_list_habits_today_log_none_when_not_logged(
    client: AsyncClient, auth_headers: dict
) -> None:
    await client.post("/api/v1/me/habits", json={"name": "No Log Habit"}, headers=auth_headers)

    list_resp = await client.get("/api/v1/me/habits", headers=auth_headers)
    assert list_resp.status_code == 200
    habits = list_resp.json()
    for habit in habits:
        # Habit without a log today should have today_log=None
        if habit["name"] == "No Log Habit":
            assert habit["today_log"] is None


# ===== Auth =====


@pytest.mark.asyncio
async def test_habits_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me/habits")
    assert response.status_code == 401

    response = await client.post("/api/v1/me/habits", json={"name": "Test"})
    assert response.status_code == 401
