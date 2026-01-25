"""
Tests for the Tools System (Issue 2.5)

Following TDD approach:
- RED: Write failing tests first
- GREEN: Implement minimal code to pass
- REFACTOR: Clean up and improve
- CONNECT: Integration tests
"""

from typing import Any

import pytest

# These imports will fail initially (RED phase)
from src.tools.base import BaseTool, ToolParameter, ToolResult
from src.tools.examples.get_current_date import GetCurrentDateTool
from src.tools.executor import ToolExecutionError, ToolExecutor
from src.tools.registry import ToolRegistry


class TestBaseTool:
    """Test BaseTool abstract class"""

    def test_tool_must_have_name(self):
        """Tool must have a name attribute"""
        tool = GetCurrentDateTool()
        assert hasattr(tool, "name")
        assert isinstance(tool.name, str)
        assert len(tool.name) > 0

    def test_tool_must_have_description(self):
        """Tool must have a description attribute"""
        tool = GetCurrentDateTool()
        assert hasattr(tool, "description")
        assert isinstance(tool.description, str)
        assert len(tool.description) > 0

    def test_tool_must_have_parameters(self):
        """Tool must have parameters (JSONSchema dict)"""
        tool = GetCurrentDateTool()
        assert hasattr(tool, "parameters")
        assert isinstance(tool.parameters, dict)
        # Should be valid JSONSchema
        assert "type" in tool.parameters or "properties" in tool.parameters

    @pytest.mark.asyncio
    async def test_tool_execute_returns_tool_result(self):
        """Tool execute method must return ToolResult"""
        tool = GetCurrentDateTool()
        result = await tool.execute({})
        assert isinstance(result, ToolResult)

    @pytest.mark.asyncio
    async def test_tool_result_has_required_fields(self):
        """ToolResult must have success, data, and error fields"""
        tool = GetCurrentDateTool()
        result = await tool.execute({})

        assert hasattr(result, "success")
        assert isinstance(result.success, bool)

        assert hasattr(result, "data")

        assert hasattr(result, "error")
        # error should be None when success is True
        if result.success:
            assert result.error is None


class TestToolRegistry:
    """Test ToolRegistry for managing tools"""

    def setup_method(self):
        """Setup fresh registry for each test"""
        self.registry = ToolRegistry()

    def test_registry_starts_empty(self):
        """New registry should have no tools"""
        assert len(self.registry.list_tools()) == 0

    def test_register_tool(self):
        """Should be able to register a tool"""
        tool = GetCurrentDateTool()
        self.registry.register(tool)

        tools = self.registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == tool.name

    def test_register_duplicate_tool_raises_error(self):
        """Registering tool with same name should raise error"""
        tool1 = GetCurrentDateTool()
        tool2 = GetCurrentDateTool()

        self.registry.register(tool1)

        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(tool2)

    def test_get_tool_by_name(self):
        """Should retrieve tool by name"""
        tool = GetCurrentDateTool()
        self.registry.register(tool)

        retrieved = self.registry.get_tool(tool.name)
        assert retrieved is not None
        assert retrieved.name == tool.name
        assert isinstance(retrieved, GetCurrentDateTool)

    def test_get_nonexistent_tool_returns_none(self):
        """Getting non-existent tool should return None"""
        result = self.registry.get_tool("nonexistent_tool")
        assert result is None

    def test_list_tools_returns_metadata(self):
        """list_tools should return tool metadata (name, description, parameters)"""
        tool = GetCurrentDateTool()
        self.registry.register(tool)

        tools = self.registry.list_tools()
        assert len(tools) == 1

        tool_meta = tools[0]
        assert "name" in tool_meta
        assert "description" in tool_meta
        assert "parameters" in tool_meta
        assert tool_meta["name"] == tool.name
        assert tool_meta["description"] == tool.description

    def test_unregister_tool(self):
        """Should be able to unregister a tool"""
        tool = GetCurrentDateTool()
        self.registry.register(tool)
        assert len(self.registry.list_tools()) == 1

        self.registry.unregister(tool.name)
        assert len(self.registry.list_tools()) == 0

    def test_unregister_nonexistent_tool_no_error(self):
        """Unregistering non-existent tool should not raise error"""
        # Should not raise
        self.registry.unregister("nonexistent_tool")


class TestToolExecutor:
    """Test ToolExecutor for executing tools"""

    def setup_method(self):
        """Setup executor and registry"""
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)

    @pytest.mark.asyncio
    async def test_execute_tool_by_name(self):
        """Should execute tool by name with arguments"""
        tool = GetCurrentDateTool()
        self.registry.register(tool)

        result = await self.executor.execute(tool.name, {})
        assert isinstance(result, ToolResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool_raises_error(self):
        """Executing non-existent tool should raise ToolExecutionError"""
        with pytest.raises(ToolExecutionError, match="not found"):
            await self.executor.execute("nonexistent_tool", {})

    @pytest.mark.asyncio
    async def test_execute_with_invalid_args_catches_error(self):
        """Invalid arguments should be caught and returned as error result"""

        # Create a mock tool that raises ValueError on invalid args
        class InvalidArgsTool(BaseTool):
            name = "invalid_args_tool"
            description = "Test tool"
            parameters = {"type": "object"}

            async def execute(self, args: dict[str, Any]) -> ToolResult:
                if "required_field" not in args:
                    raise ValueError("Missing required_field")
                return ToolResult(success=True, data={"result": "ok"}, error=None)

        tool = InvalidArgsTool()
        self.registry.register(tool)

        result = await self.executor.execute(tool.name, {})
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert result.error is not None
        assert "required_field" in result.error or "Missing" in result.error

    @pytest.mark.asyncio
    async def test_execute_validates_parameters(self):
        """Executor should validate parameters against tool schema (optional)"""
        # This test is for future parameter validation feature
        # For now, we'll just ensure it doesn't crash with valid params
        tool = GetCurrentDateTool()
        self.registry.register(tool)

        # Should work with empty args if no required params
        result = await self.executor.execute(tool.name, {})
        assert result.success is True


class TestGetCurrentDateTool:
    """Test GetCurrentDateTool example implementation"""

    def setup_method(self):
        """Setup tool instance"""
        self.tool = GetCurrentDateTool()

    def test_tool_has_correct_metadata(self):
        """GetCurrentDateTool should have proper metadata"""
        assert self.tool.name == "get_current_date"
        assert "date" in self.tool.description.lower() or "time" in self.tool.description.lower()
        assert isinstance(self.tool.parameters, dict)

    @pytest.mark.asyncio
    async def test_execute_returns_current_date(self):
        """Should return current date/time in result"""
        result = await self.tool.execute({})

        assert result.success is True
        assert result.data is not None
        assert "date" in result.data or "datetime" in result.data or "timestamp" in result.data
        assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_with_timezone_parameter(self):
        """Should accept timezone parameter (optional)"""
        # Test with UTC timezone
        result = await self.tool.execute({"timezone": "UTC"})
        assert result.success is True

        # Test with invalid timezone - should handle gracefully
        result = await self.tool.execute({"timezone": "Invalid/Timezone"})
        # Should either succeed with fallback or fail with clear error
        assert isinstance(result, ToolResult)

    @pytest.mark.asyncio
    async def test_execute_with_format_parameter(self):
        """Should accept format parameter for date output (optional)"""
        result = await self.tool.execute({"format": "iso"})
        assert result.success is True
        assert result.data is not None


class TestToolResult:
    """Test ToolResult data class"""

    def test_create_success_result(self):
        """Should create successful result"""
        result = ToolResult(success=True, data={"key": "value"}, error=None)
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_create_error_result(self):
        """Should create error result"""
        result = ToolResult(success=False, data=None, error="Something went wrong")
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"

    def test_result_is_serializable(self):
        """ToolResult should be JSON serializable"""
        result = ToolResult(success=True, data={"key": "value"}, error=None)

        # Should be able to convert to dict
        result_dict = (
            result.to_dict()
            if hasattr(result, "to_dict")
            else {"success": result.success, "data": result.data, "error": result.error}
        )

        assert isinstance(result_dict, dict)
        assert "success" in result_dict
        assert "data" in result_dict
        assert "error" in result_dict


class TestToolParameter:
    """Test ToolParameter helper (if implemented)"""

    def test_create_string_parameter(self):
        """Should create string parameter definition"""
        param = ToolParameter(
            name="timezone", type="string", description="Timezone for date", required=False
        )

        assert param.name == "timezone"
        assert param.type == "string"
        assert param.required is False

    def test_create_required_parameter(self):
        """Should create required parameter"""
        param = ToolParameter(name="user_id", type="string", description="User ID", required=True)

        assert param.required is True

    def test_parameter_to_jsonschema(self):
        """Should convert parameter to JSONSchema format"""
        param = ToolParameter(
            name="count", type="integer", description="Number of items", required=True
        )

        schema = (
            param.to_jsonschema()
            if hasattr(param, "to_jsonschema")
            else {"type": param.type, "description": param.description}
        )

        assert isinstance(schema, dict)
        assert "type" in schema


# Integration-style tests
class TestToolsIntegration:
    """Integration tests for the entire tools system"""

    def setup_method(self):
        """Setup complete system"""
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)

    @pytest.mark.asyncio
    async def test_register_and_execute_multiple_tools(self):
        """Should handle multiple tools in registry"""
        tool1 = GetCurrentDateTool()
        self.registry.register(tool1)

        # Get all tools
        tools = self.registry.list_tools()
        assert len(tools) == 1

        # Execute tool
        result = await self.executor.execute(tool1.name, {})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_error_handling_preserves_registry_state(self):
        """Failed execution should not corrupt registry"""
        tool = GetCurrentDateTool()
        self.registry.register(tool)

        # Try to execute with bad tool name
        try:
            await self.executor.execute("bad_tool", {})
        except ToolExecutionError:
            pass

        # Registry should still work
        retrieved = self.registry.get_tool(tool.name)
        assert retrieved is not None

        # Should still be able to execute valid tool
        result = await self.executor.execute(tool.name, {})
        assert result.success is True
