"""
Shell / bash execution tools. Runs commands with timeout, captures output.
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Optional

from .registry import registry, ToolDefinition


def run_command(
    command: str,
    timeout: int = 30,
    workspace: str = ".",
    env_vars: Optional[dict] = None,
    stdin_input: Optional[str] = None,
) -> str:
    try:
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        is_windows = sys.platform == "win32"
        shell_cmd = command if is_windows else command

        result = subprocess.run(
            shell_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workspace,
            env=env,
            input=stdin_input,
        )

        out_lines = result.stdout.splitlines()
        err_lines = result.stderr.splitlines()
        MAX = 300

        output_parts = []
        if out_lines:
            if len(out_lines) > MAX:
                output_parts.append(f"[stdout — showing last {MAX} of {len(out_lines)} lines]")
                output_parts.extend(out_lines[-MAX:])
            else:
                output_parts.extend(out_lines)

        if err_lines:
            output_parts.append("")
            output_parts.append("[stderr]")
            if len(err_lines) > MAX:
                output_parts.append(f"[showing last {MAX} of {len(err_lines)} lines]")
                output_parts.extend(err_lines[-MAX:])
            else:
                output_parts.extend(err_lines)

        exit_str = f"\n[Exit code: {result.returncode}]"
        if not output_parts:
            return f"(no output){exit_str}"
        return "\n".join(output_parts) + exit_str

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout}s. Use a longer timeout or break the task into smaller commands."
    except FileNotFoundError as e:
        return f"Error: Command not found: {e}"
    except Exception as e:
        return f"Error running command: {type(e).__name__}: {e}"


def run_script(
    script_path: str,
    args: str = "",
    interpreter: Optional[str] = None,
    timeout: int = 60,
    workspace: str = ".",
) -> str:
    try:
        p = Path(workspace) / script_path if not Path(script_path).is_absolute() else Path(script_path)
        if not p.exists():
            return f"Error: Script not found: {script_path}"

        ext = p.suffix.lower()
        interp_map = {
            ".py": "python",
            ".js": "node",
            ".ts": "npx ts-node",
            ".sh": "bash",
            ".bat": "",
            ".ps1": "powershell -File",
            ".rb": "ruby",
            ".php": "php",
            ".pl": "perl",
            ".r": "Rscript",
        }

        if not interpreter:
            interpreter = interp_map.get(ext, "")

        if interpreter:
            cmd = f"{interpreter} {p} {args}".strip()
        else:
            cmd = f"{p} {args}".strip()

        return run_command(cmd, timeout=timeout, workspace=workspace)
    except Exception as e:
        return f"Error running script: {e}"


def check_command(command: str) -> str:
    path = shutil.which(command)
    if path:
        result = run_command(f"{command} --version 2>&1 || {command} -v 2>&1 || echo 'available'", timeout=5)
        return f"✓ Found: {command} at {path}\n{result[:200]}"
    return f"✗ Not found: {command} (not in PATH)"


def get_env(variable_name: Optional[str] = None) -> str:
    if variable_name:
        val = os.environ.get(variable_name)
        if val is None:
            return f"Environment variable '{variable_name}' is not set."
        masked = val if "key" not in variable_name.lower() and "secret" not in variable_name.lower() else val[:4] + "****"
        return f"{variable_name}={masked}"
    safe_keys = [
        "PATH", "HOME", "USER", "SHELL", "PWD", "LANG", "TERM",
        "VIRTUAL_ENV", "CONDA_DEFAULT_ENV", "NODE_ENV", "PYTHON_VERSION",
        "JAVA_HOME", "GOPATH", "CARGO_HOME", "NVM_DIR",
    ]
    lines = []
    for k in safe_keys:
        v = os.environ.get(k)
        if v:
            lines.append(f"{k}={v[:100]}")
    return "\n".join(lines) if lines else "No common environment variables found."


def set_env(variable_name: str, value: str) -> str:
    os.environ[variable_name] = value
    return f"Set {variable_name}={value[:20]}{'...' if len(value) > 20 else ''} (session only)"


def process_info(filter_name: Optional[str] = None) -> str:
    try:
        if sys.platform == "win32":
            cmd = "tasklist"
        else:
            cmd = "ps aux --sort=-%cpu | head -20"
        result = run_command(cmd, timeout=5)
        if filter_name:
            lines = [l for l in result.splitlines() if filter_name.lower() in l.lower()]
            return "\n".join(lines) if lines else f"No processes matching '{filter_name}'"
        return result
    except Exception as e:
        return f"Error getting process info: {e}"


def kill_process(pid: int) -> str:
    try:
        if sys.platform == "win32":
            result = run_command(f"taskkill /PID {pid} /F", timeout=5)
        else:
            result = run_command(f"kill {pid}", timeout=5)
        return result
    except Exception as e:
        return f"Error killing process {pid}: {e}"


def register_bash_tools(workspace_getter):
    def ws():
        return workspace_getter()

    tools = [
        ToolDefinition(
            name="run_command",
            description=(
                "Execute a shell command and return its output. "
                "Supports any command available in the system shell. "
                "Use timeout for long-running commands. "
                "On Windows, uses cmd.exe; on Unix, uses /bin/sh."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30, max: 300)",
                        "default": 30,
                    },
                    "stdin_input": {
                        "type": "string",
                        "description": "Optional stdin input for the command",
                    },
                },
                "required": ["command"],
            },
            handler=lambda command, timeout=30, stdin_input=None: run_command(
                command, timeout, ws(), stdin_input=stdin_input
            ),
            category="shell",
        ),
        ToolDefinition(
            name="run_script",
            description="Run a script file. Automatically detects interpreter from extension (.py, .js, .sh, .ts, etc.).",
            input_schema={
                "type": "object",
                "properties": {
                    "script_path": {"type": "string", "description": "Path to the script"},
                    "args": {"type": "string", "description": "Command-line arguments", "default": ""},
                    "interpreter": {"type": "string", "description": "Override interpreter (e.g., 'python3', 'node')"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 60},
                },
                "required": ["script_path"],
            },
            handler=lambda script_path, args="", interpreter=None, timeout=60: run_script(
                script_path, args, interpreter, timeout, ws()
            ),
            category="shell",
        ),
        ToolDefinition(
            name="check_command",
            description="Check if a command/program is installed and get its version.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command name to check"},
                },
                "required": ["command"],
            },
            handler=lambda command: check_command(command),
            category="shell",
        ),
        ToolDefinition(
            name="get_env",
            description="Get environment variables. Returns a specific variable or safe common ones.",
            input_schema={
                "type": "object",
                "properties": {
                    "variable_name": {"type": "string", "description": "Variable name (omit for common vars)"},
                },
                "required": [],
            },
            handler=lambda variable_name=None: get_env(variable_name),
            category="shell",
        ),
        ToolDefinition(
            name="set_env",
            description="Set an environment variable for the current session.",
            input_schema={
                "type": "object",
                "properties": {
                    "variable_name": {"type": "string", "description": "Variable name"},
                    "value": {"type": "string", "description": "Variable value"},
                },
                "required": ["variable_name", "value"],
            },
            handler=lambda variable_name, value: set_env(variable_name, value),
            category="shell",
        ),
        ToolDefinition(
            name="process_info",
            description="List running processes, optionally filtered by name.",
            input_schema={
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "Filter processes by name"},
                },
                "required": [],
            },
            handler=lambda filter_name=None: process_info(filter_name),
            category="shell",
        ),
        ToolDefinition(
            name="kill_process",
            description="Kill a process by PID.",
            input_schema={
                "type": "object",
                "properties": {
                    "pid": {"type": "integer", "description": "Process ID to kill"},
                },
                "required": ["pid"],
            },
            handler=lambda pid: kill_process(pid),
            category="shell",
            requires_confirm=True,
        ),
    ]
    for tool in tools:
        registry.register(tool)
