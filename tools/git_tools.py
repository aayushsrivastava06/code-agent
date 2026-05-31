"""
Git tools — status, log, diff, blame, commit, branch, stash.
All operations via subprocess calling git directly.
"""

from typing import Optional
from .registry import registry, ToolDefinition
from .bash_tool import run_command


def git_status(workspace: str = ".") -> str:
    return run_command("git status --short --branch", timeout=10, workspace=workspace)


def git_log(n: int = 15, oneline: bool = False, author: str = "", workspace: str = ".") -> str:
    fmt = "--oneline" if oneline else "--format='%h  %ad  %an  %s' --date=short"
    author_flag = f"--author='{author}'" if author else ""
    return run_command(f"git log {fmt} -{n} {author_flag}", timeout=10, workspace=workspace)


def git_diff(staged: bool = False, file_path: str = "", commit: str = "", workspace: str = ".") -> str:
    flags = "--cached" if staged else ""
    target = commit or file_path
    return run_command(f"git diff {flags} {target}".strip(), timeout=10, workspace=workspace)


def git_blame(path: str, workspace: str = ".") -> str:
    return run_command(f"git blame -n '{path}'", timeout=10, workspace=workspace)


def git_commit(message: str, add_all: bool = True, workspace: str = ".") -> str:
    cmds = []
    if add_all:
        cmds.append("git add -A")
    cmds.append(f'git commit -m "{message}"')
    return run_command(" && ".join(cmds), timeout=15, workspace=workspace)


def git_branch(action: str = "list", branch_name: str = "", workspace: str = ".") -> str:
    if action == "list":
        return run_command("git branch -a", timeout=5, workspace=workspace)
    elif action == "create":
        return run_command(f"git checkout -b '{branch_name}'", timeout=5, workspace=workspace)
    elif action == "switch":
        return run_command(f"git checkout '{branch_name}'", timeout=5, workspace=workspace)
    elif action == "delete":
        return run_command(f"git branch -d '{branch_name}'", timeout=5, workspace=workspace)
    elif action == "merge":
        return run_command(f"git merge '{branch_name}'", timeout=10, workspace=workspace)
    return f"Unknown branch action: {action}"


def git_stash(action: str = "save", message: str = "", workspace: str = ".") -> str:
    if action == "save":
        msg = f'"{message}"' if message else ""
        return run_command(f"git stash push -m {msg}", timeout=5, workspace=workspace)
    elif action == "pop":
        return run_command("git stash pop", timeout=5, workspace=workspace)
    elif action == "list":
        return run_command("git stash list", timeout=5, workspace=workspace)
    elif action == "drop":
        return run_command("git stash drop", timeout=5, workspace=workspace)
    return f"Unknown stash action: {action}"


def git_push(remote: str = "origin", branch: str = "", workspace: str = ".") -> str:
    return run_command(f"git push {remote} {branch}".strip(), timeout=30, workspace=workspace)


def git_pull(remote: str = "origin", branch: str = "", workspace: str = ".") -> str:
    return run_command(f"git pull {remote} {branch}".strip(), timeout=30, workspace=workspace)


def git_reset(mode: str = "soft", commit: str = "HEAD~1", workspace: str = ".") -> str:
    return run_command(f"git reset --{mode} {commit}", timeout=5, workspace=workspace)


def git_show(commit: str = "HEAD", workspace: str = ".") -> str:
    return run_command(f"git show --stat {commit}", timeout=5, workspace=workspace)


def detect_project(workspace: str = ".") -> str:
    import os
    from pathlib import Path

    base = Path(workspace)
    findings = []
    markers = {
        "Python/Django": ["manage.py"],
        "Python/Flask": ["app.py", "wsgi.py", "application.py"],
        "Python": ["setup.py", "pyproject.toml", "requirements.txt", "poetry.lock"],
        "Node.js/Next.js": ["next.config.js", "next.config.ts"],
        "Node.js/React": ["vite.config.js", "vite.config.ts", "react-scripts"],
        "Node.js": ["package.json"],
        "Go": ["go.mod"],
        "Rust": ["Cargo.toml"],
        "Java/Maven": ["pom.xml"],
        "Java/Gradle": ["build.gradle"],
        "Ruby on Rails": ["Gemfile", "config/routes.rb"],
        "PHP/Laravel": ["artisan"],
        "Docker": ["Dockerfile", "docker-compose.yml"],
        "Kubernetes": ["k8s/", "kubernetes/"],
        "Terraform": ["main.tf"],
    }

    for name, files in markers.items():
        for f in files:
            if (base / f).exists():
                findings.append(name)
                break

    if not findings:
        findings.append("Unknown project type")

    languages = []
    ext_counts: dict = {}
    try:
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in {
                "node_modules", "__pycache__", ".git", "dist", "build", ".venv", "venv"
            }]
            for f in files:
                ext = Path(f).suffix.lower()
                if ext:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
    except Exception:
        pass

    lang_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
        ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".c": "C",
        ".swift": "Swift", ".kt": "Kotlin", ".dart": "Dart",
    }
    top_exts = sorted(ext_counts.items(), key=lambda x: -x[1])[:5]
    for ext, count in top_exts:
        lang = lang_map.get(ext)
        if lang:
            languages.append(f"{lang} ({count} files)")

    git_info = run_command("git remote -v 2>&1 | head -2", timeout=5, workspace=workspace)
    branch = run_command("git branch --show-current 2>&1", timeout=5, workspace=workspace).strip()

    return (
        f"Project Analysis: {workspace}\n"
        f"{'='*40}\n"
        f"Frameworks/Types: {', '.join(findings)}\n"
        f"Top languages: {', '.join(languages) or 'unknown'}\n"
        f"Git branch: {branch or 'not a git repo'}\n"
        f"Git remotes:\n{git_info.strip()}\n"
    )


def get_dependencies(workspace: str = ".") -> str:
    from pathlib import Path
    import json
    base = Path(workspace)
    output = []

    pkg_json = base / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            deps = data.get("dependencies", {})
            dev_deps = data.get("devDependencies", {})
            output.append(f"Node.js ({data.get('name', 'unknown')} v{data.get('version', '?')})")
            output.append(f"  Dependencies ({len(deps)}): " + ", ".join(list(deps.keys())[:20]))
            output.append(f"  DevDependencies ({len(dev_deps)}): " + ", ".join(list(dev_deps.keys())[:20]))
            scripts = data.get("scripts", {})
            if scripts:
                output.append(f"  Scripts: " + ", ".join(scripts.keys()))
        except Exception as e:
            output.append(f"package.json parse error: {e}")

    for req_file in ["requirements.txt", "Pipfile", "pyproject.toml"]:
        p = base / req_file
        if p.exists():
            content = p.read_text()[:2000]
            output.append(f"\nPython ({req_file}):\n{content}")
            break

    for go_file in ["go.mod"]:
        p = base / go_file
        if p.exists():
            output.append(f"\nGo (go.mod):\n{p.read_text()[:1000]}")

    for cargo_file in ["Cargo.toml"]:
        p = base / cargo_file
        if p.exists():
            output.append(f"\nRust (Cargo.toml):\n{p.read_text()[:1000]}")

    return "\n".join(output) if output else "No dependency files found."


def run_tests(test_command: str = "", workspace: str = ".") -> str:
    if not test_command:
        from pathlib import Path
        base = Path(workspace)
        if (base / "pytest.ini").exists() or (base / "pyproject.toml").exists():
            test_command = "python -m pytest -v"
        elif (base / "package.json").exists():
            import json
            pkg = json.loads((base / "package.json").read_text())
            if "test" in pkg.get("scripts", {}):
                test_command = "npm test"
            else:
                test_command = "npx jest"
        elif (base / "Cargo.toml").exists():
            test_command = "cargo test"
        elif (base / "go.mod").exists():
            test_command = "go test ./..."
        else:
            return "Cannot detect test runner. Please provide test_command."

    return run_command(test_command, timeout=120, workspace=workspace)


def lint_code(path: str = ".", workspace: str = ".") -> str:
    from pathlib import Path
    base = Path(workspace)
    results = []

    if (base / "pyproject.toml").exists() or (base / ".flake8").exists():
        r = run_command(f"python -m flake8 {path} 2>&1 | head -50", timeout=15, workspace=workspace)
        results.append(f"flake8:\n{r}")
    elif Path(path).suffix == ".py":
        r = run_command(f"python -m py_compile {path} && echo 'Syntax OK'", timeout=5, workspace=workspace)
        results.append(f"Python syntax check:\n{r}")

    if (base / ".eslintrc.js").exists() or (base / ".eslintrc.json").exists():
        r = run_command(f"npx eslint {path} 2>&1 | head -50", timeout=15, workspace=workspace)
        results.append(f"ESLint:\n{r}")

    return "\n\n".join(results) if results else "No linter configured. Install flake8 (Python) or eslint (JS/TS)."


def format_code(path: str, workspace: str = ".") -> str:
    from pathlib import Path
    ext = Path(path).suffix.lower()
    formatters = {
        ".py": f"python -m black {path}",
        ".js": f"npx prettier --write {path}",
        ".ts": f"npx prettier --write {path}",
        ".tsx": f"npx prettier --write {path}",
        ".jsx": f"npx prettier --write {path}",
        ".json": f"npx prettier --write {path}",
        ".md": f"npx prettier --write {path}",
        ".go": f"gofmt -w {path}",
        ".rs": f"rustfmt {path}",
    }
    cmd = formatters.get(ext, f"npx prettier --write {path}")
    return run_command(cmd, timeout=15, workspace=workspace)


def register_git_tools(workspace_getter):
    def ws():
        return workspace_getter()

    tools = [
        ToolDefinition(
            name="git_status",
            description="Get the current git status showing modified, staged, and untracked files.",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=lambda: git_status(ws()),
            category="git",
        ),
        ToolDefinition(
            name="git_log",
            description="Get git commit history.",
            input_schema={
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "description": "Number of commits to show", "default": 15},
                    "oneline": {"type": "boolean", "description": "One line per commit", "default": False},
                    "author": {"type": "string", "description": "Filter by author name"},
                },
                "required": [],
            },
            handler=lambda n=15, oneline=False, author="": git_log(n, oneline, author, ws()),
            category="git",
        ),
        ToolDefinition(
            name="git_diff",
            description="Show git diff. Can show staged changes, unstaged changes, or diff of a specific file/commit.",
            input_schema={
                "type": "object",
                "properties": {
                    "staged": {"type": "boolean", "description": "Show staged (cached) changes", "default": False},
                    "file_path": {"type": "string", "description": "Specific file to diff"},
                    "commit": {"type": "string", "description": "Commit hash or range (e.g. 'HEAD~1')"},
                },
                "required": [],
            },
            handler=lambda staged=False, file_path="", commit="": git_diff(staged, file_path, commit, ws()),
            category="git",
        ),
        ToolDefinition(
            name="git_blame",
            description="Show who last modified each line of a file (git blame).",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
            handler=lambda path: git_blame(path, ws()),
            category="git",
        ),
        ToolDefinition(
            name="git_commit",
            description="Stage all changes and create a git commit.",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                    "add_all": {"type": "boolean", "description": "Stage all changes before committing", "default": True},
                },
                "required": ["message"],
            },
            handler=lambda message, add_all=True: git_commit(message, add_all, ws()),
            category="git",
        ),
        ToolDefinition(
            name="git_branch",
            description="List, create, switch, delete, or merge git branches.",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "create", "switch", "delete", "merge"], "default": "list"},
                    "branch_name": {"type": "string", "description": "Branch name (for create/switch/delete/merge)"},
                },
                "required": [],
            },
            handler=lambda action="list", branch_name="": git_branch(action, branch_name, ws()),
            category="git",
        ),
        ToolDefinition(
            name="git_stash",
            description="Stash, pop, list, or drop git stashes.",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["save", "pop", "list", "drop"], "default": "save"},
                    "message": {"type": "string", "description": "Stash message"},
                },
                "required": [],
            },
            handler=lambda action="save", message="": git_stash(action, message, ws()),
            category="git",
        ),
        ToolDefinition(
            name="git_push",
            description="Push commits to a remote repository.",
            input_schema={
                "type": "object",
                "properties": {
                    "remote": {"type": "string", "description": "Remote name", "default": "origin"},
                    "branch": {"type": "string", "description": "Branch name"},
                },
                "required": [],
            },
            handler=lambda remote="origin", branch="": git_push(remote, branch, ws()),
            category="git",
        ),
        ToolDefinition(
            name="git_pull",
            description="Pull latest changes from a remote repository.",
            input_schema={
                "type": "object",
                "properties": {
                    "remote": {"type": "string", "description": "Remote name", "default": "origin"},
                    "branch": {"type": "string", "description": "Branch name"},
                },
                "required": [],
            },
            handler=lambda remote="origin", branch="": git_pull(remote, branch, ws()),
            category="git",
        ),
        ToolDefinition(
            name="detect_project",
            description="Auto-detect the project type, framework, languages, and git info.",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=lambda: detect_project(ws()),
            category="git",
        ),
        ToolDefinition(
            name="get_dependencies",
            description="Read and list project dependencies from package.json, requirements.txt, go.mod, etc.",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=lambda: get_dependencies(ws()),
            category="git",
        ),
        ToolDefinition(
            name="run_tests",
            description="Run the project's test suite. Auto-detects pytest, jest, cargo test, etc.",
            input_schema={
                "type": "object",
                "properties": {
                    "test_command": {"type": "string", "description": "Override test command (auto-detected if omitted)"},
                },
                "required": [],
            },
            handler=lambda test_command="": run_tests(test_command, ws()),
            category="git",
        ),
        ToolDefinition(
            name="lint_code",
            description="Run linter on code files. Supports flake8 (Python), ESLint (JS/TS).",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to lint", "default": "."},
                },
                "required": [],
            },
            handler=lambda path=".": lint_code(path, ws()),
            category="git",
        ),
        ToolDefinition(
            name="format_code",
            description="Format code using black (Python), prettier (JS/TS/JSON), gofmt (Go), etc.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File to format"},
                },
                "required": ["path"],
            },
            handler=lambda path: format_code(path, ws()),
            category="git",
        ),
    ]
    for tool in tools:
        registry.register(tool)
