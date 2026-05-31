"""
Code search tools — grep, find files, symbol search, references, todos.
Uses ripgrep if available, falls back to Python implementations.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Optional, List

from .registry import registry, ToolDefinition
from .bash_tool import run_command


def _has_ripgrep() -> bool:
    return shutil.which("rg") is not None


def search_files(
    pattern: str,
    path: str = ".",
    file_pattern: str = "",
    case_sensitive: bool = True,
    include_context: int = 2,
    max_results: int = 100,
    workspace: str = ".",
) -> str:
    try:
        base = Path(workspace) / path if not Path(path).is_absolute() else Path(path)

        if _has_ripgrep():
            cmd_parts = ["rg", "--line-number", "--no-heading", "--color=never"]
            if not case_sensitive:
                cmd_parts.append("-i")
            if include_context > 0:
                cmd_parts.extend(["-C", str(include_context)])
            if file_pattern:
                cmd_parts.extend(["-g", file_pattern])
            cmd_parts.extend(["-m", str(max_results)])
            cmd_parts.append(f'"{pattern}"')
            cmd_parts.append(str(base))
            result = run_command(" ".join(cmd_parts), timeout=15)
            return result

        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"Invalid regex pattern: {e}"

        results = []
        found = 0
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {
                "node_modules", "__pycache__", ".git", "dist", "build", ".venv", "venv"
            }]
            for fname in files:
                if file_pattern:
                    import fnmatch
                    if not fnmatch.fnmatch(fname, file_pattern):
                        continue
                fpath = Path(root) / fname
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    for i, line in enumerate(lines, 1):
                        if regex.search(line):
                            rel = fpath.relative_to(workspace)
                            ctx_start = max(0, i - 1 - include_context)
                            ctx_end = min(len(lines), i + include_context)
                            for j in range(ctx_start, ctx_end):
                                marker = ">" if j == i - 1 else " "
                                results.append(f"{rel}:{j+1}:{marker} {lines[j]}")
                            results.append("")
                            found += 1
                            if found >= max_results:
                                results.append(f"[Stopped at {max_results} results]")
                                return "\n".join(results)
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue

        if not results:
            return f"No matches found for '{pattern}' in {path}"
        return "\n".join(results)
    except Exception as e:
        return f"Error searching: {e}"


def find_files(
    name_pattern: str,
    path: str = ".",
    file_type: str = "any",
    max_results: int = 50,
    workspace: str = ".",
) -> str:
    try:
        import fnmatch
        base = Path(workspace) / path if not Path(path).is_absolute() else Path(path)
        results = []

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in {
                "node_modules", "__pycache__", ".git", "dist", "build", ".venv", "venv", ".tox"
            }]

            candidates = []
            if file_type in ("any", "dir"):
                candidates.extend([(d, True) for d in dirs])
            if file_type in ("any", "file"):
                candidates.extend([(f, False) for f in files])

            for name, is_dir in candidates:
                if fnmatch.fnmatch(name.lower(), name_pattern.lower()):
                    full = Path(root) / name
                    try:
                        rel = full.relative_to(workspace)
                        icon = "📁" if is_dir else "📄"
                        results.append(f"{icon} {rel}")
                    except ValueError:
                        results.append(f"{'📁' if is_dir else '📄'} {full}")
                    if len(results) >= max_results:
                        results.append(f"[Stopped at {max_results} results]")
                        return "\n".join(results)

        if not results:
            return f"No files matching '{name_pattern}' found in {path}"
        return f"Found {len(results)} matches:\n" + "\n".join(results)
    except Exception as e:
        return f"Error finding files: {e}"


def search_replace(
    pattern: str,
    replacement: str,
    path: str = ".",
    file_pattern: str = "*.py",
    dry_run: bool = True,
    workspace: str = ".",
) -> str:
    try:
        import fnmatch
        base = Path(workspace) / path if not Path(path).is_absolute() else Path(path)
        changed_files = []
        total_replacements = 0

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"Invalid regex: {e}"

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in {
                "node_modules", "__pycache__", ".git", "dist", "build", ".venv"
            }]
            for fname in files:
                if not fnmatch.fnmatch(fname, file_pattern):
                    continue
                fpath = Path(root) / fname
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    new_content, n = regex.subn(replacement, content)
                    if n > 0:
                        rel = fpath.relative_to(workspace)
                        changed_files.append(f"  {rel} ({n} replacement{'s' if n > 1 else ''})")
                        total_replacements += n
                        if not dry_run:
                            fpath.write_text(new_content, encoding="utf-8")
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue

        if not changed_files:
            return f"No matches for '{pattern}' in {file_pattern} files under {path}"

        mode = "DRY RUN — no changes made" if dry_run else "APPLIED"
        return (
            f"Search/Replace [{mode}]\n"
            f"Pattern: {pattern}\n"
            f"Replacement: {replacement}\n"
            f"Files affected: {len(changed_files)}\n"
            f"Total replacements: {total_replacements}\n\n"
            + "\n".join(changed_files)
            + ("\n\nRe-run with dry_run=false to apply changes." if dry_run else "")
        )
    except Exception as e:
        return f"Error in search_replace: {e}"


def get_symbols(path: str, workspace: str = ".") -> str:
    try:
        full = Path(workspace) / path if not Path(path).is_absolute() else Path(path)
        if not full.exists():
            return f"File not found: {path}"
        content = full.read_text(encoding="utf-8", errors="replace")
        ext = full.suffix.lower()

        symbols = []
        if ext == ".py":
            patterns = [
                (r"^(class\s+\w+[^:]*):?", "class"),
                (r"^(\s*def\s+\w+\s*\([^)]*\))", "function"),
                (r"^(\w+)\s*=\s*", "variable"),
            ]
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            patterns = [
                (r"^(class\s+\w+)", "class"),
                (r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", "function"),
                (r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(", "arrow_function"),
                (r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=", "variable"),
                (r"^(?:export\s+)?interface\s+(\w+)", "interface"),
                (r"^(?:export\s+)?type\s+(\w+)\s*=", "type"),
            ]
        elif ext in (".go",):
            patterns = [
                (r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", "function"),
                (r"^type\s+(\w+)\s+struct", "struct"),
                (r"^type\s+(\w+)\s+interface", "interface"),
            ]
        else:
            patterns = [
                (r"^\s*(?:public|private|protected)?\s*(?:static)?\s*(?:class|interface|enum)\s+(\w+)", "class"),
                (r"^\s*(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(", "method"),
            ]

        for i, line in enumerate(content.splitlines(), 1):
            for pat, kind in patterns:
                m = re.match(pat, line.strip() if kind in ("class",) else line)
                if m:
                    name = m.group(1).strip()
                    symbols.append(f"  Line {i:4d}: [{kind}] {name}")
                    break

        if not symbols:
            return f"No symbols found in {path} (language: {ext})"
        return f"Symbols in {path} ({len(symbols)} found):\n" + "\n".join(symbols)
    except Exception as e:
        return f"Error getting symbols: {e}"


def find_todos(path: str = ".", workspace: str = ".") -> str:
    try:
        base = Path(workspace) / path if not Path(path).is_absolute() else Path(path)
        TODO_PATTERN = re.compile(
            r"#|//|/\*|\*|<!--|\"\"\"|\'\'\'"
            r".*?\b(TODO|FIXME|HACK|XXX|BUG|NOTE|OPTIMIZE|REFACTOR)\b[:\s]*(.*)",
            re.IGNORECASE,
        )
        results = []
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in {
                "node_modules", "__pycache__", ".git", "dist", "build", ".venv"
            }]
            for fname in files:
                if not any(fname.endswith(ext) for ext in [
                    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".cpp",
                    ".h", ".rb", ".php", ".cs", ".swift", ".kt", ".sh", ".md",
                ]):
                    continue
                fpath = Path(root) / fname
                try:
                    for i, line in enumerate(fpath.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                        m = re.search(r"\b(TODO|FIXME|HACK|XXX|BUG|NOTE|OPTIMIZE|REFACTOR)\b[:\s]*(.*)", line, re.I)
                        if m:
                            rel = fpath.relative_to(workspace)
                            tag = m.group(1).upper()
                            comment = m.group(2).strip()[:80]
                            results.append(f"  [{tag}] {rel}:{i} — {comment}")
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue

        if not results:
            return "No TODOs/FIXMEs found."
        return f"Found {len(results)} items:\n" + "\n".join(results)
    except Exception as e:
        return f"Error finding todos: {e}"


def analyze_code(path: str, workspace: str = ".") -> str:
    try:
        full = Path(workspace) / path if not Path(path).is_absolute() else Path(path)
        if not full.exists():
            return f"File not found: {path}"

        content = full.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        total_lines = len(lines)
        blank_lines = sum(1 for l in lines if not l.strip())
        comment_lines = sum(1 for l in lines if l.strip().startswith(("#", "//", "*", "/*", "<!--")))
        code_lines = total_lines - blank_lines - comment_lines
        avg_len = sum(len(l) for l in lines) / max(total_lines, 1)
        long_lines = sum(1 for l in lines if len(l) > 120)

        functions = len(re.findall(r"\bdef\s+\w+|function\s+\w+|\bfunc\s+\w+", content))
        classes = len(re.findall(r"\bclass\s+\w+", content))
        imports = len(re.findall(r"^\s*(?:import|from|require|use|include)\s+", content, re.M))
        todos = len(re.findall(r"\b(TODO|FIXME|HACK|XXX)\b", content, re.I))
        complexity = max(1, len(re.findall(r"\b(if|elif|else|for|while|try|except|catch|switch|case|&&|\|\|)\b", content)))

        grade = "A" if complexity < 10 else "B" if complexity < 20 else "C" if complexity < 40 else "D"

        return (
            f"Code Analysis: {path}\n"
            f"{'='*40}\n"
            f"Lines:          {total_lines} total, {code_lines} code, {blank_lines} blank, {comment_lines} comments\n"
            f"Avg line length: {avg_len:.1f} chars | Long lines (>120): {long_lines}\n"
            f"Functions:      {functions}\n"
            f"Classes:        {classes}\n"
            f"Imports:        {imports}\n"
            f"TODOs/FIXMEs:   {todos}\n"
            f"Complexity est: {complexity} (grade: {grade})\n"
        )
    except Exception as e:
        return f"Error analyzing {path}: {e}"


def register_search_tools(workspace_getter):
    def ws():
        return workspace_getter()

    tools = [
        ToolDefinition(
            name="search_files",
            description=(
                "Search for a pattern (regex or literal) in files. "
                "Uses ripgrep if available for speed. "
                "Returns matching lines with context."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex or literal string to search for"},
                    "path": {"type": "string", "description": "Directory or file to search in", "default": "."},
                    "file_pattern": {"type": "string", "description": "Glob for file types (e.g. '*.py', '*.ts')", "default": ""},
                    "case_sensitive": {"type": "boolean", "description": "Case-sensitive search", "default": True},
                    "include_context": {"type": "integer", "description": "Lines of context around match", "default": 2},
                    "max_results": {"type": "integer", "description": "Max number of results", "default": 100},
                },
                "required": ["pattern"],
            },
            handler=lambda pattern, path=".", file_pattern="", case_sensitive=True, include_context=2, max_results=100: search_files(
                pattern, path, file_pattern, case_sensitive, include_context, max_results, ws()
            ),
            category="search",
        ),
        ToolDefinition(
            name="find_files",
            description="Find files or directories by name pattern (glob). Like Unix 'find'.",
            input_schema={
                "type": "object",
                "properties": {
                    "name_pattern": {"type": "string", "description": "Glob pattern (e.g. '*.py', 'test_*', 'config.*')"},
                    "path": {"type": "string", "description": "Directory to search in", "default": "."},
                    "file_type": {"type": "string", "enum": ["any", "file", "dir"], "description": "Filter by type", "default": "any"},
                    "max_results": {"type": "integer", "description": "Max results to return", "default": 50},
                },
                "required": ["name_pattern"],
            },
            handler=lambda name_pattern, path=".", file_type="any", max_results=50: find_files(
                name_pattern, path, file_type, max_results, ws()
            ),
            category="search",
        ),
        ToolDefinition(
            name="search_replace",
            description=(
                "Find and replace a regex pattern across multiple files. "
                "Run with dry_run=true first to preview changes, then dry_run=false to apply."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to find"},
                    "replacement": {"type": "string", "description": "Replacement string (supports regex groups like \\1)"},
                    "path": {"type": "string", "description": "Directory to search", "default": "."},
                    "file_pattern": {"type": "string", "description": "File glob filter", "default": "*.py"},
                    "dry_run": {"type": "boolean", "description": "Preview without applying changes", "default": True},
                },
                "required": ["pattern", "replacement"],
            },
            handler=lambda pattern, replacement, path=".", file_pattern="*.py", dry_run=True: search_replace(
                pattern, replacement, path, file_pattern, dry_run, ws()
            ),
            category="search",
        ),
        ToolDefinition(
            name="get_symbols",
            description="Extract functions, classes, interfaces, and variables from a source file.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Source file path"},
                },
                "required": ["path"],
            },
            handler=lambda path: get_symbols(path, ws()),
            category="search",
        ),
        ToolDefinition(
            name="find_todos",
            description="Find all TODO, FIXME, HACK, XXX, BUG comments in the codebase.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory to search", "default": "."},
                },
                "required": [],
            },
            handler=lambda path=".": find_todos(path, ws()),
            category="search",
        ),
        ToolDefinition(
            name="analyze_code",
            description="Analyze a source file for metrics: lines, complexity, functions, classes, imports.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Source file to analyze"},
                },
                "required": ["path"],
            },
            handler=lambda path: analyze_code(path, ws()),
            category="search",
        ),
    ]
    for tool in tools:
        registry.register(tool)
