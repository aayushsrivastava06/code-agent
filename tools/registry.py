"""
Tool registry — central list of all tools the agent can call.
Each tool has a name, description, input schema (JSON Schema), and handler function.
"""

from typing import Callable, Any
from dataclasses import dataclass, field


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    handler: Callable
    category: str = "general"
    requires_confirm: bool = False


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def all_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def for_provider(self) -> list[dict]:
        """Return tool schemas in OpenAI function-calling format."""
        result = []
        for tool in self._tools.values():
            result.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            })
        return result

    def call(self, name: str, inputs: dict) -> tuple[str, bool]:
        """Execute a tool by name. Returns (result_str, success)."""
        tool = self._tools.get(name)
        if not tool:
            return f"Unknown tool: {name}", False
        # Normalize inputs
        if inputs is None:
            inputs = {}
        if not isinstance(inputs, dict):
            return f"Tool error in {name}: inputs must be a dict.", False

        # Basic required-field validation using the tool's JSON Schema `required` list
        required = []
        try:
            schema = tool.input_schema or {}
            if isinstance(schema, dict):
                required = schema.get("required", []) or []
        except Exception:
            required = []

        missing = [r for r in required if r not in inputs]
        if missing:
            return f"Error: Missing required arguments: {', '.join(missing)}", False

        try:
            result = tool.handler(**inputs)
            if result is None:
                return "(no output)", True
            return str(result), True
        except TypeError as e:
            # Common case: handler called with missing or wrong args
            return f"Tool TypeError in {name}: {e}", False
        except Exception as e:
            return f"Tool error in {name}: {type(e).__name__}: {e}", False

    def list_by_category(self) -> dict[str, list[str]]:
        cats: dict[str, list[str]] = {}
        for tool in self._tools.values():
            cats.setdefault(tool.category, []).append(tool.name)
        return cats


registry = ToolRegistry()
