"""
Tool Registry for managing and discovering tools

The registry maintains a collection of available tools and provides
methods for registration, discovery, and metadata access.
"""

from typing import Any

from src.tools.base import BaseTool


class ToolRegistry:
    """
    Registry for managing tools

    Maintains a collection of tools and provides methods for:
    - Registering new tools
    - Retrieving tools by name
    - Listing all available tools
    - Unregistering tools
    """

    def __init__(self) -> None:
        """Initialize empty tool registry"""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool in the registry

        Args:
            tool: The tool to register

        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' is already registered. "
                f"Use unregister() first to replace it."
            )

        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        """
        Remove a tool from the registry

        Args:
            tool_name: Name of the tool to remove

        Note:
            Does not raise an error if tool doesn't exist (idempotent)
        """
        self._tools.pop(tool_name, None)

    def get_tool(self, tool_name: str) -> BaseTool | None:
        """
        Retrieve a tool by name

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            The tool instance, or None if not found
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> list[dict[str, Any]]:
        """
        List all registered tools with their metadata

        Returns:
            List of tool metadata dictionaries containing:
            - name: Tool name
            - description: Tool description
            - parameters: Parameter schema
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Get all tools as LLM tool definitions

        Returns:
            List of tool definitions for function calling
        """
        return [tool.to_tool_definition() for tool in self._tools.values()]

    def __len__(self) -> int:
        """Return number of registered tools"""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """Check if tool is registered"""
        return tool_name in self._tools
