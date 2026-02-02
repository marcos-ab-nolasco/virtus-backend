"""
Orchestrator Agent - Routes user messages to tools or direct responses

The orchestrator is responsible for:
1. Building user context
2. Checking if onboarding is needed
3. Deciding whether to invoke a tool or respond directly
4. Executing tools when needed
5. Formatting responses

Refactored to inherit from BaseAgent and use skills.
"""

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from src.agents.actions import Action, ActionType
from src.agents.base import AgentResponse, BaseAgent
from src.tools.base import ToolResult
from src.tools.executor import ToolExecutor
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator agent that routes messages and invokes tools.

    Inherits from BaseAgent to use skills-based system prompts.
    Maintains backward compatibility with process_message() API.
    """

    def __init__(
        self,
        llm_service: Any,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        context_service: Any,
        skills_path: Path | None = None,
    ):
        """
        Initialize orchestrator with dependencies.

        Args:
            llm_service: LLM service for generating responses
            tool_registry: Registry of available tools
            tool_executor: Executor for running tools
            context_service: Service for building user context
            skills_path: Optional path to skills folder
        """
        super().__init__(
            llm_service=llm_service,
            tool_registry=tool_registry,
            skills_path=skills_path,
        )
        self.tool_executor = tool_executor
        self.context_service = context_service

        # Keep references with original names for backward compatibility
        self.llm_service = llm_service
        self.tool_registry = tool_registry

    @property
    def name(self) -> str:
        return "orchestrator"

    @property
    def skills(self) -> list[str]:
        return [
            "shared/persona_base",
            "shared/tom_ajuste",
            "shared/contexto_usuario",
            "orchestrator/classificacao_intencao",
            "orchestrator/roteamento",
        ]

    @property
    def available_tools(self) -> list[str]:
        # Orchestrator can use all registered tools for now
        return list(self.tool_registry.list_tools())

    def should_route_to_onboarding(self, context: dict[str, Any]) -> bool:
        """
        Check if user needs to be routed to onboarding.

        Args:
            context: User context with profile data

        Returns:
            True if onboarding is needed
        """
        profile = context.get("profile")
        if not profile:
            return True

        onboarding_status = profile.get("onboarding_status")
        return onboarding_status != "COMPLETED"

    async def process_message(
        self,
        user_id: UUID,
        message: str,
        conversation_id: UUID,
    ) -> str:
        """
        Process a user message and return a response.

        This is the main entry point, maintaining backward compatibility.

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

            # Step 2: Check if onboarding is needed
            if self.should_route_to_onboarding(context):
                logger.info("User needs onboarding, returning handoff signal")
                return await self._handle_onboarding_needed(message, context)

            # Step 3: Decide action
            action = await self._decide_action(message, context)
            logger.info(f"Decided action: {action.type.value}")

            # Step 4: Execute action
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

    async def _handle_onboarding_needed(
        self, message: str, context: dict[str, Any]
    ) -> str:
        """
        Handle case when user needs onboarding.

        For now, returns a message indicating onboarding is needed.
        In the future, this will be handled by AgentRouter.

        Args:
            message: User's message
            context: User context

        Returns:
            Response indicating onboarding is needed
        """
        # Get user's preferred name or full name
        user_info = context.get("user", {})
        profile_info = context.get("profile", {})
        preferred_name = profile_info.get("preferred_name")
        full_name = user_info.get("full_name", "")
        name = preferred_name or (full_name.split()[0] if full_name else "")

        greeting = f"Olá{', ' + name if name else ''}!"

        return f"""{greeting}

Antes de começarmos, preciso te conhecer um pouco melhor. Vou fazer algumas perguntas rápidas - leva só 3-5 minutos.

Isso vai me ajudar a te acompanhar do jeito que funciona melhor pra você.

Vamos lá?"""

    async def _build_context(self, user_id: UUID) -> dict[str, Any]:
        """
        Build user context for the conversation.

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
        Decide what action to take based on the message.

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
        Execute a tool action.

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
        Format tool result for LLM consumption.

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
        Generate response incorporating tool result.

        Uses skills-based system prompt.

        Args:
            message: Original user message
            tool_name: Name of tool that was executed
            tool_result: Formatted tool result
            context: User context

        Returns:
            Generated response
        """
        try:
            # Build system prompt using skills
            base_prompt = self.build_system_prompt(context)

            system_prompt = f"""{base_prompt}

---

O usuário perguntou: "{message}"

Você invocou a ferramenta '{tool_name}' e obteve este resultado:
{tool_result}

Use esta informação para responder de forma útil e conversacional."""

            response: str = await self.llm_service.generate_response(
                messages=[{"role": "user", "content": message}],
                system_prompt=system_prompt,
            )
            return response
        except Exception as e:
            logger.error(f"Error generating response with tool result: {e}")
            # Fallback: return tool result directly
            return f"Aqui está o que encontrei:\n{tool_result}"

    async def _generate_direct_response(self, message: str, context: dict[str, Any]) -> str:
        """
        Generate direct LLM response without tool.

        Uses skills-based system prompt.

        Args:
            message: User's message
            context: User context

        Returns:
            Generated response
        """
        try:
            # Build system prompt using skills
            system_prompt = self.build_system_prompt(context)

            response: str = await self.llm_service.generate_response(
                messages=[{"role": "user", "content": message}],
                system_prompt=system_prompt,
            )
            return response
        except Exception as e:
            logger.error(f"Error generating direct response: {e}")
            return "Desculpe, estou tendo dificuldades para gerar uma resposta agora."

    async def _generate_error_response(
        self, message: str, error: str, context: dict[str, Any]
    ) -> str:
        """
        Generate response when tool execution failed.

        Args:
            message: Original user message
            error: Error message from tool
            context: User context

        Returns:
            Error response
        """
        return f"Desculpe, encontrei um erro ao tentar te ajudar: {error}"

    def _get_fallback_error_message(self) -> str:
        """
        Get fallback error message for critical failures.

        Returns:
            Generic error message
        """
        return "Desculpe, estou com dificuldades técnicas. Por favor, tente novamente mais tarde."
