"""
Core agent loop — the brain of the agent.
Handles the conversation, tool calling, streaming, and multi-step reasoning.
"""

import json
import sys
import time
import traceback
from typing import Optional, Iterator

from .config import Config
from .context import ConversationContext
from .display import (
    console, print_tool_use, print_tool_result, print_markdown,
    print_error, print_warning, print_info, print_success,
    print_thinking, print_separator, print_compact_tool, COLORS
)
from tools.registry import registry
from providers.base import ProviderError
from providers.factory import create_provider


class Agent:
    """
    The main agent loop — orchestrates AI reasoning + tool calling.
    Mimics Claude Code's agentic architecture:
    1. Receive user message
    2. Call AI model
    3. Parse tool calls from response
    4. Execute tools
    5. Feed results back
    6. Repeat until done
    """

    def __init__(self, config: Config, context: ConversationContext):
        self.config = config
        self.context = context
        self.provider = None
        self._load_provider()
        self.verbose = config.verbose
        self.safe_mode = config.safe_mode
        self.iteration_count = 0

    def _load_provider(self):
        try:
            self.provider = create_provider(self.config)
        except ProviderError as e:
            print_error(str(e))
            self.provider = None

    def switch_provider(self, provider_name: str, model: str = ""):
        self.config.provider = provider_name.lower()
        if model:
            self.config.model = model
        else:
            self.config.model = self.config.get_default_model(provider_name)
        self._load_provider()
        if self.provider:
            print_success(f"Switched to {provider_name} / {self.config.model}")
        return self.provider is not None

    def _get_tools_schema(self) -> list[dict]:
        """Return all registered tools in the provider's function-calling format."""
        return registry.for_provider()

    def _execute_tool(self, name: str, arguments: dict) -> tuple[str, bool]:
        """Execute a tool and return (result, success)."""
        tool = registry.get(name)
        if not tool:
            return f"Tool not found: {name}. Available: {', '.join(t.name for t in registry.all_tools())}", False

        if self.safe_mode and tool.requires_confirm:
            from agent.display import confirm
            if not confirm(f"Allow tool '{name}' with args: {json.dumps(arguments, indent=2)[:200]}?"):
                return "Tool execution cancelled by user.", False

        start = time.time()
        result, success = registry.call(name, arguments)
        duration = time.time() - start

        if self.verbose:
            print_tool_result(name, result, success)
        else:
            status = "✓" if success else "✗"
            preview = result.replace("\n", " ")[:80]
            print_compact_tool(name, f"{status} {preview}")

        return result, success

    def _build_messages_for_api(self) -> list[dict]:
        """Build the message list to send to the API."""
        messages = []
        for msg in self.context.messages:
            if msg.role in ("user", "assistant"):
                api_msg = {"role": msg.role}
                if msg.content is not None and str(msg.content).strip():
                    api_msg["content"] = msg.content
                # If this assistant message included tool_calls but no textual content,
                # avoid sending raw tool_call objects to providers (some reject them).
                # Instead, include a short human-readable placeholder describing the call.
                if msg.role == "assistant" and (not api_msg.get("content")) and getattr(msg, "tool_calls", None):
                    parts = []
                    import json as _json
                    for tc in msg.tool_calls:
                        name = tc.get("name") or (tc.get("function") or {}).get("name")
                        args = tc.get("arguments") or (tc.get("function") or {}).get("arguments") or {}
                        try:
                            arg_s = _json.dumps(args)
                        except Exception:
                            arg_s = str(args)
                        parts.append(f"CALL {name} ARGS {arg_s}")
                    api_msg["content"] = "[tool_calls] " + " ; ".join(parts)
                messages.append(api_msg)
        return messages

    def _handle_tool_calls_response(self, tool_calls: list[dict]) -> str:
        """Execute all tool calls and format results into a follow-up message."""
        tool_results = []
        for tc in tool_calls:
            name = tc.get("name", "")
            arguments = tc.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except Exception:
                    arguments = {}

            print_tool_use(name, arguments)
            result, success = self._execute_tool(name, arguments)

            tool_results.append(
                f"Tool: {name}\n"
                f"Result ({'' if success else 'ERROR — '}{'success' if success else 'failed'}):\n"
                f"{result}"
            )

        combined = "\n\n---\n\n".join(tool_results)
        return combined

    def _stream_response(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """Stream response from provider, collecting full text and any tool calls."""
        if not self.provider:
            return "No provider configured. Use /provider to set one.", []

        tools = self._get_tools_schema()
        full_text = ""
        tool_calls = []

        try:
            resp = self.provider.chat(
                messages=messages,
                tools=tools,
                system=self.context.get_system_prompt(),
                stream=False,
            )

            full_text = resp.get("content", "")
            tool_calls = resp.get("tool_calls", [])
            usage = resp.get("usage", {})

            if usage:
                self.context.total_tokens += usage.get("input", 0) + usage.get("output", 0)

            # If the provider returned neither content nor tool calls, return a clear error
            if (not full_text or not str(full_text).strip()) and not tool_calls:
                err = "Error: assistant returned empty content and no tool calls."
                print_error(err)
                return err, []

            if full_text and not tool_calls:
                print_markdown(full_text)

        except ProviderError as e:
            print_error(f"Provider error: {e}")
            return str(e), []
        except KeyboardInterrupt:
            print_warning("\nInterrupted by user.")
            return full_text, []
        except Exception as e:
            if self.config.verbose:
                traceback.print_exc()
            print_error(f"Unexpected error: {e}")
            return str(e), []

        return full_text, tool_calls

    def run(self, user_message: str) -> str:
        """
        Main agentic loop for a single user turn.
        Runs until the model stops requesting tool calls or max_iterations hit.
        """
        if not self.provider:
            return "No provider configured. Please set API keys in .env and choose a /provider."

        self.context.add_user_message(user_message)
        self.context.trim_to_window(self.config.context_window)

        final_response = ""
        self.iteration_count = 0

        while self.iteration_count < self.config.max_iterations:
            self.iteration_count += 1

            messages = self._build_messages_for_api()
            text, tool_calls = self._stream_response(messages)

            if not tool_calls:
                # Avoid adding empty assistant messages which can break provider APIs
                if text and str(text).strip():
                    self.context.add_assistant_message(text)
                    final_response = text
                else:
                    err_text = "Error: assistant returned empty content. Please retry with clarified input."
                    self.context.add_assistant_message(err_text)
                    final_response = err_text
                break

            self.context.add_assistant_message(text, tool_calls=tool_calls)

            tool_results_text = self._handle_tool_calls_response(tool_calls)

            self.context.add_user_message(
                f"Tool results:\n\n{tool_results_text}\n\n"
                f"Continue with the task. If done, summarize what was accomplished."
            )

            if self.iteration_count >= self.config.max_iterations:
                print_warning(f"Reached max iterations ({self.config.max_iterations}). Stopping.")
                break

        return final_response

    def one_shot(self, user_message: str) -> str:
        """Single-turn response without tool calling, for quick questions."""
        if not self.provider:
            return "No provider configured."
        messages = [{"role": "user", "content": user_message}]
        try:
            resp = self.provider.chat(
                messages=messages,
                tools=None,
                system=self.context.get_system_prompt(),
            )
            return resp.get("content", "")
        except Exception as e:
            return f"Error: {e}"

    def compact_history(self) -> str:
        """Summarize the conversation to save context."""
        if len(self.context.messages) < 4:
            return "Nothing to compact yet."
        history_text = self.context.format_history()
        summary_prompt = (
            f"Summarize this conversation concisely in bullet points, "
            f"focusing on: what the user asked for, what files were changed, "
            f"and what was accomplished.\n\n{history_text[:4000]}"
        )
        summary = self.one_shot(summary_prompt)
        self.context.compact(summary)
        return f"Conversation compacted.\nSummary:\n{summary}"

    @property
    def status(self) -> dict:
        return {
            "provider": self.config.provider,
            "model": self.config.model,
            "workspace": self.context.workspace,
            "messages": len(self.context.messages),
            "tokens_used": self.context.total_tokens,
            "safe_mode": self.safe_mode,
            "verbose": self.verbose,
            "tools_available": len(registry.all_tools()),
            "max_iterations": self.config.max_iterations,
        }
