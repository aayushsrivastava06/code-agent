"""
Provider factory — instantiate the right provider based on config.
"""

from .base import BaseProvider, ProviderError


def create_provider(config) -> BaseProvider:
    name = config.provider.lower()
    try:
        if name == "gemini":
            from .gemini import GeminiProvider
            return GeminiProvider(config)
        elif name == "groq":
            from .groq import GroqProvider
            return GroqProvider(config)
        elif name == "openrouter":
            from .openrouter import OpenRouterProvider
            return OpenRouterProvider(config)
        elif name == "together":
            from .together import TogetherProvider
            return TogetherProvider(config)
        elif name == "ollama":
            from .ollama import OllamaProvider
            return OllamaProvider(config)
        elif name == "cohere":
            from .cohere import CohereProvider
            return CohereProvider(config)
        elif name == "mistral":
            from .mistral import MistralProvider
            return MistralProvider(config)
        elif name == "huggingface":
            from .huggingface import HuggingFaceProvider
            return HuggingFaceProvider(config)
        else:
            raise ProviderError(
                f"Unknown provider: {name}\n"
                f"Available: gemini, groq, openrouter, together, ollama, cohere, mistral, huggingface"
            )
    except ImportError as e:
        raise ProviderError(f"Failed to import provider '{name}': {e}")


def get_all_provider_info() -> dict:
    return {
        "gemini": {
            "name": "Google Gemini",
            "free": True,
            "key_env": "GEMINI_API_KEY",
            "get_key": "https://aistudio.google.com/app/apikey",
            "models": ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"],
            "tools": True,
            "streaming": True,
            "notes": "Best overall quality. gemini-2.0-flash-exp is free and very capable.",
        },
        "groq": {
            "name": "Groq",
            "free": True,
            "key_env": "GROQ_API_KEY",
            "get_key": "https://console.groq.com",
            "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
            "tools": True,
            "streaming": True,
            "notes": "Fastest inference. llama-3.3-70b-versatile is free and very smart.",
        },
        "openrouter": {
            "name": "OpenRouter",
            "free": True,
            "key_env": "OPENROUTER_API_KEY",
            "get_key": "https://openrouter.ai/keys",
            "models": ["google/gemini-2.0-flash-exp:free", "meta-llama/llama-3.3-70b-instruct:free"],
            "tools": True,
            "streaming": True,
            "notes": "Access to many providers through one API. Free models marked with :free.",
        },
        "together": {
            "name": "Together AI",
            "free": True,
            "key_env": "TOGETHER_API_KEY",
            "get_key": "https://api.together.xyz",
            "models": ["meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"],
            "tools": True,
            "streaming": True,
            "notes": "Good free tier with Llama models.",
        },
        "ollama": {
            "name": "Ollama (Local)",
            "free": True,
            "key_env": None,
            "get_key": "https://ollama.ai",
            "models": ["llama3.2", "codellama", "qwen2.5-coder", "deepseek-r1"],
            "tools": True,
            "streaming": True,
            "notes": "Completely free, runs locally. No internet needed after model download.",
        },
        "cohere": {
            "name": "Cohere",
            "free": True,
            "key_env": "COHERE_API_KEY",
            "get_key": "https://dashboard.cohere.com/api-keys",
            "models": ["command-r", "command-r-plus"],
            "tools": True,
            "streaming": True,
            "notes": "Good tool-use support with command-r.",
        },
        "mistral": {
            "name": "Mistral AI",
            "free": True,
            "key_env": "MISTRAL_API_KEY",
            "get_key": "https://console.mistral.ai/api-keys",
            "models": ["mistral-small-latest", "open-mistral-7b", "open-mixtral-8x7b"],
            "tools": True,
            "streaming": True,
            "notes": "Open models available. mistral-small has generous free tier.",
        },
        "huggingface": {
            "name": "HuggingFace",
            "free": True,
            "key_env": "HUGGINGFACE_TOKEN",
            "get_key": "https://huggingface.co/settings/tokens",
            "models": ["microsoft/Phi-3.5-mini-instruct", "HuggingFaceH4/zephyr-7b-beta"],
            "tools": False,
            "streaming": False,
            "notes": "Access to thousands of open models. No tool-calling support.",
        },
    }
