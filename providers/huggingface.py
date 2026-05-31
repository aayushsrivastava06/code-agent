"""
HuggingFace Inference API provider — free tier with many open models.
Get free token at: https://huggingface.co/settings/tokens
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import Iterator

from .base import BaseProvider, ProviderError


class HuggingFaceProvider(BaseProvider):
    name = "huggingface"
    supports_streaming = False
    supports_tools = False

    FREE_MODELS = [
        "microsoft/Phi-3.5-mini-instruct",
        "microsoft/Phi-3-mini-4k-instruct",
        "HuggingFaceH4/zephyr-7b-beta",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "google/gemma-2-2b-it",
        "Qwen/Qwen2.5-7B-Instruct",
        "meta-llama/Llama-3.2-1B-Instruct",
        "deepseek-ai/deepseek-coder-1.3b-instruct",
    ]

    BASE_URL = "https://api-inference.huggingface.co/models"

    def __init__(self, config):
        super().__init__(config)
        if not config.huggingface_token:
            raise ProviderError(
                "HUGGINGFACE_TOKEN not set. Get a free token at: https://huggingface.co/settings/tokens"
            )
        self.token = config.huggingface_token
        self.model = config.model or "microsoft/Phi-3.5-mini-instruct"

    def _build_prompt(self, messages: list[dict], system: str) -> str:
        parts = []
        if system:
            parts.append(f"<|system|>\n{system}\n<|end|>")
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                parts.append(f"<|user|>\n{content}\n<|end|>")
            elif role == "assistant":
                parts.append(f"<|assistant|>\n{content}\n<|end|>")
        parts.append("<|assistant|>")
        return "\n".join(parts)

    def _request(self, payload: dict) -> dict:
        url = f"{self.BASE_URL}/{self.model}"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 503:
                raise ProviderError(f"Model {self.model} is loading. Please wait and try again. ({body[:200]})")
            raise ProviderError(f"HuggingFace API error {e.code}: {body[:500]}")
        except Exception as e:
            raise ProviderError(f"HuggingFace request failed: {e}")

    def chat(self, messages, tools=None, system="", stream=False) -> dict:
        msgs = self.normalize_messages(messages)
        prompt = self._build_prompt(msgs, system)
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": min(self.config.max_tokens, 2048),
                "temperature": self.config.temperature,
                "return_full_text": False,
            },
        }
        resp = self._request(payload)

        if isinstance(resp, list) and resp:
            text = resp[0].get("generated_text", "")
        elif isinstance(resp, dict):
            text = resp.get("generated_text", str(resp))
        else:
            text = str(resp)

        text = text.replace("<|end|>", "").replace("<|assistant|>", "").strip()

        return {
            "content": text,
            "tool_calls": [],
            "stop_reason": "end_turn",
            "usage": {"input": len(prompt.split()), "output": len(text.split())},
        }

    def list_models(self) -> list[str]:
        return self.FREE_MODELS
