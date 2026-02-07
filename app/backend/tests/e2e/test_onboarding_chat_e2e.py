"""E2E tests for onboarding through the chat endpoint.

Tests the full flow: user sends message → AgentRouter routes → agent responds.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_profile import OnboardingStatus, UserProfile


@pytest.fixture
async def chat_conversation(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> str:
    """Create a conversation for chat tests and return its ID."""
    response = await client.post(
        "/chat/conversations",
        json={
            "title": "Onboarding Chat",
            "ai_provider": "openai",
            "ai_model": "gpt-4",
        },
        headers=auth_headers,
    )
    return response.json()["id"]


class TestOnboardingChatE2E:
    """E2E tests for onboarding via chat."""

    @pytest.mark.asyncio
    async def test_new_user_gets_onboarding_via_chat(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        chat_conversation: str,
        db_session: AsyncSession,
    ):
        """User without completed onboarding should get onboarding response via chat."""
        # Verify user starts with NOT_STARTED
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()
        assert profile.onboarding_status == OnboardingStatus.NOT_STARTED

        with patch(
            "src.services.chat._route_agent_response",
            new_callable=AsyncMock,
            return_value="Olá! Eu sou o Virtus, seu assistente pessoal. Vamos começar?",
        ):
            response = await client.post(
                f"/chat/conversations/{chat_conversation}/messages",
                json={"role": "user", "content": "Oi!"},
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["assistant_message"]["role"] == "assistant"
            assert len(data["assistant_message"]["content"]) > 0

    @pytest.mark.asyncio
    async def test_completed_user_gets_normal_chat(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        chat_conversation: str,
        db_session: AsyncSession,
    ):
        """User with COMPLETED onboarding should get normal orchestrator response."""
        # Mark onboarding as completed
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()
        profile.onboarding_status = OnboardingStatus.COMPLETED
        await db_session.commit()

        with patch(
            "src.services.chat._route_agent_response",
            new_callable=AsyncMock,
            return_value="Claro! Posso te ajudar com sua agenda.",
        ):
            response = await client.post(
                f"/chat/conversations/{chat_conversation}/messages",
                json={"role": "user", "content": "Qual minha agenda de hoje?"},
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["assistant_message"]["content"] == "Claro! Posso te ajudar com sua agenda."

    @pytest.mark.asyncio
    async def test_onboarding_status_reflects_progress(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ):
        """GET /onboarding/status should reflect progress after onboarding advances."""
        from src.services.onboarding import advance_step, start_onboarding

        # Start onboarding and advance a few steps
        await start_onboarding(db_session, test_user.id)
        await advance_step(db_session, test_user.id)  # intro -> name
        await advance_step(db_session, test_user.id)  # name -> frequency

        # Check status endpoint
        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["current_step"] == "frequency"
        assert data["progress_percent"] == 28
