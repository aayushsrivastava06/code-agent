"""
Mistral AI provider — free tier with mistral-small and open models.
Get free API key at: https://console.mistral.ai/api-keys
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import Iterator

from .base import BaseProvider, ProviderError


class MistralProvider(BaseProvider):
    name = "mistral"
    supports_streaming = True
    supports_tools = True

    FREE_MODELS = [
        "mistral-small-latest",
        "mistral-tiny",
        "open-mistral-7b",
        "open-mixtral-8x7b",
        "codestral-mamba-latest",
    ]

    BASE_URL = "https://api.mistral.ai/v1/chat/completions"

    def __init__(self, config):
        super().__init__(config)
        if not config.mistral_api_key:
            raise ProviderError(
                "MISTRAL_API_KEY not set. Get a free key at: https://console.mistral.ai/api-keys"
            )
        self.api_key = config.mistral_api_key
        self.model = config.model or "mistral-small-latest"

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
            raise ProviderError(f"Mistral API error {e.code}: {body[:500]}")
        except Exception as e:
            raise ProviderError(f"Mistral request failed: {e}")

    def _build_payload(self, messages, tools, system, stream) -> dict:
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
        content = message.get("content", "") or ""
        raw_tools = message.get("tool_calls", []) or []
        tool_calls = self._extract_tool_calls(raw_tools)
        usage = resp.get("usage", {})
        return {
            "content": content,
            "tool_calls": tool_calls,
            "stop_reason": "tool_use" if tool_calls else choice.get("finish_reason", "stop"),
            "usage": {"input": usage.get("prompt_tokens", 0), "output": usage.get("completion_tokens", 0)},
        }

    def stream_chat(self, messages, tools=None, system="") -> Iterator[str]:
        msgs = self.normalize_messages(messages)
        payload = self._build_payload(msgs, tools or [], system, True)
        data = json.dumps(payload).encode("utf-8")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            self.BASE_URL, data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                for line in resp:
                    s = line.decode("utf-8", errors="replace").strip()
                    if s.startswith("data:"):
                        js = s[5:].strip()
                        if js == "[DONE]":
                            break
                        try:
                            chunk = json.loads(js)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except Exception:
                            continue
        except Exception:
            yield ""

    def list_models(self) -> list[str]:
        return self.FREE_MODELS
