"""
Base class for all AI providers.
Each provider implements chat completion with tool/function calling support.
"""

from abc import ABC, abstractmethod
from typing import Iterator, Optional


class BaseProvider(ABC):
    name: str = "base"
    supports_streaming: bool = True
    supports_tools: bool = True

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        system: str = "",
        stream: bool = False,
    ) -> dict:
        """
        Send a chat request and return a normalized response dict:
        {
            "content": str,                  # text response
            "tool_calls": [                  # may be empty
                {
                    "id": str,
                    "name": str,
                    "arguments": dict,
                }
            ],
            "stop_reason": str,              # "end_turn", "tool_use", "max_tokens", "stop"
            "usage": {"input": int, "output": int},
        }
        """
        ...

    def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        system: str = "",
    ) -> Iterator[str]:
        """Stream text tokens. Override if provider supports native streaming."""
        response = self.chat(messages, tools, system, stream=False)
        yield response.get("content", "")

    def normalize_messages(self, messages: list[dict]) -> list[dict]:
        """Ensure messages follow the provider's expected format."""
        normalized = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant"):
                api_msg = {"role": role}
                # Include content if present and non-empty
                if content is not None and str(content).strip():
                    api_msg["content"] = str(content)
                # Preserve any tool_calls attached to assistant messages
                if role == "assistant" and msg.get("tool_calls"):
                    api_msg["tool_calls"] = msg.get("tool_calls")
                normalized.append(api_msg)
        return normalized

    def _extract_tool_calls(self, raw_calls: list) -> list[dict]:
        """Normalize tool calls from provider-specific format."""
        result = []
        for call in raw_calls:
            if isinstance(call, dict):
                fn = call.get("function", call)
                import json
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                result.append({
                    "id": call.get("id", f"call_{len(result)}"),
                    "name": fn.get("name", ""),
                    "arguments": args,
                })
        return result


class ProviderError(Exception):
    """Raised when a provider call fails."""
    pass
