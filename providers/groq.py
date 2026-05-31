"""
Groq provider — extremely fast inference, generous free tier.
Free models: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b, gemma2-9b
Get free API key at: https://console.groq.com
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import Iterator

from .base import BaseProvider, ProviderError


class GroqProvider(BaseProvider):
    name = "groq"
    supports_streaming = True
    supports_tools = True

    FREE_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3.2-11b-vision-preview",
        "llama-3.2-90b-vision-preview",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
        "gemma-7b-it",
        "llama-guard-3-8b",
    ]

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, config):
        super().__init__(config)
        if not config.groq_api_key:
            raise ProviderError(
                "GROQ_API_KEY not set. Get a free key at: https://console.groq.com"
            )
        self.api_key = config.groq_api_key
        self.model = config.model or "llama-3.3-70b-versatile"

    def _request(self, payload: dict) -> dict:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.BASE_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise ProviderError(f"Groq API error {e.code}: {body[:500]}")
        except Exception as e:
            raise ProviderError(f"Groq request failed: {e}")

    def _build_payload(self, messages: list[dict], tools: list[dict], system: str, stream: bool) -> dict:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)

        payload: dict = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": stream,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        return payload

    def chat(self, messages, tools=None, system="", stream=False) -> dict:
        msgs = self.normalize_messages(messages)
        payload = self._build_payload(msgs, tools or [], system, False)
        resp = self._request(payload)

        choice = resp.get("choices", [{}])[0]
        message = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "stop")
        content = message.get("content", "") or ""
        raw_tools = message.get("tool_calls", []) or []

        tool_calls = self._extract_tool_calls(raw_tools)
        usage = resp.get("usage", {})

        return {
            "content": content,
            "tool_calls": tool_calls,
            "stop_reason": "tool_use" if tool_calls else finish_reason,
            "usage": {
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
            },
        }

    def stream_chat(self, messages, tools=None, system="") -> Iterator[str]:
        msgs = self.normalize_messages(messages)
        payload = self._build_payload(msgs, tools or [], system, True)
        data = json.dumps(payload).encode("utf-8")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            self.BASE_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                for line in resp:
                    s = line.decode("utf-8", errors="replace").strip()
                    if s.startswith("data:"):
                        json_str = s[5:].strip()
                        if json_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(json_str)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except Exception:
                            continue
        except Exception:
            yield ""

    def list_models(self) -> list[str]:
        return self.FREE_MODELS
