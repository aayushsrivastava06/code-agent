"""
Cohere provider — free tier available with command-r.
Get free API key at: https://dashboard.cohere.com/api-keys
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import Iterator

from .base import BaseProvider, ProviderError


class CohereProvider(BaseProvider):
    name = "cohere"
    supports_streaming = True
    supports_tools = True

    FREE_MODELS = [
        "command-r",
        "command-r-plus",
        "command",
        "command-light",
    ]

    BASE_URL = "https://api.cohere.com/v2/chat"

    def __init__(self, config):
        super().__init__(config)
        if not config.cohere_api_key:
            raise ProviderError(
                "COHERE_API_KEY not set. Get a free key at: https://dashboard.cohere.com/api-keys"
            )
        self.api_key = config.cohere_api_key
        self.model = config.model or "command-r"

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
            raise ProviderError(f"Cohere API error {e.code}: {body[:500]}")
        except Exception as e:
            raise ProviderError(f"Cohere request failed: {e}")

    def _build_payload(self, messages, tools, system, stream) -> dict:
        msgs = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                msgs.append({"role": "user", "content": content})
            elif role == "assistant":
                msgs.append({"role": "assistant", "content": content})

        payload: dict = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": stream,
        }
        if system:
            payload["system"] = system
        if tools:
            cohere_tools = []
            for t in tools:
                fn = t.get("function", t)
                params = fn.get("parameters", {})
                props = params.get("properties", {})
                required = params.get("required", [])
                cohere_params = {}
                for name, schema in props.items():
                    cohere_params[name] = {
                        "description": schema.get("description", ""),
                        "type": schema.get("type", "string"),
                        "required": name in required,
                    }
                cohere_tools.append({
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "parameter_definitions": cohere_params,
                })
            payload["tools"] = cohere_tools
        return payload

    def chat(self, messages, tools=None, system="", stream=False) -> dict:
        msgs = self.normalize_messages(messages)
        payload = self._build_payload(msgs, tools or [], system, False)
        resp = self._request(payload)
        message = resp.get("message", {})
        content_list = message.get("content", [])
        content = ""
        for item in content_list:
            if isinstance(item, dict) and item.get("type") == "text":
                content += item.get("text", "")
            elif isinstance(item, str):
                content += item
        tool_calls = []
        for tc in message.get("tool_calls", []) or []:
            tool_calls.append({
                "id": tc.get("id", f"co_{len(tool_calls)}"),
                "name": tc.get("name", ""),
                "arguments": tc.get("parameters", {}),
            })
        usage = resp.get("usage", {})
        return {
            "content": content,
            "tool_calls": tool_calls,
            "stop_reason": "tool_use" if tool_calls else resp.get("finish_reason", "stop"),
            "usage": {
                "input": usage.get("billed_units", {}).get("input_tokens", 0),
                "output": usage.get("billed_units", {}).get("output_tokens", 0),
            },
        }

    def list_models(self) -> list[str]:
        return self.FREE_MODELS
