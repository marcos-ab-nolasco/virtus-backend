"""
Tool Executor for executing tools from the registry

Handles tool invocation, error handling, and result formatting.
"""

import logging
from typing import Any

from src.tools.base import ToolResult
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when tool execution fails"""

    pass


class ToolExecutor:
    """
    Executes tools from the registry

    Provides a safe interface for executing tools with:
    - Error handling
    - Logging
    - Result formatting
    """

    def __init__(self, registry: ToolRegistry) -> None:
        """
        Initialize executor with a tool registry

        Args:
            registry: The tool registry to use for tool lookup
        """
        self.registry = registry

    async def execute(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        """
        Execute a tool by name with the given arguments

        Args:
            tool_name: Name of the tool to execute
            args: Dictionary of arguments to pass to the tool

        Returns:
            ToolResult with success status, data, and/or error message

        Raises:
            ToolExecutionError: If the tool is not found in the registry
        """
        # Get tool from registry
        tool = self.registry.get_tool(tool_name)
        if tool is None:
            error_msg = f"Tool '{tool_name}' not found in registry"
            logger.error(error_msg)
            raise ToolExecutionError(error_msg)

        # Execute tool with error handling
        try:
            logger.info(f"Executing tool: {tool_name} with args: {args}")
            result = await tool.execute(args)
            logger.info(f"Tool {tool_name} completed: success={result.success}")
            return result

        except Exception as e:
            # Catch any errors during execution and return as error result
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Tool {tool_name} failed: {error_msg}", exc_info=True)

            return ToolResult(success=False, data=None, error=error_msg)

    async def execute_with_fallback(
        self, tool_name: str, args: dict[str, Any], fallback_message: str | None = None
    ) -> ToolResult:
        """
        Execute tool with fallback message if tool not found

        Args:
            tool_name: Name of the tool to execute
            args: Arguments to pass to the tool
            fallback_message: Message to return if tool not found

        Returns:
            ToolResult (always succeeds, uses fallback if tool not found)
        """
        try:
            return await self.execute(tool_name, args)
        except ToolExecutionError as e:
            if fallback_message is None:
                fallback_message = f"Tool '{tool_name}' is not available"

            logger.warning(f"Using fallback for {tool_name}: {e}")
            return ToolResult(success=False, data=None, error=fallback_message)
