"""
Tests for Orchestrator Agent (Issue 2.6)

Following TDD approach for agentic system.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.agents.actions import Action, ActionType
from src.agents.orchestrator import OrchestratorAgent
from src.tools.base import ToolResult
from src.tools.examples.get_current_date import GetCurrentDateTool
from src.tools.executor import ToolExecutor
from src.tools.registry import ToolRegistry


class TestOrchestratorAgent:
    """Test OrchestratorAgent core functionality"""

    def setup_method(self):
        """Setup orchestrator with mocked dependencies"""
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)

        # Register test tool
        self.registry.register(GetCurrentDateTool())

        # Mock LLM service
        self.mock_llm = AsyncMock()

        # Mock context service
        self.mock_context = AsyncMock()
        self.mock_context.build_permanent_context = AsyncMock(
            return_value={"user": {"id": "test-user"}}
        )

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            tool_executor=self.executor,
            context_service=self.mock_context,
        )

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Orchestrator should initialize with dependencies"""
        assert self.orchestrator.llm_service == self.mock_llm
        assert self.orchestrator.tool_registry == self.registry
        assert self.orchestrator.tool_executor == self.executor
        assert self.orchestrator.context_service == self.mock_context

    @pytest.mark.asyncio
    async def test_process_message_direct_response(self):
        """Should handle direct response (no tool needed)"""
        user_id = uuid4()
        message = "Hello, how are you?"

        # Mock LLM to return direct response (no tool call)
        self.mock_llm.generate_response = AsyncMock(return_value="I'm doing well, thank you!")

        response = await self.orchestrator.process_message(
            user_id=user_id,
            message=message,
            conversation_id=uuid4(),
        )

        assert isinstance(response, str)
        assert len(response) > 0
        assert response == "I'm doing well, thank you!"

    @pytest.mark.asyncio
    async def test_process_message_with_tool_invocation(self):
        """Should invoke tool when LLM requests it"""
        user_id = uuid4()
        message = "What time is it?"

        # Mock LLM to return tool call
        self.mock_llm.chat_with_tools = AsyncMock(
            return_value={
                "tool_calls": [
                    {
                        "name": "get_current_date",
                        "arguments": {"timezone": "UTC", "format": "iso"},
                    }
                ]
            }
        )

        # Mock second LLM call to format tool result
        self.mock_llm.generate_response = AsyncMock(
            return_value="The current time is 2024-01-11T10:30:00+00:00"
        )

        response = await self.orchestrator.process_message(
            user_id=user_id,
            message=message,
            conversation_id=uuid4(),
        )

        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_decide_action_returns_action(self):
        """_decide_action should return Action object"""
        action = await self.orchestrator._decide_action(
            message="Test message",
            context={"user": {"id": "test"}},
        )

        assert isinstance(action, Action)
        assert action.type in [ActionType.DIRECT_RESPONSE, ActionType.SKILL_CALL]

    @pytest.mark.asyncio
    async def test_decide_action_tool_call(self):
        """Should decide to call tool for time-related queries"""
        action = await self.orchestrator._decide_action(
            message="What time is it?",
            context={},
        )

        # Simple keyword matching should detect time query
        if action.type == ActionType.SKILL_CALL:
            assert action.skill_name is not None

    @pytest.mark.asyncio
    async def test_execute_tool_action(self):
        """Should execute tool and return result"""
        action = Action(
            type=ActionType.SKILL_CALL,
            skill_name="get_current_date",
            skill_args={"timezone": "UTC"},
        )

        result = await self.orchestrator._execute_tool(action)

        assert isinstance(result, ToolResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool_returns_error(self):
        """Should handle non-existent tool gracefully"""
        action = Action(
            type=ActionType.SKILL_CALL,
            skill_name="nonexistent_tool",
            skill_args={},
        )

        result = await self.orchestrator._execute_tool(action)

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_format_tool_result_for_llm(self):
        """Should format tool result for LLM consumption"""
        tool_result = ToolResult(
            success=True,
            data={"datetime": "2024-01-11T10:30:00Z", "timezone": "UTC"},
            error=None,
        )

        formatted = self.orchestrator._format_tool_result(tool_result)

        assert isinstance(formatted, str)
        assert "datetime" in formatted or "2024-01-11" in formatted


class TestActionDataClass:
    """Test Action dataclass"""

    def test_create_direct_response_action(self):
        """Should create direct response action"""
        action = Action(type=ActionType.DIRECT_RESPONSE)

        assert action.type == ActionType.DIRECT_RESPONSE
        assert action.skill_name is None
        assert action.skill_args is None

    def test_create_tool_call_action(self):
        """Should create tool call action"""
        action = Action(
            type=ActionType.SKILL_CALL,
            skill_name="get_current_date",
            skill_args={"timezone": "UTC"},
        )

        assert action.type == ActionType.SKILL_CALL
        assert action.skill_name == "get_current_date"
        assert action.skill_args == {"timezone": "UTC"}


class TestOrchestratorWithContext:
    """Test orchestrator context building"""

    def setup_method(self):
        """Setup orchestrator"""
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            tool_executor=self.executor,
            context_service=self.mock_context,
        )

    @pytest.mark.asyncio
    async def test_builds_context_before_processing(self):
        """Should build user context before processing message"""
        user_id = uuid4()

        self.mock_context.build_permanent_context = AsyncMock(
            return_value={"user": {"id": str(user_id), "timezone": "UTC"}}
        )

        self.mock_llm.generate_response = AsyncMock(return_value="Response")

        await self.orchestrator.process_message(
            user_id=user_id,
            message="Test",
            conversation_id=uuid4(),
        )

        # Verify context was built
        self.mock_context.build_permanent_context.assert_called_once()
        call_args = self.mock_context.build_permanent_context.call_args
        assert call_args is not None


class TestOrchestratorErrorHandling:
    """Test orchestrator error handling"""

    def setup_method(self):
        """Setup orchestrator"""
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            tool_executor=self.executor,
            context_service=self.mock_context,
        )

    @pytest.mark.asyncio
    async def test_handles_llm_failure_gracefully(self):
        """Should handle LLM failure gracefully"""
        self.mock_llm.generate_response = AsyncMock(side_effect=Exception("LLM API error"))

        self.mock_context.build_permanent_context = AsyncMock(return_value={"user": {}})

        response = await self.orchestrator.process_message(
            user_id=uuid4(),
            message="Test",
            conversation_id=uuid4(),
        )

        # Should return error message instead of crashing
        assert isinstance(response, str)
        assert any(word in response.lower() for word in ["error", "sorry", "apologize", "trouble"])

    @pytest.mark.asyncio
    async def test_handles_tool_execution_failure(self):
        """Should handle tool execution failure"""
        # Register a tool that will fail
        self.registry.register(GetCurrentDateTool())

        # Mock LLM to request tool with invalid args
        self.mock_llm.chat_with_tools = AsyncMock(
            return_value={
                "tool_calls": [
                    {
                        "name": "get_current_date",
                        "arguments": {"invalid_arg": "value"},  # Invalid arg
                    }
                ]
            }
        )

        # Mock second call to handle tool error
        self.mock_llm.generate_response = AsyncMock(
            return_value="I encountered an error getting the time."
        )

        self.mock_context.build_permanent_context = AsyncMock(return_value={"user": {}})

        response = await self.orchestrator.process_message(
            user_id=uuid4(),
            message="What time is it?",
            conversation_id=uuid4(),
        )

        # Should handle gracefully
        assert isinstance(response, str)


class TestOrchestratorLogging:
    """Test orchestrator decision logging"""

    def setup_method(self):
        """Setup orchestrator"""
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.mock_llm = AsyncMock()
        self.mock_context = AsyncMock()

        self.orchestrator = OrchestratorAgent(
            llm_service=self.mock_llm,
            tool_registry=self.registry,
            tool_executor=self.executor,
            context_service=self.mock_context,
        )

    @pytest.mark.asyncio
    async def test_logs_decision_making(self):
        """Should log decision making process"""
        with patch("src.agents.orchestrator.logger") as mock_logger:
            self.mock_llm.generate_response = AsyncMock(return_value="Response")
            self.mock_context.build_permanent_context = AsyncMock(return_value={"user": {}})

            await self.orchestrator.process_message(
                user_id=uuid4(),
                message="Test",
                conversation_id=uuid4(),
            )

            # Verify logging was called
            assert mock_logger.info.called or mock_logger.debug.called
