"""
Conversation context and history management.
Handles message history, summarization, token counting, and memory.
"""

import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Message:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    tool_calls: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)
    tokens: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Message":
        return cls(**d)

    def to_api_format(self) -> dict:
        msg: dict = {"role": self.role, "content": self.content}
        return msg


@dataclass
class ToolCall:
    id: str
    name: str
    inputs: dict
    result: Optional[str] = None
    success: bool = True
    duration: float = 0.0


class ConversationContext:
    """Manages the full conversation history and context window."""

    SYSTEM_PROMPT = """You are an extremely advanced AI coding agent — a direct peer to Claude Code.
You operate directly in the user's terminal, have full access to their filesystem, can run shell commands,
search code, browse the web, and complete complex multi-step engineering tasks autonomously.

## Core Principles
1. **Accuracy first** — Never hallucinate file contents or command outputs. Always read files before editing them.
2. **Think before acting** — For complex tasks, reason through the approach before executing tools.
3. **Minimal footprint** — Make targeted changes. Don't rewrite files unless necessary.
4. **Confirm destructive actions** — Before deleting files, running risky commands, or making broad changes, confirm with the user unless in autonomous mode.
5. **Real code, real results** — Every code change must be syntactically correct and logically sound.
6. **Iterate and recover** — If a command fails, diagnose and fix. Don't give up.
7. **Thorough verification** — After completing tasks, verify the result works as expected.

## Available Tools
You have access to these tools (use them freely and in combination):

### File Operations
- `read_file` — Read any file with optional line range
- `write_file` — Create or overwrite a file
- `edit_file` — Apply targeted find-and-replace edits (preferred for modifications)
- `append_file` — Append content to a file
- `delete_file` — Delete a file (with confirmation)
- `copy_file` — Copy a file to new location
- `move_file` — Move/rename a file
- `list_directory` — List files in a directory with metadata
- `make_directory` — Create directories
- `file_info` — Get file metadata (size, modified time, permissions)

### Code Search & Analysis
- `search_files` — Grep/ripgrep through files with regex support
- `find_files` — Find files by name pattern (like `find`)
- `search_replace` — Find and replace across multiple files
- `get_symbols` — Extract functions, classes, variables from code files
- `get_definition` — Find where a symbol is defined
- `get_references` — Find all references to a symbol
- `analyze_code` — Static analysis and complexity metrics
- `find_todos` — Find TODO/FIXME/HACK comments

### Shell & Process
- `run_command` — Execute any shell command with timeout
- `run_script` — Run a script file (python, bash, node, etc.)
- `check_command` — Test if a command/program is available
- `get_env` — Get environment variables
- `set_env` — Set environment variables for session
- `process_info` — Get running processes
- `kill_process` — Kill a process by PID

### Web & Network
- `web_search` — Search the web (DuckDuckGo, free)
- `fetch_url` — Fetch/scrape a webpage
- `download_file` — Download a file from URL
- `check_url` — Check if a URL is accessible

### Project Intelligence
- `git_status` — Get git status
- `git_log` — Get commit history
- `git_diff` — Get diff of changes
- `git_blame` — See who changed what line
- `git_commit` — Commit changes
- `git_branch` — List/create/switch branches
- `detect_project` — Auto-detect project type, framework, language
- `get_dependencies` — Read package.json/requirements.txt/etc.
- `run_tests` — Run project test suite
- `lint_code` — Run linter on code
- `format_code` — Format code with prettier/black/etc.

### Utilities
- `calculate` — Math calculations and expressions
- `encode_decode` — Base64, URL, HTML encode/decode
- `json_parse` — Parse and query JSON
- `regex_test` — Test regular expressions
- `diff_files` — Show diff between two files
- `create_todo` — Create a task/todo item
- `list_todos` — List current tasks

## Reasoning Style
- Break complex problems into clear steps
- Use `<thinking>` tags when reasoning through hard problems (not visible to user)
- Show your work for complex transformations
- When you're unsure, ask the user before proceeding
- Prefer reading existing code before writing new code

## Error Handling
- If a tool fails, diagnose the error and try alternative approaches
- Never silently fail — always report errors with context
- Retry with corrections on transient failures

## Code Quality Standards
- Follow the project's existing style and conventions
- Write self-documenting code with meaningful names
- Add error handling for edge cases
- Preserve existing tests; add new ones when making changes
- Follow language-specific best practices

You are operating in: {workspace}
Current date: {date}
"""

    def __init__(self, workspace: str = "."):
        import datetime
        self.messages: list[Message] = []
        self.tool_history: list[ToolCall] = []
        self.workspace = workspace
        self.total_tokens = 0
        self.session_start = time.time()
        self._undo_stack: list[dict] = []
        self._date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT.format(workspace=self.workspace, date=self._date)

    def add_user_message(self, content: str) -> Message:
        msg = Message(role="user", content=content)
        self.messages.append(msg)
        return msg

    def add_assistant_message(self, content: str, tool_calls: list = None) -> Message:
        msg = Message(role="assistant", content=content, tool_calls=tool_calls or [])
        self.messages.append(msg)
        return msg

    def add_tool_result(self, tool_name: str, result: str, success: bool = True):
        msg = Message(
            role="tool",
            content=result,
            tool_results=[{"name": tool_name, "success": success}],
        )
        self.messages.append(msg)
        return msg

    def get_messages_for_api(self, provider: str = "generic") -> list[dict]:
        result = []
        for msg in self.messages:
            if msg.role == "tool":
                continue
            result.append({"role": msg.role, "content": msg.content})
        return result

    def push_undo(self, operation: dict):
        self._undo_stack.append(operation)
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)

    def pop_undo(self) -> Optional[dict]:
        if self._undo_stack:
            return self._undo_stack.pop()
        return None

    def compact(self, summary: str):
        self.messages = [Message(role="assistant", content=f"[Conversation summary: {summary}]")]

    def reset(self):
        self.messages = []
        self.tool_history = []
        self.total_tokens = 0
        self._undo_stack = []

    def save(self, path: Path):
        data = {
            "workspace": self.workspace,
            "session_start": self.session_start,
            "total_tokens": self.total_tokens,
            "messages": [m.to_dict() for m in self.messages],
        }
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: Path):
        data = json.loads(path.read_text())
        self.workspace = data.get("workspace", ".")
        self.session_start = data.get("session_start", time.time())
        self.total_tokens = data.get("total_tokens", 0)
        self.messages = [Message.from_dict(m) for m in data.get("messages", [])]

    def get_stats(self) -> dict:
        elapsed = time.time() - self.session_start
        return {
            "messages": len(self.messages),
            "tool_calls": len(self.tool_history),
            "estimated_tokens": self.total_tokens,
            "session_duration": f"{elapsed:.0f}s",
            "workspace": self.workspace,
        }

    def estimate_tokens(self) -> int:
        total = 0
        for msg in self.messages:
            total += len(msg.content) // 4
        return total

    def trim_to_window(self, max_tokens: int = 80000):
        while self.estimate_tokens() > max_tokens and len(self.messages) > 2:
            self.messages.pop(1)

    @property
    def last_assistant_message(self) -> Optional[str]:
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                return msg.content
        return None

    def format_history(self) -> str:
        lines = []
        for msg in self.messages:
            role = msg.role.upper()
            ts = time.strftime("%H:%M:%S", time.localtime(msg.timestamp))
            lines.append(f"[{ts}] {role}: {msg.content[:200]}")
        return "\n".join(lines)
