"""
Configuration management for the AI coding agent.
Loads settings from environment variables and .env file.
"""

import os
import json
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """Central configuration object."""

    def __init__(self):
        self.provider: str = os.getenv("AI_PROVIDER", "gemini").lower()
        self.model: str = os.getenv("AI_MODEL", "")
        self.max_tokens: int = int(os.getenv("MAX_TOKENS", "8192"))
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
        self.max_iterations: int = int(os.getenv("MAX_ITERATIONS", "50"))
        self.context_window: int = int(os.getenv("CONTEXT_WINDOW", "100000"))

        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        self.openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
        self.together_api_key: str = os.getenv("TOGETHER_API_KEY", "")
        self.ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.cohere_api_key: str = os.getenv("COHERE_API_KEY", "")
        self.mistral_api_key: str = os.getenv("MISTRAL_API_KEY", "")
        self.huggingface_token: str = os.getenv("HUGGINGFACE_TOKEN", "")

        self.workspace_dir: Path = Path(os.getenv("WORKSPACE_DIR", ".")).resolve()
        self.history_file: Path = Path(os.getenv("HISTORY_FILE", "~/.agent_history")).expanduser()
        self.config_dir: Path = Path(os.getenv("CONFIG_DIR", "~/.agent")).expanduser()
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.allow_bash: bool = os.getenv("ALLOW_BASH", "true").lower() == "true"
        self.allow_web: bool = os.getenv("ALLOW_WEB", "true").lower() == "true"
        self.allow_file_write: bool = os.getenv("ALLOW_FILE_WRITE", "true").lower() == "true"
        self.safe_mode: bool = os.getenv("SAFE_MODE", "false").lower() == "true"

        self.max_file_size_kb: int = int(os.getenv("MAX_FILE_SIZE_KB", "512"))
        self.max_output_lines: int = int(os.getenv("MAX_OUTPUT_LINES", "200"))
        self.bash_timeout: int = int(os.getenv("BASH_TIMEOUT", "30"))

        self.theme: str = os.getenv("AGENT_THEME", "dark")
        self.verbose: bool = os.getenv("VERBOSE", "false").lower() == "true"
        self.stream: bool = os.getenv("STREAM", "true").lower() == "true"

        self._provider_defaults = {
            "gemini": "gemini-2.0-flash-exp",
            "groq": "llama-3.3-70b-versatile",
            "openrouter": "google/gemini-2.0-flash-exp:free",
            "together": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            "ollama": "llama3.2",
            "cohere": "command-r",
            "mistral": "mistral-small-latest",
            "huggingface": "microsoft/Phi-3.5-mini-instruct",
        }

        if not self.model:
            self.model = self._provider_defaults.get(self.provider, "gemini-2.0-flash-exp")

    def get_provider_config(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": self.stream,
        }

    def save_setting(self, key: str, value: str):
        settings_file = self.config_dir / "settings.json"
        settings = {}
        if settings_file.exists():
            with open(settings_file) as f:
                settings = json.load(f)
        settings[key] = value
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)

    def load_settings(self) -> dict:
        settings_file = self.config_dir / "settings.json"
        if settings_file.exists():
            with open(settings_file) as f:
                return json.load(f)
        return {}

    def list_providers(self) -> list[str]:
        return list(self._provider_defaults.keys())

    def get_default_model(self, provider: str) -> str:
        return self._provider_defaults.get(provider, "")


config = Config()
