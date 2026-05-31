"""
Google Gemini provider using the free REST API.
Free tier: gemini-2.0-flash-exp, gemini-1.5-flash, gemini-1.5-pro
Get free API key at: https://aistudio.google.com/app/apikey
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import Iterator

from .base import BaseProvider, ProviderError


class GeminiProvider(BaseProvider):
    name = "gemini"
    supports_streaming = True
    supports_tools = True

    FREE_MODELS = [
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-thinking-exp",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
        "gemini-exp-1206",
    ]

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, config):
        super().__init__(config)
        if not config.gemini_api_key:
            raise ProviderError(
                "GEMINI_API_KEY not set. Get a free key at: https://aistudio.google.com/app/apikey"
            )
        self.api_key = config.gemini_api_key
        self.model = config.model or "gemini-2.0-flash-exp"

    def _request(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.BASE_URL}/{self.model}:{endpoint}?key={self.api_key}"
        data = json.dumps(payload).encode("utf-8")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise ProviderError(f"Gemini API error {e.code}: {error_body[:500]}")
        except Exception as e:
            raise ProviderError(f"Gemini request failed: {e}")

    def _build_payload(self, messages: list[dict], tools: list[dict], system: str) -> dict:
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}],
            })

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            },
        }

        if system:
            payload["system_instruction"] = {"parts": [{"text": system}]}

        if tools:
            fn_declarations = []
            for tool in tools:
                fn = tool.get("function", tool)
                fn_declarations.append({
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {}),
                })
            payload["tools"] = [{"function_declarations": fn_declarations}]
            payload["tool_config"] = {"function_calling_config": {"mode": "AUTO"}}

        return payload

    def chat(self, messages, tools=None, system="", stream=False) -> dict:
        msgs = self.normalize_messages(messages)
        payload = self._build_payload(msgs, tools or [], system)

        try:
            resp = self._request("generateContent", payload)
        except Exception as e:
            raise ProviderError(str(e))

        candidates = resp.get("candidates", [])
        if not candidates:
            return {"content": "", "tool_calls": [], "stop_reason": "error", "usage": {}}

        candidate = candidates[0]
        content_parts = candidate.get("content", {}).get("parts", [])
        finish_reason = candidate.get("finishReason", "STOP")

        text_parts = []
        tool_calls = []

        for part in content_parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "id": f"gemini_{fc['name']}_{len(tool_calls)}",
                    "name": fc["name"],
                    "arguments": fc.get("args", {}),
                })

        usage = resp.get("usageMetadata", {})
        stop_map = {
            "STOP": "end_turn",
            "MAX_TOKENS": "max_tokens",
            "SAFETY": "stop",
            "RECITATION": "stop",
        }

        return {
            "content": "\n".join(text_parts),
            "tool_calls": tool_calls,
            "stop_reason": stop_map.get(finish_reason, "end_turn") if not tool_calls else "tool_use",
            "usage": {
                "input": usage.get("promptTokenCount", 0),
                "output": usage.get("candidatesTokenCount", 0),
            },
        }

    def stream_chat(self, messages, tools=None, system="") -> Iterator[str]:
        msgs = self.normalize_messages(messages)
        payload = self._build_payload(msgs, tools or [], system)
        payload["generationConfig"]["candidateCount"] = 1

        url = f"{self.BASE_URL}/{self.model}:streamGenerateContent?key={self.api_key}&alt=sse"
        data = json.dumps(payload).encode("utf-8")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                for line in resp:
                    line_str = line.decode("utf-8", errors="replace").strip()
                    if line_str.startswith("data:"):
                        json_str = line_str[5:].strip()
                        if json_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(json_str)
                            parts = chunk.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    yield part["text"]
                        except Exception:
                            continue
        except Exception:
            yield ""

    def list_models(self) -> list[str]:
        return self.FREE_MODELS
