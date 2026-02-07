"""OpenAI chat completion service."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException, status
from openai import AsyncOpenAI
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.config import get_settings

from .base import BaseAIService

logger = logging.getLogger(__name__)


class OpenAIService(BaseAIService):
    """Implementation of the AI service using OpenAI's chat completions API."""

    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None
        self._client = AsyncOpenAI(api_key=api_key) if api_key else None

    async def generate_response(
        self,
        messages: list[dict[str, Any]],
        model: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a completion using OpenAI with retry logic."""
        if self._client is None:
            logger.warning("OpenAI provider not configured: missing OPENAI_API_KEY")
            return "OpenAI não está configurado. Defina OPENAI_API_KEY para habilitar respostas automáticas."

        client = self._client
        payload = self._build_payload(messages, system_prompt)

        try:
            async for attempt in AsyncRetrying(
                reraise=True,
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=4),
                retry=retry_if_exception_type(Exception),
            ):
                with attempt:
                    if attempt.retry_state.attempt_number > 1:
                        logger.warning(
                            f"OpenAI retry attempt {attempt.retry_state.attempt_number}/3: model={model}"
                        )
                    response = await client.chat.completions.create(
                        model=model,
                        messages=payload,  # type: ignore[arg-type]
                    )
        except Exception as exc:  # noqa: BLE001 - upstream errors vary
            logger.error(
                f"OpenAI call failed after retries: model={model} error={type(exc).__name__}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to generate response from OpenAI: {exc}",
            ) from exc

        message = response.choices[0].message

        if isinstance(message.content, str):
            content = message.content
        else:
            parts: list[str] = []
            for part in message.content or []:  # type: ignore[var-annotated]
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                else:
                    text_value = getattr(part, "text", None)
                    if isinstance(text_value, str):
                        parts.append(text_value)
            content = "".join(parts)

        if not content:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenAI returned an empty response",
            )

        return content

    async def generate_response_with_tools(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        tool_choice: str = "auto",
        model: str = "gpt-4o-mini",
    ) -> dict[str, Any]:
        """
        Generate a completion using OpenAI with function calling support.

        Args:
            messages: Conversation history
            system_prompt: System instructions
            tools: OpenAI tool definitions (function calling schema)
            tool_choice: "auto", "none", or "required"
            model: Model to use (defaults to gpt-4o-mini)

        Returns:
            dict with keys:
            - content: str | None (text response)
            - tool_calls: list[dict] | None (function calls)
            - finish_reason: str (OpenAI finish_reason)

        Raises:
            HTTPException(502): If OpenAI API fails after retries

        Example:
            >>> result = await service.generate_response_with_tools(
            ...     messages=[{"role": "user", "content": "What's the weather in SF?"}],
            ...     system_prompt="You are a helpful assistant.",
            ...     tools=[{"type": "function", "function": {...}}],
            ... )
            >>> print(result["tool_calls"])
            [{"id": "call_123", "name": "get_weather", "arguments": {"location": "SF"}}]
        """
        if self._client is None:
            logger.warning("OpenAI provider not configured: missing OPENAI_API_KEY")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenAI not configured. Set OPENAI_API_KEY environment variable.",
            )

        client = self._client
        payload = self._build_payload(messages, system_prompt)

        try:
            async for attempt in AsyncRetrying(
                reraise=True,
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=4),
                retry=retry_if_exception_type(Exception),
            ):
                with attempt:
                    if attempt.retry_state.attempt_number > 1:
                        logger.warning(
                            f"OpenAI retry attempt {attempt.retry_state.attempt_number}/3: model={model}"
                        )

                    # Build API call parameters
                    api_params: dict[str, Any] = {
                        "model": model,
                        "messages": payload,
                    }

                    # Add tools if provided
                    if tools:
                        api_params["tools"] = tools
                        api_params["tool_choice"] = tool_choice

                    response = await client.chat.completions.create(**api_params)

        except Exception as exc:  # noqa: BLE001 - upstream errors vary
            logger.error(
                f"OpenAI API call failed after retries: model={model} error={type(exc).__name__}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to generate response from OpenAI API: {exc}",
            ) from exc

        # Extract response data
        choice = response.choices[0]
        message = choice.message

        # Parse content
        content: str | None = None
        if message.content:
            if isinstance(message.content, str):
                content = message.content
            else:
                # Handle complex content types (similar to generate_response)
                parts: list[str] = []
                for part in message.content:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict):
                        text = part.get("text")
                        if isinstance(text, str):
                            parts.append(text)
                    else:
                        text_value = getattr(part, "text", None)
                        if isinstance(text_value, str):
                            parts.append(text_value)
                content = "".join(parts) if parts else None

        # Parse tool calls
        tool_calls = self._parse_tool_calls(message.tool_calls) if message.tool_calls else None

        return {
            "content": content,
            "tool_calls": tool_calls,
            "finish_reason": choice.finish_reason,
        }

    @staticmethod
    def _parse_tool_calls(tool_calls: Any) -> list[dict[str, Any]]:
        """
        Parse OpenAI tool calls into our standard format.

        Transforms:
            - tool_call.id -> dict["id"]
            - tool_call.function.name -> dict["name"]
            - tool_call.function.arguments (JSON string) -> dict["arguments"] (parsed dict)

        Args:
            tool_calls: OpenAI tool_calls from message

        Returns:
            List of parsed tool call dicts
        """
        parsed_calls: list[dict[str, Any]] = []

        for tool_call in tool_calls:
            # Parse JSON arguments string to dict
            arguments_str = tool_call.function.arguments
            try:
                arguments = json.loads(arguments_str) if arguments_str else {}
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool call arguments: {arguments_str}")
                arguments = {}

            parsed_calls.append(
                {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": arguments,
                }
            )

        return parsed_calls

    @staticmethod
    def _build_payload(
        messages: list[dict[str, Any]], system_prompt: str | None
    ) -> list[dict[str, Any]]:
        """Prepare message payload including optional system prompt."""
        payload: list[dict[str, Any]] = []

        if system_prompt:
            payload.append({"role": "system", "content": system_prompt})

        for msg in messages:
            entry = {"role": msg["role"], "content": msg["content"]}
            if msg.get("role") == "tool" and "tool_call_id" in msg:
                entry["tool_call_id"] = msg["tool_call_id"]
            if msg.get("role") == "assistant" and "tool_calls" in msg:
                entry["tool_calls"] = msg["tool_calls"]
            payload.append(entry)

        return payload
