"""Tests for OpenAI function calling support."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.services.ai.openai_service import OpenAIService


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch("src.services.ai.openai_service.AsyncOpenAI") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def openai_service(mock_openai_client: MagicMock) -> OpenAIService:
    """Create OpenAI service instance with mocked client."""
    return OpenAIService()


class TestGenerateResponseWithTools:
    """Test generate_response_with_tools method."""

    @pytest.mark.asyncio
    async def test_generate_response_with_tools_returns_correct_structure(
        self, openai_service: OpenAIService, mock_openai_client: MagicMock
    ) -> None:
        """Test that response has correct structure."""
        # Mock OpenAI response
        mock_message = MagicMock()
        mock_message.content = "I'll help you with that."
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Call method
        result = await openai_service.generate_response_with_tools(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="You are a helpful assistant.",
            tools=[],
        )

        # Verify structure
        assert isinstance(result, dict)
        assert "content" in result
        assert "tool_calls" in result
        assert "finish_reason" in result

    @pytest.mark.asyncio
    async def test_generate_response_with_tools_text_response(
        self, openai_service: OpenAIService, mock_openai_client: MagicMock
    ) -> None:
        """Test text response without tool calls."""
        # Mock OpenAI response with text only
        mock_message = MagicMock()
        mock_message.content = "Hello! How can I help you today?"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Call method
        result = await openai_service.generate_response_with_tools(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="You are a helpful assistant.",
            tools=[],
        )

        # Verify text response
        assert result["content"] == "Hello! How can I help you today?"
        assert result["tool_calls"] is None
        assert result["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_generate_response_with_tools_calls_function(
        self, openai_service: OpenAIService, mock_openai_client: MagicMock
    ) -> None:
        """Test function calling."""
        # Mock tool call
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "get_weather"
        mock_tool_call.function.arguments = '{"location": "San Francisco"}'

        mock_message = MagicMock()
        mock_message.content = None
        mock_message.tool_calls = [mock_tool_call]

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "tool_calls"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Call method
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                },
            }
        ]

        result = await openai_service.generate_response_with_tools(
            messages=[{"role": "user", "content": "What's the weather?"}],
            system_prompt="You are a helpful assistant.",
            tools=tools,
        )

        # Verify tool call format
        assert result["content"] is None
        assert result["tool_calls"] is not None
        assert len(result["tool_calls"]) == 1

        tool_call = result["tool_calls"][0]
        assert tool_call["id"] == "call_123"
        assert tool_call["type"] == "function"
        assert tool_call["name"] == "get_weather"
        assert tool_call["arguments"] == {"location": "San Francisco"}
        assert result["finish_reason"] == "tool_calls"

    @pytest.mark.asyncio
    async def test_generate_response_with_tools_includes_system_prompt(
        self, openai_service: OpenAIService, mock_openai_client: MagicMock
    ) -> None:
        """Test that system prompt is included in API call."""
        # Mock response
        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Call method
        system_prompt = "You are a weather assistant."
        await openai_service.generate_response_with_tools(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt=system_prompt,
            tools=[],
        )

        # Verify system prompt was included
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]

        # First message should be system prompt
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == system_prompt

    @pytest.mark.asyncio
    async def test_generate_response_with_tools_passes_tools_param(
        self, openai_service: OpenAIService, mock_openai_client: MagicMock
    ) -> None:
        """Test that tools array is passed to API."""
        # Mock response
        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Call method
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                },
            }
        ]

        await openai_service.generate_response_with_tools(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="System prompt",
            tools=tools,
        )

        # Verify tools parameter
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs["tools"] == tools

    @pytest.mark.asyncio
    async def test_generate_response_with_tools_respects_tool_choice(
        self, openai_service: OpenAIService, mock_openai_client: MagicMock
    ) -> None:
        """Test that tool_choice parameter is passed correctly."""
        # Mock response
        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Test with different tool_choice values
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                },
            }
        ]

        for choice in ["auto", "none", "required"]:
            await openai_service.generate_response_with_tools(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="System prompt",
                tools=tools,
                tool_choice=choice,
            )

            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args.kwargs["tool_choice"] == choice

    @pytest.mark.asyncio
    async def test_generate_response_with_tools_handles_errors(
        self, openai_service: OpenAIService, mock_openai_client: MagicMock
    ) -> None:
        """Test error handling when API fails."""
        # Mock API failure
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))

        # Should raise HTTPException after retries
        with pytest.raises(HTTPException) as exc_info:
            await openai_service.generate_response_with_tools(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="System prompt",
                tools=[],
            )

        assert exc_info.value.status_code == 502
        assert "OpenAI API" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_generate_response_with_tools_retries_on_failure(
        self, openai_service: OpenAIService, mock_openai_client: MagicMock
    ) -> None:
        """Test retry logic on transient failures."""
        # Mock: first 2 calls fail, 3rd succeeds
        mock_message = MagicMock()
        mock_message.content = "Success"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                Exception("Temporary error 1"),
                Exception("Temporary error 2"),
                mock_response,
            ]
        )

        # Should succeed on 3rd attempt
        result = await openai_service.generate_response_with_tools(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="System prompt",
            tools=[],
        )

        assert result["content"] == "Success"
        # Verify it was called 3 times
        assert mock_openai_client.chat.completions.create.call_count == 3


class TestParseToolCalls:
    """Test _parse_tool_calls preserves OpenAI-compatible format."""

    def test_parse_tool_calls_includes_type_field(self) -> None:
        """Parsed tool calls must include type='function' for OpenAI roundtrip."""
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_abc"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "save_profile"
        mock_tool_call.function.arguments = '{"name": "João"}'

        result = OpenAIService._parse_tool_calls([mock_tool_call])

        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["id"] == "call_abc"
        assert result[0]["name"] == "save_profile"
        assert result[0]["arguments"] == {"name": "João"}

    def test_parse_tool_calls_multiple_calls(self) -> None:
        """Multiple tool calls should all have type field."""
        calls = []
        for i in range(3):
            tc = MagicMock()
            tc.id = f"call_{i}"
            tc.type = "function"
            tc.function.name = f"tool_{i}"
            tc.function.arguments = "{}"
            calls.append(tc)

        result = OpenAIService._parse_tool_calls(calls)

        assert len(result) == 3
        for parsed in result:
            assert parsed["type"] == "function"


class TestBuildPayloadToolCalls:
    """Test _build_payload correctly formats assistant messages with tool_calls."""

    def test_build_payload_formats_tool_calls_for_openai_api(self) -> None:
        """Assistant messages with tool_calls must use OpenAI nested format."""
        # This is the internal format (after _parse_tool_calls)
        messages = [
            {"role": "user", "content": "Do something"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "name": "save_profile",
                        "arguments": {"name": "João"},
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"success": true}',
                "tool_call_id": "call_123",
            },
        ]

        payload = OpenAIService._build_payload(messages, system_prompt=None)

        # Find assistant message in payload
        assistant_msg = next(m for m in payload if m["role"] == "assistant")
        tc = assistant_msg["tool_calls"][0]

        # Must have OpenAI-compatible nested format
        assert tc["id"] == "call_123"
        assert tc["type"] == "function"
        assert tc["function"]["name"] == "save_profile"
        assert tc["function"]["arguments"] == '{"name": "João"}'

    def test_build_payload_roundtrip_preserves_tool_call_id(self) -> None:
        """Tool messages must preserve tool_call_id."""
        messages = [
            {
                "role": "tool",
                "content": '{"success": true}',
                "tool_call_id": "call_xyz",
            },
        ]

        payload = OpenAIService._build_payload(messages, system_prompt=None)

        assert payload[0]["tool_call_id"] == "call_xyz"
