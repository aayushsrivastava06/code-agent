"""
Ollama provider — run models fully locally for free.
Install Ollama: https://ollama.ai
Pull a model: ollama pull llama3.2
No API key needed — completely free and private.
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import Iterator

from .base import BaseProvider, ProviderError


class OllamaProvider(BaseProvider):
    name = "ollama"
    supports_streaming = True
    supports_tools = True

    RECOMMENDED_MODELS = [
        "llama3.2",
        "llama3.1",
        "mistral",
        "codellama",
        "qwen2.5-coder",
        "deepseek-r1",
        "phi3",
        "gemma2",
        "mixtral",
        "llama3.2:1b",
        "llama3.2:3b",
        "starcoder2",
        "codegemma",
    ]

    def __init__(self, config):
        super().__init__(config)
        self.base_url = config.ollama_base_url.rstrip("/")
        self.model = config.model or "llama3.2"

    def _request(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise ProviderError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running: https://ollama.ai\n"
                f"Error: {e.reason}"
            )
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise ProviderError(f"Ollama error {e.code}: {body[:500]}")
        except Exception as e:
            raise ProviderError(f"Ollama request failed: {e}")

    def _build_payload(self, messages, tools, system, stream) -> dict:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)
        payload: dict = {
            "model": self.model,
            "messages": msgs,
            "stream": stream,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t.get("function", t)} for t in tools]
        return payload

    def chat(self, messages, tools=None, system="", stream=False) -> dict:
        msgs = self.normalize_messages(messages)
        payload = self._build_payload(msgs, tools or [], system, False)
        resp = self._request("/api/chat", payload)
        message = resp.get("message", {})
        content = message.get("content", "") or ""
        raw_tools = message.get("tool_calls", []) or []
        tool_calls = []
        for tc in raw_tools:
            fn = tc.get("function", {})
            tool_calls.append({
                "id": f"ollama_{fn.get('name', '')}_{len(tool_calls)}",
                "name": fn.get("name", ""),
                "arguments": fn.get("arguments", {}),
            })
        return {
            "content": content,
            "tool_calls": tool_calls,
            "stop_reason": "tool_use" if tool_calls else resp.get("done_reason", "stop"),
            "usage": {
                "input": resp.get("prompt_eval_count", 0),
                "output": resp.get("eval_count", 0),
            },
        }

    def stream_chat(self, messages, tools=None, system="") -> Iterator[str]:
        msgs = self.normalize_messages(messages)
        payload = self._build_payload(msgs, tools or [], system, True)
        url = f"{self.base_url}/api/chat"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for line in resp:
                    line_str = line.decode("utf-8", errors="replace").strip()
                    if not line_str:
                        continue
                    try:
                        chunk = json.loads(line_str)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done"):
                            break
                    except Exception:
                        continue
        except Exception:
            yield ""

    def list_models(self) -> list[str]:
        try:
            url = f"{self.base_url}/api/tags"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                models = data.get("models", [])
                return [m["name"] for m in models] if models else self.RECOMMENDED_MODELS
        except Exception:
            return self.RECOMMENDED_MODELS

    def pull_model(self, model_name: str) -> str:
        try:
            payload = {"name": model_name, "stream": False}
            resp = self._request("/api/pull", payload)
            return f"Pulled model: {model_name} — {resp.get('status', 'done')}"
        except Exception as e:
            return f"Failed to pull {model_name}: {e}"
