"""
File system tools — read, write, edit, delete, move, copy, list, info.
These are the core tools the agent uses to interact with the codebase.
"""

import os
import shutil
import stat
import time
from pathlib import Path
from typing import Optional

from .registry import registry, ToolDefinition


def _resolve(path: str, workspace: str = ".") -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = Path(workspace) / p
    return p.resolve()


def read_file(path: str, start_line: int = 1, end_line: Optional[int] = None,
              workspace: str = ".") -> str:
    try:
        full_path = _resolve(path, workspace)
        if not full_path.exists():
            return f"Error: File not found: {path}"
        if not full_path.is_file():
            return f"Error: Path is not a file: {path}"
        size_kb = full_path.stat().st_size / 1024
        if size_kb > 2048:
            return f"Error: File too large ({size_kb:.0f}KB). Use search_files to find specific content."
        content = full_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines(keepends=True)
        total = len(lines)
        s = max(1, start_line) - 1
        e = end_line if end_line else total
        selected = lines[s:e]
        numbered = []
        for i, line in enumerate(selected, start=s + 1):
            numbered.append(f"{i:6d}\t{line.rstrip()}")
        header = f"File: {path} ({total} lines total"
        if start_line > 1 or (end_line and end_line < total):
            header += f", showing lines {s+1}-{min(e, total)}"
        header += ")"
        return header + "\n" + "\n".join(numbered)
    except Exception as e:
        return f"Error reading {path}: {e}"


def write_file(path: str, content: str, workspace: str = ".") -> str:
    try:
        full_path = _resolve(path, workspace)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        existed = full_path.exists()
        old_content = full_path.read_text(encoding="utf-8", errors="replace") if existed else ""
        full_path.write_text(content, encoding="utf-8")
        lines = len(content.splitlines())
        action = "Updated" if existed else "Created"
        return f"{action} {path} ({lines} lines, {len(content)} bytes)"
    except Exception as e:
        return f"Error writing {path}: {e}"


def edit_file(path: str, old_string: str, new_string: str, workspace: str = ".") -> str:
    try:
        full_path = _resolve(path, workspace)
        if not full_path.exists():
            return f"Error: File not found: {path}"
        content = full_path.read_text(encoding="utf-8", errors="replace")
        if old_string not in content:
            lines_with_partial = []
            for i, line in enumerate(content.splitlines(), 1):
                if old_string[:30] in line:
                    lines_with_partial.append(f"  Line {i}: {line.strip()}")
            hint = ""
            if lines_with_partial:
                hint = "\nPartial matches found:\n" + "\n".join(lines_with_partial[:5])
            return f"Error: Could not find the specified string to replace in {path}.{hint}"
        count = content.count(old_string)
        if count > 1:
            new_content = content.replace(old_string, new_string, 1)
            full_path.write_text(new_content, encoding="utf-8")
            return f"Replaced first occurrence of string in {path} ({count} total occurrences found — use search_replace to replace all)"
        new_content = content.replace(old_string, new_string)
        full_path.write_text(new_content, encoding="utf-8")
        old_lines = len(old_string.splitlines())
        new_lines = len(new_string.splitlines())
        return f"Successfully edited {path} ({old_lines} lines → {new_lines} lines)"
    except Exception as e:
        return f"Error editing {path}: {e}"


def append_file(path: str, content: str, workspace: str = ".") -> str:
    try:
        full_path = _resolve(path, workspace)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error appending to {path}: {e}"


def delete_file(path: str, workspace: str = ".") -> str:
    try:
        full_path = _resolve(path, workspace)
        if not full_path.exists():
            return f"Error: Path not found: {path}"
        if full_path.is_dir():
            shutil.rmtree(full_path)
            return f"Deleted directory: {path}"
        else:
            full_path.unlink()
            return f"Deleted file: {path}"
    except Exception as e:
        return f"Error deleting {path}: {e}"


def copy_file(source: str, destination: str, workspace: str = ".") -> str:
    try:
        src = _resolve(source, workspace)
        dst = _resolve(destination, workspace)
        if not src.exists():
            return f"Error: Source not found: {source}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        return f"Copied {source} → {destination}"
    except Exception as e:
        return f"Error copying: {e}"


def move_file(source: str, destination: str, workspace: str = ".") -> str:
    try:
        src = _resolve(source, workspace)
        dst = _resolve(destination, workspace)
        if not src.exists():
            return f"Error: Source not found: {source}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return f"Moved {source} → {destination}"
    except Exception as e:
        return f"Error moving: {e}"


def list_directory(path: str = ".", show_hidden: bool = False, workspace: str = ".") -> str:
    try:
        full_path = _resolve(path, workspace)
        if not full_path.exists():
            return f"Error: Path not found: {path}"
        if not full_path.is_dir():
            return f"Error: Not a directory: {path}"
        entries = sorted(full_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        lines = [f"Directory: {full_path}\n"]
        for entry in entries:
            if not show_hidden and entry.name.startswith("."):
                continue
            try:
                stat_info = entry.stat()
                size = stat_info.st_size
                mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat_info.st_mtime))
                if entry.is_dir():
                    icon = "📁"
                    size_str = "<dir>"
                else:
                    icon = "📄"
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size/1024:.1f}KB"
                    else:
                        size_str = f"{size/1024/1024:.1f}MB"
                lines.append(f"  {icon} {entry.name:<40} {size_str:>8}  {mtime}")
            except PermissionError:
                lines.append(f"  ⛔ {entry.name} (permission denied)")
        lines.append(f"\n{len(entries)} items")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing {path}: {e}"


def make_directory(path: str, workspace: str = ".") -> str:
    try:
        full_path = _resolve(path, workspace)
        full_path.mkdir(parents=True, exist_ok=True)
        return f"Created directory: {path}"
    except Exception as e:
        return f"Error creating directory {path}: {e}"


def file_info(path: str, workspace: str = ".") -> str:
    try:
        full_path = _resolve(path, workspace)
        if not full_path.exists():
            return f"Error: Path not found: {path}"
        s = full_path.stat()
        info = {
            "path": str(full_path),
            "type": "directory" if full_path.is_dir() else "file",
            "size": f"{s.st_size} bytes ({s.st_size/1024:.1f} KB)",
            "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s.st_ctime)),
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s.st_mtime)),
            "permissions": oct(stat.S_IMODE(s.st_mode)),
        }
        if full_path.is_file():
            try:
                text = full_path.read_text(encoding="utf-8", errors="replace")
                info["lines"] = str(len(text.splitlines()))
                info["encoding"] = "utf-8"
                ext = full_path.suffix.lower()
                lang_map = {
                    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                    ".jsx": "React JSX", ".tsx": "React TSX", ".html": "HTML",
                    ".css": "CSS", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
                    ".md": "Markdown", ".sh": "Shell", ".rs": "Rust", ".go": "Go",
                    ".java": "Java", ".cpp": "C++", ".c": "C", ".rb": "Ruby",
                }
                info["language"] = lang_map.get(ext, ext.lstrip(".").upper() or "Unknown")
            except Exception:
                info["encoding"] = "binary"
        return "\n".join(f"  {k}: {v}" for k, v in info.items())
    except Exception as e:
        return f"Error getting info for {path}: {e}"


def diff_files(path1: str, path2: str, workspace: str = ".") -> str:
    import difflib
    try:
        f1 = _resolve(path1, workspace)
        f2 = _resolve(path2, workspace)
        c1 = f1.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        c2 = f2.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        diff = list(difflib.unified_diff(c1, c2, fromfile=path1, tofile=path2))
        if not diff:
            return "Files are identical."
        return "".join(diff)
    except Exception as e:
        return f"Error comparing files: {e}"


def register_file_tools(workspace_getter):
    def ws():
        return workspace_getter()

    tools = [
        ToolDefinition(
            name="read_file",
            description="Read the contents of a file. Optionally specify line range with start_line and end_line.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"},
                    "start_line": {"type": "integer", "description": "Starting line number (1-indexed)", "default": 1},
                    "end_line": {"type": "integer", "description": "Ending line number (inclusive). Omit to read to end."},
                },
                "required": ["path"],
            },
            handler=lambda path, start_line=1, end_line=None: read_file(path, start_line, end_line, ws()),
            category="files",
        ),
        ToolDefinition(
            name="write_file",
            description="Create or completely overwrite a file with new content. Creates parent directories as needed.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Full file content"},
                },
                "required": ["path", "content"],
            },
            handler=lambda path, content: write_file(path, content, ws()),
            category="files",
            requires_confirm=False,
        ),
        ToolDefinition(
            name="edit_file",
            description=(
                "Make a targeted edit to an existing file by replacing old_string with new_string. "
                "The old_string must exactly match content in the file (including whitespace/indentation). "
                "Preferred over write_file for modifications."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_string": {"type": "string", "description": "Exact string to find and replace"},
                    "new_string": {"type": "string", "description": "Replacement string"},
                },
                "required": ["path", "old_string", "new_string"],
            },
            handler=lambda path, old_string, new_string: edit_file(path, old_string, new_string, ws()),
            category="files",
        ),
        ToolDefinition(
            name="append_file",
            description="Append content to the end of an existing file.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content to append"},
                },
                "required": ["path", "content"],
            },
            handler=lambda path, content: append_file(path, content, ws()),
            category="files",
        ),
        ToolDefinition(
            name="delete_file",
            description="Delete a file or directory.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to delete"},
                },
                "required": ["path"],
            },
            handler=lambda path: delete_file(path, ws()),
            category="files",
            requires_confirm=True,
        ),
        ToolDefinition(
            name="copy_file",
            description="Copy a file or directory to a new location.",
            input_schema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path"},
                    "destination": {"type": "string", "description": "Destination path"},
                },
                "required": ["source", "destination"],
            },
            handler=lambda source, destination: copy_file(source, destination, ws()),
            category="files",
        ),
        ToolDefinition(
            name="move_file",
            description="Move or rename a file or directory.",
            input_schema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path"},
                    "destination": {"type": "string", "description": "Destination path"},
                },
                "required": ["source", "destination"],
            },
            handler=lambda source, destination: move_file(source, destination, ws()),
            category="files",
        ),
        ToolDefinition(
            name="list_directory",
            description="List the contents of a directory with file sizes and modification times.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path (default: current)", "default": "."},
                    "show_hidden": {"type": "boolean", "description": "Include hidden files/dirs", "default": False},
                },
                "required": [],
            },
            handler=lambda path=".", show_hidden=False: list_directory(path, show_hidden, ws()),
            category="files",
        ),
        ToolDefinition(
            name="make_directory",
            description="Create a directory (and parent directories) if it doesn't exist.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to create"},
                },
                "required": ["path"],
            },
            handler=lambda path: make_directory(path, ws()),
            category="files",
        ),
        ToolDefinition(
            name="file_info",
            description="Get metadata about a file or directory: size, type, modification time, line count, language.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File or directory path"},
                },
                "required": ["path"],
            },
            handler=lambda path: file_info(path, ws()),
            category="files",
        ),
        ToolDefinition(
            name="diff_files",
            description="Show the unified diff between two files.",
            input_schema={
                "type": "object",
                "properties": {
                    "path1": {"type": "string", "description": "First file path"},
                    "path2": {"type": "string", "description": "Second file path"},
                },
                "required": ["path1", "path2"],
            },
            handler=lambda path1, path2: diff_files(path1, path2, ws()),
            category="files",
        ),
    ]
    for tool in tools:
        registry.register(tool)
