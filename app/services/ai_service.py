"""Server-side provider adapters used only by the managed AI Gateway."""

import json
import os
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from google import genai

load_dotenv()

PROVIDERS = {
    "gemini": {
        "name": "Gemini",
        "key_env": "GEMINI_API_KEY",
        "model_env": "GEMINI_MODEL",
        "default_model": "gemini-3.6-flash",
        "models": [
            {"id": "gemini-3.5-flash-lite", "label": "Budget", "price": "$"},
            {"id": "gemini-3.6-flash", "label": "Balanced", "price": "$$"},
            {"id": "gemini-3.1-pro-preview", "label": "Powerful (Preview)", "price": "$$$"},
        ],
    },
    "openai": {
        "name": "OpenAI",
        "key_env": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
        "default_model": "gpt-5.4-mini",
        "models": [
            {"id": "gpt-5.4-nano", "label": "Budget", "price": "$"},
            {"id": "gpt-5.4-mini", "label": "Balanced", "price": "$$"},
            {"id": "gpt-5.4", "label": "Powerful", "price": "$$$"},
        ],
    },
    "claude": {
        "name": "Claude",
        "key_env": "ANTHROPIC_API_KEY",
        "model_env": "ANTHROPIC_MODEL",
        "default_model": "claude-sonnet-5",
        "models": [
            {"id": "claude-haiku-4-5", "label": "Budget", "price": "$"},
            {"id": "claude-sonnet-5", "label": "Balanced", "price": "$$"},
            {"id": "claude-opus-5", "label": "Powerful", "price": "$$$"},
        ],
    },
    "deepseek": {
        "name": "DeepSeek",
        "key_env": "DEEPSEEK_API_KEY",
        "model_env": "DEEPSEEK_MODEL",
        "default_model": "deepseek-v4-flash",
        "models": [
            {"id": "deepseek-v4-flash", "label": "Budget / Balanced", "price": "$"},
            {"id": "deepseek-v4-pro", "label": "Powerful", "price": "$$"},
        ],
    },
    "grok": {
        "name": "Grok",
        "key_env": "XAI_API_KEY",
        "model_env": "XAI_MODEL",
        "default_model": "grok-4.3",
        "models": [
            {"id": "grok-4.3", "label": "Balanced", "price": "$$"},
            {"id": "grok-4.5", "label": "Powerful", "price": "$$$"},
        ],
    },
    "groq": {
        "name": "Groq",
        "key_env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
        "default_model": "llama-3.3-70b-versatile",
        "models": [
            {"id": "llama-3.1-8b-instant", "label": "Fast", "price": "$"},
            {"id": "llama-3.3-70b-versatile", "label": "Balanced", "price": "$$"},
        ],
    },
}


class AIResult(str):
    """String-compatible reply carrying provider-reported token usage."""

    def __new__(cls, text: str, input_tokens: int = 0, output_tokens: int = 0):
        value = super().__new__(cls, text)
        value.input_tokens = int(input_tokens or 0)
        value.output_tokens = int(output_tokens or 0)
        return value


class ProviderHTTPError(RuntimeError):
    """Sanitized provider error retaining retry metadata, never credentials."""

    def __init__(self, status_code: int, detail: str, retry_after: float | None = None):
        super().__init__(f"AI provider request failed with HTTP {status_code}: {detail[:300]}")
        self.status_code = status_code
        self.retry_after = retry_after


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            return max(0.0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError):
            return None


def get_provider_status(company_id: int | None = None) -> list[dict]:
    """Return safe provider metadata without exposing API keys."""
    return [
        {
            "id": provider_id,
            "name": config["name"],
            "configured": bool(get_server_api_key(provider_id)),
            "managed_by_gateway": True,
            "model": get_server_model(provider_id),
            "models": config["models"],
        }
        for provider_id, config in PROVIDERS.items()
    ]


def get_server_model(provider: str) -> str:
    """Return the operator-configured model; customers cannot override it."""
    config = PROVIDERS[provider]
    selected = os.getenv(config["model_env"], config["default_model"])
    allowed = {item["id"] for item in config["models"]}
    return selected if selected in allowed else config["default_model"]


def get_server_api_key(provider: str) -> str:
    """Prefer encrypted owner-managed credentials, with environment fallback."""
    try:
        from app.owner.repository import get_provider_key
        saved = get_provider_key(provider)
        if saved: return saved
    except Exception:
        pass
    return os.getenv(PROVIDERS[provider]["key_env"], "").strip()


def get_selected_model(company_id: int, provider: str) -> str:
    """Return a company's validated model choice for a provider."""
    from app.database import settings_repository

    config = PROVIDERS[provider]
    selected = settings_repository.get_settings(company_id).get(
        "ai_models", {}
    ).get(provider)
    allowed = {item["id"] for item in config["models"]}
    if selected in allowed:
        return selected
    env_model = os.getenv(config["model_env"], config["default_model"])
    return env_model if env_model in allowed else config["default_model"]


def save_selected_model(company_id: int, provider: str, model: str) -> str:
    """Validate and persist one model selection per company and provider."""
    from app.database import settings_repository

    config = PROVIDERS[provider]
    allowed = {item["id"] for item in config["models"]}
    if model not in allowed:
        raise ValueError("This model is not supported for the selected provider.")
    settings = settings_repository.get_settings(company_id)
    selections = dict(settings.get("ai_models", {}))
    selections[provider] = model
    settings["ai_models"] = selections
    settings_repository.save_settings(company_id, settings)
    return model


def _post_json(url: str, payload: dict, headers: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ProviderHTTPError(
            exc.code, detail, _retry_after_seconds(exc.headers.get("Retry-After"))
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Could not connect to AI provider: {exc.reason}") from exc


def _gemini_reply(prompt: str, api_key: str, model: str) -> AIResult:
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        usage = getattr(response, "usage_metadata", None)
        return AIResult(
            response.text or "No response generated.",
            getattr(usage, "prompt_token_count", 0),
            getattr(usage, "candidates_token_count", 0),
        )
    finally:
        client.close()


def _openai_reply(prompt: str, api_key: str, model: str) -> AIResult:
    data = _post_json(
        "https://api.openai.com/v1/responses",
        {"model": model, "input": prompt},
        {"Authorization": f"Bearer {api_key}"},
    )
    parts = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])
    usage = data.get("usage", {})
    return AIResult(
        "\n".join(parts).strip() or "No response generated.",
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
    )


def _claude_reply(prompt: str, api_key: str, model: str) -> AIResult:
    data = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "model": model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        },
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    text = "\n".join(
        block.get("text", "")
        for block in data.get("content", [])
        if block.get("type") == "text"
    ).strip() or "No response generated."
    usage = data.get("usage", {})
    return AIResult(text, usage.get("input_tokens", 0), usage.get("output_tokens", 0))


def _deepseek_reply(prompt: str, api_key: str, model: str) -> AIResult:
    data = _post_json(
        "https://api.deepseek.com/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        {"Authorization": f"Bearer {api_key}"},
    )
    choices = data.get("choices", [])
    if not choices:
        return "No response generated."
    usage = data.get("usage", {})
    return AIResult(
        choices[0].get("message", {}).get("content", "").strip() or "No response generated.",
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )


def _grok_reply(prompt: str, api_key: str, model: str) -> AIResult:
    data = _post_json(
        "https://api.x.ai/v1/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        {"Authorization": f"Bearer {api_key}"},
    )
    choices = data.get("choices", [])
    if not choices:
        return "No response generated."
    usage = data.get("usage", {})
    return AIResult(
        choices[0].get("message", {}).get("content", "").strip() or "No response generated.",
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )


def _groq_reply(prompt: str, api_key: str, model: str) -> AIResult:
    data = _post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        {"model": model, "messages": [{"role": "user", "content": prompt}]},
        {"Authorization": f"Bearer {api_key}"},
    )
    choices = data.get("choices", [])
    if not choices:
        return AIResult("No response generated.")
    usage = data.get("usage", {})
    return AIResult(
        choices[0].get("message", {}).get("content", "").strip() or "No response generated.",
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )


def generate_reply(
    prompt: str,
    provider: str = "gemini",
    model: str | None = None,
    api_key: str | None = None,
) -> str:
    """Call one configured AI provider and return its text response."""
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown AI provider: {provider}")

    config = PROVIDERS[provider]
    api_key = (api_key or get_server_api_key(provider)).strip()
    if not api_key:
        raise RuntimeError(f"{config['name']} API key is not configured.")
    selected_model = model or os.getenv(config["model_env"], config["default_model"])

    callers = {
        "gemini": _gemini_reply,
        "openai": _openai_reply,
        "claude": _claude_reply,
        "deepseek": _deepseek_reply,
        "grok": _grok_reply,
        "groq": _groq_reply,
    }
    return callers[provider](prompt, api_key, selected_model)
