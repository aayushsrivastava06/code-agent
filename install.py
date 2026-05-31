#!/usr/bin/env python3
"""
One-click installer for Code Agent.
Run: python install.py
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path


def run(cmd, check=True):
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0 and check:
        print(f"ERROR: {result.stderr[:300]}")
    return result.returncode == 0


def main():
    print("=" * 60)
    print("  Code Agent Installer")
    print("=" * 60)
    print()

    py = sys.executable
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"ERROR: Python 3.9+ required. Found: {sys.version}")
        sys.exit(1)

    print(f"Python: {sys.version.split()[0]} ✓")

    print("\n[1/4] Installing dependencies...")
    ok = run(f'"{py}" -m pip install --upgrade pip -q')
    ok = run(f'"{py}" -m pip install -r requirements.txt')
    if not ok:
        print("WARNING: Some packages failed to install. Trying minimal install...")
        run(f'"{py}" -m pip install rich python-dotenv')

    print("\n[2/4] Checking for ripgrep (optional, for faster code search)...")
    if shutil.which("rg"):
        print("  ripgrep found ✓")
    else:
        print("  ripgrep not found (optional) — falling back to Python search")
        print("  Install from: https://github.com/BurntSushi/ripgrep/releases")

    print("\n[3/4] Creating .env from template...")
    env_path = Path(".env")
    env_example = Path(".env.example")
    if not env_path.exists() and env_example.exists():
        shutil.copy(env_example, env_path)
        print("  Created .env from template")
    elif env_path.exists():
        print("  .env already exists, skipping")

    print("\n[4/4] Verifying installation...")
    result = subprocess.run(
        [py, "-c", "import rich; from agent.config import Config; print('OK')"],
        capture_output=True, text=True, cwd=str(Path(__file__).parent)
    )
    if "OK" in result.stdout:
        print("  Verification passed ✓")
    else:
        print(f"  Verification warning: {result.stderr[:200]}")

    print()
    print("=" * 60)
    print("  Installation Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print()
    print("  1. Edit .env and add your free API key:")
    print("     GEMINI_API_KEY=your_key  (https://aistudio.google.com/app/apikey)")
    print("     — OR —")
    print("     GROQ_API_KEY=your_key    (https://console.groq.com)")
    print("     — OR —")
    print("     Install Ollama for 100% local, free inference:")
    print("     https://ollama.ai  →  ollama pull llama3.2")
    print()
    print("  2. Run the agent:")
    print()
    if sys.platform == "win32":
        print("     run.bat")
        print("     — OR —")
        print("     python main.py")
    else:
        print("     bash run.sh")
        print("     — OR —")
        print("     python main.py")
    print()
    print("  3. Run setup wizard:")
    print("     python main.py --setup")
    print()
    print("  4. Get help:")
    print("     python main.py --help")
    print("     python main.py --providers")
    print()


if __name__ == "__main__":
    main()
