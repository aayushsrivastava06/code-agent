"""
Utility tools — math, JSON, regex, base64, todo lists, project init.
"""

import json
import re
import base64
import urllib.parse
import hashlib
import time
import uuid
from pathlib import Path
from typing import Optional
from .registry import registry, ToolDefinition

_todos: list[dict] = []


def calculate(expression: str) -> str:
    try:
        safe_names = {
            "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
            "pow": pow, "int": int, "float": float, "len": len,
        }
        try:
            import math
            safe_names.update({k: v for k, v in vars(math).items() if not k.startswith("_")})
        except ImportError:
            pass
        result = eval(expression, {"__builtins__": {}}, safe_names)
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error evaluating '{expression}': {e}"


def encode_decode(text: str, operation: str = "base64_encode") -> str:
    try:
        ops = {
            "base64_encode": lambda t: base64.b64encode(t.encode()).decode(),
            "base64_decode": lambda t: base64.b64decode(t.encode()).decode(errors="replace"),
            "url_encode": lambda t: urllib.parse.quote(t),
            "url_decode": lambda t: urllib.parse.unquote(t),
            "html_encode": lambda t: t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"),
            "html_decode": lambda t: t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'),
            "hex_encode": lambda t: t.encode().hex(),
            "hex_decode": lambda t: bytes.fromhex(t).decode(errors="replace"),
            "md5": lambda t: hashlib.md5(t.encode()).hexdigest(),
            "sha256": lambda t: hashlib.sha256(t.encode()).hexdigest(),
            "sha1": lambda t: hashlib.sha1(t.encode()).hexdigest(),
            "rot13": lambda t: t.translate(str.maketrans(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
            )),
            "reverse": lambda t: t[::-1],
            "upper": lambda t: t.upper(),
            "lower": lambda t: t.lower(),
            "count_chars": lambda t: f"Length: {len(t)} chars, {len(t.encode())} bytes, {len(t.split())} words, {len(t.splitlines())} lines",
        }
        if operation not in ops:
            return f"Unknown operation: {operation}. Available: {', '.join(ops.keys())}"
        return ops[operation](text)
    except Exception as e:
        return f"Error in {operation}: {e}"


def json_parse(content: str, query: str = "", pretty: bool = True) -> str:
    try:
        data = json.loads(content)
        if query:
            parts = query.lstrip("$.").split(".")
            current = data
            for part in parts:
                if "[" in part:
                    key, idx_str = part.split("[", 1)
                    idx = int(idx_str.rstrip("]"))
                    if key:
                        current = current[key]
                    current = current[idx]
                elif isinstance(current, dict):
                    current = current[part]
                elif isinstance(current, list):
                    current = [item.get(part) if isinstance(item, dict) else item for item in current]
            data = current
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        return json.dumps(data, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f"JSON parse error: {e}"
    except (KeyError, IndexError, TypeError) as e:
        return f"Query error at '{query}': {e}"
    except Exception as e:
        return f"Error: {e}"


def regex_test(pattern: str, text: str, flags_str: str = "") -> str:
    try:
        flag_map = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL, "x": re.VERBOSE}
        flags = 0
        for f in flags_str:
            if f in flag_map:
                flags |= flag_map[f]
        regex = re.compile(pattern, flags)
        matches = list(regex.finditer(text))
        if not matches:
            return f"Pattern '{pattern}' — No matches found in text."
        result_lines = [f"Pattern: {pattern}", f"Matches: {len(matches)}", ""]
        for i, m in enumerate(matches[:20]):
            result_lines.append(f"Match {i+1}: {repr(m.group())} at position {m.start()}-{m.end()}")
            if m.groups():
                for j, g in enumerate(m.groups(), 1):
                    result_lines.append(f"  Group {j}: {repr(g)}")
            if m.groupdict():
                for k, v in m.groupdict().items():
                    result_lines.append(f"  Named group '{k}': {repr(v)}")
        if len(matches) > 20:
            result_lines.append(f"... and {len(matches) - 20} more matches")
        return "\n".join(result_lines)
    except re.error as e:
        return f"Invalid regex: {e}"
    except Exception as e:
        return f"Error: {e}"


def create_todo(title: str, priority: str = "medium", tags: str = "") -> str:
    todo = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "priority": priority,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "done": False,
    }
    _todos.append(todo)
    return f"Created todo [{todo['id']}]: {title} (priority: {priority})"


def list_todos(show_done: bool = False) -> str:
    items = _todos if show_done else [t for t in _todos if not t["done"]]
    if not items:
        return "No todos." if show_done else "No pending todos."
    lines = []
    for t in items:
        status = "✓" if t["done"] else "○"
        priority_colors = {"high": "!", "medium": "-", "low": "·"}
        p = priority_colors.get(t["priority"], "-")
        tags = f" [{', '.join(t['tags'])}]" if t["tags"] else ""
        lines.append(f"  [{t['id']}] {status} {p} {t['title']}{tags}")
    return f"Todos ({len(items)} items):\n" + "\n".join(lines)


def complete_todo(todo_id: str) -> str:
    for t in _todos:
        if t["id"] == todo_id:
            t["done"] = True
            return f"Completed: {t['title']}"
    return f"Todo not found: {todo_id}"


def generate_uuid(count: int = 1) -> str:
    if count == 1:
        return str(uuid.uuid4())
    return "\n".join(str(uuid.uuid4()) for _ in range(min(count, 20)))


def timestamp_convert(ts: str = "", format_str: str = "") -> str:
    try:
        if not ts:
            now = time.time()
            return (
                f"Current Unix timestamp: {now:.0f}\n"
                f"UTC: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(now))}\n"
                f"Local: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}"
            )
        ts_float = float(ts)
        utc = time.strftime(format_str or "%Y-%m-%d %H:%M:%S", time.gmtime(ts_float))
        local = time.strftime(format_str or "%Y-%m-%d %H:%M:%S", time.localtime(ts_float))
        return f"Unix: {ts}\nUTC: {utc}\nLocal: {local}"
    except Exception as e:
        return f"Error converting timestamp: {e}"


def init_project(project_type: str = "python", name: str = "myproject", workspace: str = ".") -> str:
    from pathlib import Path
    base = Path(workspace)
    created = []

    templates = {
        "python": {
            "README.md": f"# {name}\n\nA Python project.\n\n## Setup\n\n```bash\npip install -r requirements.txt\npython main.py\n```\n",
            "main.py": f'#!/usr/bin/env python3\n"""Main entry point for {name}."""\n\n\ndef main():\n    print("Hello from {name}!")\n\n\nif __name__ == "__main__":\n    main()\n',
            "requirements.txt": "# Add your dependencies here\n",
            ".gitignore": "__pycache__/\n*.pyc\n*.pyo\n.env\nvenv/\n.venv/\ndist/\nbuild/\n*.egg-info/\n",
            "tests/__init__.py": "",
            "tests/test_main.py": f'"""Tests for {name}."""\nimport pytest\n\n\ndef test_placeholder():\n    assert True\n',
        },
        "node": {
            "README.md": f"# {name}\n\n## Setup\n\n```bash\nnpm install\nnode index.js\n```\n",
            "index.js": f'// {name}\n\nconsole.log("Hello from {name}!");\n',
            "package.json": json.dumps({"name": name, "version": "1.0.0", "main": "index.js", "scripts": {"start": "node index.js", "test": "echo \"Error: no test specified\" && exit 1"}, "keywords": [], "author": "", "license": "ISC"}, indent=2),
            ".gitignore": "node_modules/\n.env\ndist/\nbuild/\n",
        },
        "typescript": {
            "README.md": f"# {name}\n\n## Setup\n\n```bash\nnpm install\nnpx ts-node src/index.ts\n```\n",
            "src/index.ts": f'// {name}\n\nconst main = (): void => {{\n  console.log("Hello from {name}!");\n}};\n\nmain();\n',
            "tsconfig.json": json.dumps({"compilerOptions": {"target": "ES2020", "module": "commonjs", "strict": True, "esModuleInterop": True, "outDir": "./dist"}, "include": ["src/**/*"]}, indent=2),
            "package.json": json.dumps({"name": name, "version": "1.0.0", "scripts": {"start": "ts-node src/index.ts", "build": "tsc", "test": "jest"}, "devDependencies": {"typescript": "^5.0.0", "ts-node": "^10.0.0", "@types/node": "^20.0.0"}}, indent=2),
            ".gitignore": "node_modules/\ndist/\n.env\n",
        },
        "fastapi": {
            "README.md": f"# {name}\n\n## Setup\n\n```bash\npip install -r requirements.txt\nuvicorn main:app --reload\n```\n",
            "main.py": f'from fastapi import FastAPI\n\napp = FastAPI(title="{name}")\n\n\n@app.get("/")\ndef root():\n    return {{"message": "Hello from {name}!"}}\n\n\n@app.get("/health")\ndef health():\n    return {{"status": "ok"}}\n',
            "requirements.txt": "fastapi>=0.100.0\nuvicorn[standard]>=0.20.0\npydantic>=2.0.0\n",
            ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n.venv/\n",
        },
    }

    template = templates.get(project_type, templates["python"])
    for filepath, content in template.items():
        full = base / filepath
        full.parent.mkdir(parents=True, exist_ok=True)
        if not full.exists():
            full.write_text(content, encoding="utf-8")
            created.append(filepath)

    result = f"Initialized {project_type} project '{name}':\n"
    result += "\n".join(f"  + {f}" for f in created)
    result += "\n\nNext: git init && git add -A && git commit -m 'Initial commit'"
    return result


def register_utility_tools(workspace_getter):
    def ws():
        return workspace_getter()

    tools = [
        ToolDefinition(
            name="calculate",
            description="Evaluate a mathematical expression. Supports standard math functions (sqrt, sin, cos, log, etc.).",
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression to evaluate (e.g. '2 ** 32', 'sqrt(144)', '(3.14 * 5 ** 2)')"},
                },
                "required": ["expression"],
            },
            handler=lambda expression: calculate(expression),
            category="utility",
        ),
        ToolDefinition(
            name="encode_decode",
            description="Encode/decode text or compute hashes. Operations: base64_encode, base64_decode, url_encode, url_decode, html_encode, html_decode, hex_encode, hex_decode, md5, sha256, sha1, rot13, reverse, upper, lower, count_chars.",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Input text"},
                    "operation": {"type": "string", "description": "Operation to apply", "default": "base64_encode"},
                },
                "required": ["text"],
            },
            handler=lambda text, operation="base64_encode": encode_decode(text, operation),
            category="utility",
        ),
        ToolDefinition(
            name="json_parse",
            description="Parse JSON content and optionally query it using dot notation (e.g. '$.user.name', '$.items[0]').",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "JSON string to parse"},
                    "query": {"type": "string", "description": "Dot-notation path to extract (e.g. '$.key.subkey')", "default": ""},
                    "pretty": {"type": "boolean", "description": "Pretty-print output", "default": True},
                },
                "required": ["content"],
            },
            handler=lambda content, query="", pretty=True: json_parse(content, query, pretty),
            category="utility",
        ),
        ToolDefinition(
            name="regex_test",
            description="Test a regular expression against text. Shows all matches with groups.",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern"},
                    "text": {"type": "string", "description": "Text to test against"},
                    "flags_str": {"type": "string", "description": "Flags: i=case-insensitive, m=multiline, s=dotall", "default": ""},
                },
                "required": ["pattern", "text"],
            },
            handler=lambda pattern, text, flags_str="": regex_test(pattern, text, flags_str),
            category="utility",
        ),
        ToolDefinition(
            name="create_todo",
            description="Create a task/todo item to track work items.",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task description"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"], "default": "medium"},
                    "tags": {"type": "string", "description": "Comma-separated tags"},
                },
                "required": ["title"],
            },
            handler=lambda title, priority="medium", tags="": create_todo(title, priority, tags),
            category="utility",
        ),
        ToolDefinition(
            name="list_todos",
            description="List current todo items.",
            input_schema={
                "type": "object",
                "properties": {
                    "show_done": {"type": "boolean", "description": "Include completed items", "default": False},
                },
                "required": [],
            },
            handler=lambda show_done=False: list_todos(show_done),
            category="utility",
        ),
        ToolDefinition(
            name="generate_uuid",
            description="Generate one or more UUIDs.",
            input_schema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of UUIDs to generate", "default": 1},
                },
                "required": [],
            },
            handler=lambda count=1: generate_uuid(count),
            category="utility",
        ),
        ToolDefinition(
            name="timestamp_convert",
            description="Convert Unix timestamps to human-readable dates, or get the current timestamp.",
            input_schema={
                "type": "object",
                "properties": {
                    "ts": {"type": "string", "description": "Unix timestamp (leave empty for current time)"},
                    "format_str": {"type": "string", "description": "strftime format string"},
                },
                "required": [],
            },
            handler=lambda ts="", format_str="": timestamp_convert(ts, format_str),
            category="utility",
        ),
        ToolDefinition(
            name="init_project",
            description="Initialize a new project with standard structure and boilerplate files. Types: python, node, typescript, fastapi.",
            input_schema={
                "type": "object",
                "properties": {
                    "project_type": {"type": "string", "enum": ["python", "node", "typescript", "fastapi"], "default": "python"},
                    "name": {"type": "string", "description": "Project name", "default": "myproject"},
                },
                "required": [],
            },
            handler=lambda project_type="python", name="myproject": init_project(project_type, name, ws()),
            category="utility",
        ),
    ]
    for tool in tools:
        registry.register(tool)
