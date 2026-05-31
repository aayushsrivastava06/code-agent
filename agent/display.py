"""
Terminal UI using Rich for beautiful output — mimics Claude Code's interface.
"""

import sys
from typing import Optional, Iterator
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.rule import Rule
from rich import box
import time


console = Console(highlight=True)
stderr_console = Console(stderr=True, style="red")


COLORS = {
    "primary":   "#7C3AED",
    "secondary": "#A78BFA",
    "success":   "#10B981",
    "warning":   "#F59E0B",
    "error":     "#EF4444",
    "info":      "#3B82F6",
    "dim":       "#6B7280",
    "text":      "#F9FAFB",
    "tool":      "#06B6D4",
    "user":      "#F472B6",
    "assistant": "#818CF8",
}

BANNER = r"""
 ██████╗ ██████╗ ██████╗ ███████╗     █████╗  ██████╗ ███████╗███╗   ██╗████████╗
██╔════╝██╔═══██╗██╔══██╗██╔════╝    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
██║     ██║   ██║██║  ██║█████╗      ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
██║     ██║   ██║██║  ██║██╔══╝      ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
╚██████╗╚██████╔╝██████╔╝███████╗    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
 ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝  
"""


def print_banner(provider: str, model: str):
    console.print(f"\n[{COLORS['secondary']}]{BANNER}[/]", justify="center")
    console.print(
        Panel(
            f"[{COLORS['success']}]Provider:[/] [{COLORS['text']}]{provider}[/]   "
            f"[{COLORS['success']}]Model:[/] [{COLORS['text']}]{model}[/]   "
            f"[{COLORS['success']}]Version:[/] [{COLORS['text']}]1.0.0[/]",
            border_style=COLORS["primary"],
            padding=(0, 2),
        )
    )
    console.print(
        f"[{COLORS['dim']}]Type your task or command. Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to quit.[/]\n"
    )


def print_help():
    table = Table(
        title="Available Commands",
        box=box.ROUNDED,
        border_style=COLORS["primary"],
        header_style=f"bold {COLORS['secondary']}",
        show_lines=True,
    )
    table.add_column("Command", style=f"bold {COLORS['tool']}", no_wrap=True)
    table.add_column("Description", style=COLORS["text"])

    commands = [
        ("/help", "Show this help message"),
        ("/exit, /quit", "Exit the agent"),
        ("/clear", "Clear the screen and conversation history"),
        ("/reset", "Reset conversation (keep settings)"),
        ("/provider <name>", "Switch AI provider (gemini/groq/openrouter/together/ollama/cohere/mistral)"),
        ("/model <name>", "Switch model for current provider"),
        ("/models", "List available models for current provider"),
        ("/providers", "List all available providers"),
        ("/status", "Show current configuration status"),
        ("/history", "Show conversation history"),
        ("/save <file>", "Save current conversation to file"),
        ("/load <file>", "Load conversation from file"),
        ("/undo", "Undo last file operation"),
        ("/compact", "Compact conversation history (summarize)"),
        ("/cost", "Show estimated token usage"),
        ("/verbose", "Toggle verbose tool output"),
        ("/safe", "Toggle safe mode (ask before bash/write)"),
        ("/cd <path>", "Change working directory"),
        ("/pwd", "Show current working directory"),
        ("/ls [path]", "List directory contents"),
        ("/run <cmd>", "Run a shell command directly"),
        ("/init", "Initialize agent in current project"),
        ("/memory", "Show agent memory/context"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)
    console.print()


def print_user_message(message: str):
    console.print(
        Panel(
            message,
            title=f"[bold {COLORS['user']}] You [/]",
            border_style=COLORS["user"],
            padding=(0, 1),
        )
    )


def print_assistant_prefix():
    console.print(Rule(f"[bold {COLORS['assistant']}] Agent [/]", style=COLORS["assistant"]))


def print_tool_use(tool_name: str, inputs: dict):
    truncated = {}
    for k, v in inputs.items():
        s = str(v)
        truncated[k] = s[:200] + "..." if len(s) > 200 else s

    params_str = ", ".join(f"[{COLORS['text']}]{k}[/]=[{COLORS['warning']}]{repr(v)}[/]" for k, v in truncated.items())
    console.print(
        f"  [{COLORS['tool']}]◆ Tool:[/] [{COLORS['secondary']}]{tool_name}[/]({params_str})"
    )


def print_tool_result(tool_name: str, result: str, success: bool = True):
    color = COLORS["success"] if success else COLORS["error"]
    icon = "✓" if success else "✗"
    lines = result.strip().split("\n")
    preview = "\n".join(lines[:10])
    if len(lines) > 10:
        preview += f"\n[{COLORS['dim']}]... ({len(lines) - 10} more lines)[/]"
    console.print(
        Panel(
            preview or "[dim](no output)[/dim]",
            title=f"[bold {color}]{icon} {tool_name} result[/]",
            border_style=color,
            padding=(0, 1),
            expand=False,
        )
    )


def print_markdown(text: str):
    try:
        md = Markdown(text)
        console.print(md)
    except Exception:
        console.print(text)


def print_code(code: str, language: str = "python", title: str = ""):
    try:
        syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )
        console.print(
            Panel(syntax, title=title or f"[bold]{language}[/]", border_style=COLORS["info"])
        )
    except Exception:
        console.print(code)


def print_error(message: str):
    console.print(f"[bold {COLORS['error']}]✗ Error:[/] [{COLORS['error']}]{message}[/]")


def print_warning(message: str):
    console.print(f"[bold {COLORS['warning']}]⚠ Warning:[/] [{COLORS['warning']}]{message}[/]")


def print_success(message: str):
    console.print(f"[bold {COLORS['success']}]✓[/] [{COLORS['success']}]{message}[/]")


def print_info(message: str):
    console.print(f"[{COLORS['info']}]ℹ {message}[/]")


def print_status_table(config_dict: dict):
    table = Table(
        title="Agent Status",
        box=box.ROUNDED,
        border_style=COLORS["primary"],
        header_style=f"bold {COLORS['secondary']}",
    )
    table.add_column("Setting", style=f"bold {COLORS['tool']}")
    table.add_column("Value", style=COLORS["text"])

    for k, v in config_dict.items():
        val_str = str(v)
        if "key" in k.lower() and v:
            val_str = val_str[:8] + "..." + val_str[-4:] if len(val_str) > 12 else "****"
        table.add_row(k, val_str)

    console.print(table)


def spinner(message: str):
    return Progress(
        SpinnerColumn(style=COLORS["primary"]),
        TextColumn(f"[{COLORS['secondary']}]{message}[/]"),
        transient=True,
    )


def prompt_user(prompt_text: str = "") -> str:
    try:
        return Prompt.ask(
            f"\n[bold {COLORS['primary']}]❯[/] [{COLORS['user']}]{prompt_text or 'You'}[/]"
        )
    except (KeyboardInterrupt, EOFError):
        return "/exit"


def confirm(message: str, default: bool = False) -> bool:
    try:
        return Confirm.ask(f"[{COLORS['warning']}]{message}[/]", default=default)
    except (KeyboardInterrupt, EOFError):
        return False


def print_diff(old_content: str, new_content: str, filename: str = "file"):
    import difflib
    diff = list(difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    ))
    if diff:
        diff_text = "".join(diff)
        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, title=f"[bold]Diff: {filename}[/]", border_style=COLORS["info"]))
    else:
        print_info("No changes detected.")


def stream_text(text: str, delay: float = 0.01):
    for char in text:
        console.print(char, end="")
        time.sleep(delay)
    console.print()


def print_thinking(message: str = "Thinking..."):
    console.print(f"[{COLORS['dim']}]⟳ {message}[/]")


def clear_screen():
    console.clear()


def print_separator():
    console.print(Rule(style=COLORS["dim"]))


def print_compact_tool(tool_name: str, summary: str):
    console.print(f"  [{COLORS['tool']}]▸ {tool_name}[/] [{COLORS['dim']}]{summary}[/]")
