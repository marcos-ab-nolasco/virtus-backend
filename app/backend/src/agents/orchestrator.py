"""
Orchestrator Agent - Routes user messages to skills or direct responses

The orchestrator is responsible for:
1. Building user context
2. Deciding whether to invoke a skill or respond directly
3. Executing skills when needed
4. Formatting responses
"""

import json
import logging
from typing import Any
from uuid import UUID

from src.agents.actions import Action, ActionType
from src.skills.base import SkillResult
from src.skills.executor import SkillExecutor
from src.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Orchestrator agent that routes messages and invokes skills

    The orchestrator uses a simple keyword-based routing initially,
    which can be evolved to LLM-based routing later.
    """

    def __init__(
        self,
        llm_service: Any,
        skill_registry: SkillRegistry,
        skill_executor: SkillExecutor,
        context_service: Any,
    ):
        """
        Initialize orchestrator with dependencies

        Args:
            llm_service: LLM service for generating responses
            skill_registry: Registry of available skills
            skill_executor: Executor for running skills
            context_service: Service for building user context
        """
        self.llm_service = llm_service
        self.skill_registry = skill_registry
        self.skill_executor = skill_executor
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
                # Execute skill
                logger.info(f"Executing skill: {action.skill_name}")
                skill_result = await self._execute_skill(action)

                # Format skill result and generate response
                if skill_result.success:
                    skill_output = self._format_skill_result(skill_result)
                    response = await self._generate_response_with_skill_result(
                        message=message,
                        skill_name=action.skill_name or "",
                        skill_result=skill_output,
                        context=context,
                    )
                else:
                    # Skill failed, generate error response
                    logger.warning(f"Skill execution failed: {skill_result.error}")
                    response = await self._generate_error_response(
                        message=message,
                        error=skill_result.error or "Unknown error",
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
                reasoning="No matching skill, direct response",
            )

    async def _execute_skill(self, action: Action) -> SkillResult:
        """
        Execute a skill action

        Args:
            action: Action with skill details

        Returns:
            SkillResult from execution
        """
        try:
            if action.skill_name is None:
                return SkillResult(
                    success=False,
                    data=None,
                    error="No skill name specified",
                )

            return await self.skill_executor.execute(
                skill_name=action.skill_name,
                args=action.skill_args or {},
            )
        except Exception as e:
            logger.error(f"Error executing skill: {e}", exc_info=True)
            return SkillResult(
                success=False,
                data=None,
                error=str(e),
            )

    def _format_skill_result(self, skill_result: SkillResult) -> str:
        """
        Format skill result for LLM consumption

        Args:
            skill_result: Result from skill execution

        Returns:
            Formatted string
        """
        if skill_result.data is None:
            return "No data returned"

        try:
            # Format as JSON for structured data
            return json.dumps(skill_result.data, indent=2, ensure_ascii=False)
        except Exception:
            # Fallback to string representation
            return str(skill_result.data)

    async def _generate_response_with_skill_result(
        self,
        message: str,
        skill_name: str,
        skill_result: str,
        context: dict[str, Any],
    ) -> str:
        """
        Generate response incorporating skill result

        Args:
            message: Original user message
            skill_name: Name of skill that was executed
            skill_result: Formatted skill result
            context: User context

        Returns:
            Generated response
        """
        try:
            # Create system prompt
            system_prompt = f"""You are a helpful AI assistant.
The user asked: "{message}"

You invoked the skill '{skill_name}' and got this result:
{skill_result}

Use this information to provide a helpful, conversational response to the user.
Be natural and friendly."""

            response: str = await self.llm_service.generate_response(
                messages=[{"role": "user", "content": message}],
                system_prompt=system_prompt,
            )
            return response
        except Exception as e:
            logger.error(f"Error generating response with skill result: {e}")
            # Fallback: return skill result directly
            return f"Here's what I found:\n{skill_result}"

    async def _generate_direct_response(self, message: str, context: dict[str, Any]) -> str:
        """
        Generate direct LLM response without skill

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
        Generate response when skill execution failed

        Args:
            message: Original user message
            error: Error message from skill
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
