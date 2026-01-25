"""
Orchestrator Agent - Routes user messages to tools or direct responses

The orchestrator is responsible for:
1. Building user context
2. Deciding whether to invoke a tool or respond directly
3. Executing tools when needed
4. Formatting responses
"""

import json
import logging
from typing import Any
from uuid import UUID

from src.agents.actions import Action, ActionType
from src.tools.base import ToolResult
from src.tools.executor import ToolExecutor
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Orchestrator agent that routes messages and invokes tools

    The orchestrator uses a simple keyword-based routing initially,
    which can be evolved to LLM-based routing later.
    """

    def __init__(
        self,
        llm_service: Any,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        context_service: Any,
    ):
        """
        Initialize orchestrator with dependencies

        Args:
            llm_service: LLM service for generating responses
            tool_registry: Registry of available tools
            tool_executor: Executor for running tools
            context_service: Service for building user context
        """
        self.llm_service = llm_service
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.context_service = context_service

    async def process_message(
        self,
        user_id: UUID,
        message: str,
        conversation_id: UUID,
    ) -> str:
        """
        Process a user message and return a response

        Args:
            user_id: UUID of the user
            message: User's message
            conversation_id: UUID of the conversation

        Returns:
            Response string to send back to user
        """
        try:
            logger.info(f"Processing message for user {user_id}, conversation {conversation_id}")

            # Step 1: Build context
            context = await self._build_context(user_id)
            logger.debug(f"Built context: {context}")

            # Step 2: Decide action
            action = await self._decide_action(message, context)
            logger.info(f"Decided action: {action.type.value}")

            # Step 3: Execute action
            if action.type == ActionType.SKILL_CALL:
                # Execute tool
                logger.info(f"Executing tool: {action.skill_name}")
                tool_result = await self._execute_tool(action)

                # Format tool result and generate response
                if tool_result.success:
                    tool_output = self._format_tool_result(tool_result)
                    response = await self._generate_response_with_tool_result(
                        message=message,
                        tool_name=action.skill_name or "",
                        tool_result=tool_output,
                        context=context,
                    )
                else:
                    # Tool failed, generate error response
                    logger.warning(f"Tool execution failed: {tool_result.error}")
                    response = await self._generate_error_response(
                        message=message,
                        error=tool_result.error or "Unknown error",
                        context=context,
                    )
            else:
                # Direct response
                response = await self._generate_direct_response(message, context)

            logger.info(f"Generated response (length: {len(response)})")
            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return self._get_fallback_error_message()

    async def _build_context(self, user_id: UUID) -> dict[str, Any]:
        """
        Build user context for the conversation

        Args:
            user_id: UUID of the user

        Returns:
            Context dictionary
        """
        try:
            if hasattr(self.context_service, "build_permanent_context"):
                context: dict[str, Any] = await self.context_service.build_permanent_context(
                    user_id
                )
                return context
            else:
                return {"user": {"id": str(user_id)}}
        except Exception as e:
            logger.warning(f"Failed to build context: {e}")
            return {"user": {"id": str(user_id)}}

    async def _decide_action(self, message: str, context: dict[str, Any]) -> Action:
        """
        Decide what action to take based on the message

        Currently uses simple keyword matching.
        Can be evolved to use LLM for routing.

        Args:
            message: User's message
            context: User context

        Returns:
            Action to take
        """
        message_lower = message.lower()

        # Simple keyword-based routing
        time_keywords = ["time", "date", "hora", "data", "quando"]
        preferences_keywords = ["preferences", "preferências", "settings", "configurações"]
        calendar_keywords = ["calendar", "calendário", "events", "eventos", "agenda"]

        if any(keyword in message_lower for keyword in time_keywords):
            return Action(
                type=ActionType.SKILL_CALL,
                skill_name="get_current_date",
                skill_args={"timezone": context.get("user", {}).get("timezone", "UTC")},
                reasoning="User asked about time/date",
            )
        elif any(keyword in message_lower for keyword in preferences_keywords):
            return Action(
                type=ActionType.SKILL_CALL,
                skill_name="get_user_preferences",
                skill_args={"user_id": context.get("user", {}).get("id", "")},
                reasoning="User asked about preferences",
            )
        elif any(keyword in message_lower for keyword in calendar_keywords):
            return Action(
                type=ActionType.SKILL_CALL,
                skill_name="get_calendar_events",
                skill_args={
                    "user_id": context.get("user", {}).get("id", ""),
                    "days_ahead": 7,
                },
                reasoning="User asked about calendar",
            )
        else:
            return Action(
                type=ActionType.DIRECT_RESPONSE,
                reasoning="No matching tool, direct response",
            )

    async def _execute_tool(self, action: Action) -> ToolResult:
        """
        Execute a tool action

        Args:
            action: Action with tool details

        Returns:
            ToolResult from execution
        """
        try:
            if action.skill_name is None:
                return ToolResult(
                    success=False,
                    data=None,
                    error="No tool name specified",
                )

            return await self.tool_executor.execute(
                tool_name=action.skill_name,
                args=action.skill_args or {},
            )
        except Exception as e:
            logger.error(f"Error executing tool: {e}", exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
            )

    def _format_tool_result(self, tool_result: ToolResult) -> str:
        """
        Format tool result for LLM consumption

        Args:
            tool_result: Result from tool execution

        Returns:
            Formatted string
        """
        if tool_result.data is None:
            return "No data returned"

        try:
            # Format as JSON for structured data
            return json.dumps(tool_result.data, indent=2, ensure_ascii=False)
        except Exception:
            # Fallback to string representation
            return str(tool_result.data)

    async def _generate_response_with_tool_result(
        self,
        message: str,
        tool_name: str,
        tool_result: str,
        context: dict[str, Any],
    ) -> str:
        """
        Generate response incorporating tool result

        Args:
            message: Original user message
            tool_name: Name of tool that was executed
            tool_result: Formatted tool result
            context: User context

        Returns:
            Generated response
        """
        try:
            # Create system prompt
            system_prompt = f"""You are a helpful AI assistant.
The user asked: "{message}"

You invoked the tool '{tool_name}' and got this result:
{tool_result}

Use this information to provide a helpful, conversational response to the user.
Be natural and friendly."""

            response: str = await self.llm_service.generate_response(
                messages=[{"role": "user", "content": message}],
                system_prompt=system_prompt,
            )
            return response
        except Exception as e:
            logger.error(f"Error generating response with tool result: {e}")
            # Fallback: return tool result directly
            return f"Here's what I found:\n{tool_result}"

    async def _generate_direct_response(self, message: str, context: dict[str, Any]) -> str:
        """
        Generate direct LLM response without tool

        Args:
            message: User's message
            context: User context

        Returns:
            Generated response
        """
        try:
            system_prompt = "You are a helpful AI assistant. Be friendly and conversational."

            response: str = await self.llm_service.generate_response(
                messages=[{"role": "user", "content": message}],
                system_prompt=system_prompt,
            )
            return response
        except Exception as e:
            logger.error(f"Error generating direct response: {e}")
            return "I apologize, but I'm having trouble generating a response right now."

    async def _generate_error_response(
        self, message: str, error: str, context: dict[str, Any]
    ) -> str:
        """
        Generate response when tool execution failed

        Args:
            message: Original user message
            error: Error message from tool
            context: User context

        Returns:
            Error response
        """
        return f"I apologize, but I encountered an error while trying to help you: {error}"

    def _get_fallback_error_message(self) -> str:
        """
        Get fallback error message for critical failures

        Returns:
            Generic error message
        """
        return "I apologize, but I'm experiencing technical difficulties. Please try again later."
