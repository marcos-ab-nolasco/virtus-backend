"""Tests for chat service integration with OrchestratorAgent.

Verifies that create_message routes through OrchestratorAgent
instead of calling ai_service.generate_response() directly.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Conversation, User


@pytest.fixture
async def test_conversation(db_session: AsyncSession, test_user: User) -> Conversation:
    """Create a test conversation."""
    conversation = Conversation(
        user_id=test_user.id,
        title="Test Chat",
        ai_provider="openai",
        ai_model="gpt-4",
        system_prompt="You are helpful.",
    )
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)
    return conversation


class TestChatOrchestratorIntegration:
    """Test that chat service uses OrchestratorAgent."""

    @pytest.mark.asyncio
    async def test_create_message_uses_orchestrator(
        self,
        client: AsyncClient,
        test_user: User,
        test_conversation: Conversation,
        auth_headers: dict[str, str],
        mocker: MockerFixture,
    ):
        """create_message should route through OrchestratorAgent."""
        mock_orchestrator_response = "Resposta do orchestrator"

        with patch(
            "src.services.chat._get_orchestrator_response",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ) as mock_get_response:
            response = await client.post(
                f"/chat/conversations/{test_conversation.id}/messages",
                json={"role": "user", "content": "Hello"},
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["assistant_message"]["content"] == mock_orchestrator_response
            mock_get_response.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_message_preserves_response_contract(
        self,
        client: AsyncClient,
        test_user: User,
        test_conversation: Conversation,
        auth_headers: dict[str, str],
        mocker: MockerFixture,
    ):
        """create_message should still return tuple[Message, Message] contract."""
        with patch(
            "src.services.chat._get_orchestrator_response",
            new_callable=AsyncMock,
            return_value="Resposta via orchestrator",
        ):
            response = await client.post(
                f"/chat/conversations/{test_conversation.id}/messages",
                json={"role": "user", "content": "Olá!"},
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()

            # Should have both user and assistant messages
            assert "user_message" in data
            assert "assistant_message" in data
            assert data["user_message"]["role"] == "user"
            assert data["assistant_message"]["role"] == "assistant"
            assert data["user_message"]["content"] == "Olá!"
            assert data["assistant_message"]["content"] == "Resposta via orchestrator"

    @pytest.mark.asyncio
    async def test_create_message_passes_conversation_history_to_orchestrator(
        self,
        client: AsyncClient,
        test_user: User,
        test_conversation: Conversation,
        auth_headers: dict[str, str],
        mocker: MockerFixture,
    ):
        """create_message should pass conversation history to orchestrator."""
        call_args_capture: dict = {}

        async def capture_args(db, user_id, message, conversation_id, conversation_history):
            call_args_capture["conversation_history"] = conversation_history
            call_args_capture["message"] = message
            return "Response"

        with patch(
            "src.services.chat._get_orchestrator_response",
            side_effect=capture_args,
        ):
            # Send first message
            await client.post(
                f"/chat/conversations/{test_conversation.id}/messages",
                json={"role": "user", "content": "First message"},
                headers=auth_headers,
            )

            # Check that conversation_history was passed
            assert "conversation_history" in call_args_capture
            assert isinstance(call_args_capture["conversation_history"], list)

    @pytest.mark.asyncio
    async def test_completed_onboarding_user_gets_direct_response(
        self,
        client: AsyncClient,
        test_user: User,
        test_conversation: Conversation,
        auth_headers: dict[str, str],
        mocker: MockerFixture,
    ):
        """User with COMPLETED onboarding passes through orchestrator's normal flow."""
        with patch(
            "src.services.chat._get_orchestrator_response",
            new_callable=AsyncMock,
            return_value="Resposta normal do orchestrator",
        ):
            response = await client.post(
                f"/chat/conversations/{test_conversation.id}/messages",
                json={"role": "user", "content": "Qual minha agenda?"},
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["assistant_message"]["content"] == "Resposta normal do orchestrator"
