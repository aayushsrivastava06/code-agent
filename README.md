# Code Agent 🤖

**A powerful AI coding agent like Claude Code — using only 100% free AI models.**

Code Agent is a terminal-based AI assistant that can read, write, and edit your code, run shell commands, search the web, analyze git history, debug problems, and complete complex multi-step engineering tasks autonomously — all powered by free AI APIs.

---

## ✨ Features

### Core Capabilities (same as Claude Code)
- **File Operations** — Read, write, edit, copy, move, delete files with surgical precision
- **Shell Execution** — Run any command: npm, pip, make, docker, git, etc.
- **Code Search** — grep/ripgrep across the entire codebase with regex support
- **Find Definitions** — Locate functions, classes, interfaces, and variables
- **Web Search** — Search DuckDuckGo and fetch web pages for documentation
- **Git Operations** — Status, log, diff, blame, commit, branch, push, pull
- **Multi-step Reasoning** — Completes complex tasks over many iterations
- **Project Detection** — Auto-detects Python, Node, Rust, Go, Java projects
- **Code Formatting** — black, prettier, gofmt, rustfmt
- **Test Running** — pytest, jest, cargo test, go test
- **Linting** — flake8, ESLint

### Tools Available (30+)
| Category | Tools |
|----------|-------|
| Files | read_file, write_file, edit_file, append_file, delete_file, copy_file, move_file, list_directory, make_directory, file_info, diff_files |
| Shell | run_command, run_script, check_command, get_env, set_env, process_info, kill_process |
| Search | search_files, find_files, search_replace, get_symbols, find_todos, analyze_code |
| Web | web_search, fetch_url, download_file, check_url |
| Git | git_status, git_log, git_diff, git_blame, git_commit, git_branch, git_stash, git_push, git_pull |
| Project | detect_project, get_dependencies, run_tests, lint_code, format_code |
| Utility | calculate, encode_decode, json_parse, regex_test, create_todo, list_todos, generate_uuid, timestamp_convert, init_project |

---

## 🆓 Free AI Providers

All providers are completely free to use:

| Provider | Best Free Model | Speed | Tool Calling |
|----------|----------------|-------|-------------|
| **Gemini** | gemini-2.0-flash-exp | Fast | ✅ |
| **Groq** | llama-3.3-70b-versatile | ⚡ Fastest | ✅ |
| **OpenRouter** | google/gemini-2.0-flash-exp:free | Fast | ✅ |
| **Together AI** | Llama-3.3-70B-Turbo-Free | Fast | ✅ |
| **Ollama** | llama3.2 (local) | Varies | ✅ |
| **Cohere** | command-r | Medium | ✅ |
| **Mistral** | mistral-small-latest | Fast | ✅ |
| **HuggingFace** | Phi-3.5-mini-instruct | Medium | ❌ |

---

## 🚀 Quick Start

### Windows

```batch
# 1. Install Python 3.9+ from https://www.python.org/downloads/
# 2. Double-click run.bat
#    OR open PowerShell and run:
python install.py
python main.py
```

### Mac / Linux

```bash
# 1. Install dependencies
python3 install.py

# 2. Run
python3 main.py
# OR
bash run.sh
```

---

## 📦 Installation

### Step 1: Install Python
Download from [python.org](https://www.python.org/downloads/) — Python 3.9 or newer.
On Windows: ✅ check **"Add Python to PATH"** during installation.

### Step 2: Install Code Agent

```bash
# Clone or extract the zip
# Navigate to the folder
cd code-agent

# Run the installer
python install.py
```

This installs `rich` and `python-dotenv` automatically.

### Step 3: Get a Free API Key

Choose any one (you only need one to start):

**Gemini (Recommended)**
1. Visit [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with Google
3. Click "Create API key"
4. Copy the key

**Groq (Fastest)**
1. Visit [https://console.groq.com](https://console.groq.com)
2. Sign up (free)
3. Go to API Keys → Create Key
4. Copy the key

**Ollama (100% Local, No Key Needed)**
1. Download from [https://ollama.ai](https://ollama.ai)
2. Install and run
3. `ollama pull llama3.2` (downloads the model)
4. Set `AI_PROVIDER=ollama` in .env

### Step 4: Configure .env

```bash
# Copy the example
cp .env.example .env

# Edit and add your key
# Windows: notepad .env
# Mac/Linux: nano .env
```

Add your key:
```
AI_PROVIDER=gemini
GEMINI_API_KEY=your_actual_key_here
```

### Step 5: Run!

```bash
python main.py
```

---

## 💻 Usage

### Interactive Mode (default)

```bash
python main.py
```

Type your task at the prompt. The agent will reason, call tools, and complete the task.

### One-Shot Mode

```bash
python main.py "add type hints to all functions in utils.py"
python main.py "find all TODO comments and fix them"
python main.py "write tests for the authentication module"
python main.py "refactor this class to use async/await"
```

### With Options

```bash
# Use specific provider
python main.py --provider groq

# Use specific model
python main.py --provider groq --model llama-3.3-70b-versatile

# Safe mode (confirm before writes)
python main.py --safe

# Verbose mode (see all tool outputs)
python main.py --verbose

# Work in specific directory
python main.py --workspace /path/to/your/project

# List all providers
python main.py --providers

# Run setup wizard
python main.py --setup
```

---

## 🎮 Commands (in interactive mode)

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/exit` | Exit the agent |
| `/clear` | Clear screen and history |
| `/reset` | Reset conversation |
| `/provider <name>` | Switch AI provider |
| `/model <name>` | Switch model |
| `/models` | List models for current provider |
| `/providers` | List all providers |
| `/status` | Show current config |
| `/verbose` | Toggle verbose mode |
| `/safe` | Toggle safe mode |
| `/cd <path>` | Change directory |
| `/pwd` | Show current directory |
| `/ls [path]` | List directory |
| `/run <cmd>` | Run shell command |
| `/compact` | Summarize conversation |
| `/cost` | Show token usage |
| `/save <file>` | Save conversation |
| `/load <file>` | Load conversation |
| `/init <type>` | Init new project (python/node/typescript/fastapi) |

---

## 🧠 Example Tasks

```
You: Build a REST API with FastAPI that has CRUD endpoints for a todo list, 
     with SQLite database and proper error handling

You: Review my Python code for bugs, security issues, and performance problems

You: Migrate this JavaScript project to TypeScript

You: Write comprehensive unit tests for all functions in auth.py

You: Find all places where we make HTTP requests without error handling and fix them

You: Refactor the database layer to use an ORM instead of raw SQL

You: Add logging to every API endpoint with structured JSON logs

You: Create a CI/CD workflow file for GitHub Actions

You: Analyze the git history and summarize what changed last week
```

---

## 📁 Project Structure

```
code-agent/
├── main.py              # Entry point — run this
├── install.py           # One-click installer
├── run.bat              # Windows launcher
├── run.sh               # Unix/Mac launcher
├── requirements.txt     # Python dependencies
├── .env.example         # Configuration template
├── .env                 # Your actual config (create from .env.example)
│
├── agent/
│   ├── config.py        # Configuration management
│   ├── context.py       # Conversation history & context
│   ├── core.py          # Main agent loop
│   └── display.py       # Rich terminal UI
│
├── tools/
│   ├── registry.py      # Tool registry
│   ├── file_tools.py    # File read/write/edit/delete
│   ├── bash_tool.py     # Shell command execution
│   ├── search_tools.py  # Code search & analysis
│   ├── web_tools.py     # Web search & fetch
│   ├── git_tools.py     # Git operations
│   └── utility_tools.py # Math, JSON, regex, etc.
│
└── providers/
    ├── base.py          # Abstract provider class
    ├── factory.py       # Provider instantiation
    ├── gemini.py        # Google Gemini
    ├── groq.py          # Groq
    ├── openrouter.py    # OpenRouter
    ├── together.py      # Together AI
    ├── ollama.py        # Local Ollama
    ├── cohere.py        # Cohere
    ├── mistral.py       # Mistral AI
    └── huggingface.py   # HuggingFace
```

---

## 🔧 Troubleshooting

### "GEMINI_API_KEY not set"
Add your API key to the `.env` file. Run `python main.py --setup` for guided setup.

### "Cannot connect to Ollama"
Start Ollama: open the Ollama application or run `ollama serve` in terminal.
Then pull a model: `ollama pull llama3.2`

### "Module not found: rich"
Run: `pip install rich python-dotenv`

### Windows: Python not found
Download from [python.org](https://python.org) and check "Add Python to PATH".

### Slow responses
Switch to Groq for the fastest inference:
```bash
python main.py --provider groq
```

### Rate limits
Free tiers have rate limits. The agent handles these gracefully. Switch providers with `/provider` if you hit limits.

---

## 🚀 Deploy to GitHub

```bash
# Initialize git repo
git init
git add .
git commit -m "Initial Code Agent setup"

# Create repo on GitHub, then:
git remote add origin https://github.com/yourusername/code-agent.git
git push -u origin main
```

Note: The `.env` file is excluded from git (add it to `.gitignore`). 
Share only `.env.example` so others can configure their own keys.

---

## 📄 License

MIT License — use freely for personal and commercial projects.

---

## 🙏 Credits

Built to demonstrate that powerful AI coding assistants can be created using entirely free AI models. Inspired by Claude Code's architecture and capabilities.

**Free AI APIs used:**
- [Google Gemini](https://aistudio.google.com) — best overall quality
- [Groq](https://groq.com) — fastest inference  
- [OpenRouter](https://openrouter.ai) — model aggregator
- [Together AI](https://together.ai) — fast Llama inference
- [Ollama](https://ollama.ai) — local inference
- [Cohere](https://cohere.com) — tool-use focused
- [Mistral AI](https://mistral.ai) — efficient models
- [HuggingFace](https://huggingface.co) — open model hub
