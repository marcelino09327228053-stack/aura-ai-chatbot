"""Unified AI provider integration for Gemini, OpenAI, Claude, DeepSeek, and Grok."""

import json
import os
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
}


def get_provider_status(company_id: int | None = None) -> list[dict]:
    """Return safe provider metadata without exposing API keys."""
    customer_status = {}
    if company_id is not None:
        from app.database import ai_provider_repository
        customer_status = ai_provider_repository.list_status(company_id)
    selected_models = {}
    if company_id is not None:
        from app.database import settings_repository
        selected_models = settings_repository.get_settings(company_id).get(
            "ai_models", {}
        )

    def status_model(provider_id: str, config: dict) -> str:
        selected = selected_models.get(
            provider_id,
            os.getenv(config["model_env"], config["default_model"]),
        )
        allowed = {item["id"] for item in config["models"]}
        return selected if selected in allowed else config["default_model"]

    return [
        {
            "id": provider_id,
            "name": config["name"],
            "configured": (
                provider_id in customer_status
                or bool(os.getenv(config["key_env"], "").strip())
            ),
            "customer_connected": provider_id in customer_status,
            "key_suffix": customer_status.get(provider_id, {}).get("key_suffix", ""),
            "model": status_model(provider_id, config),
            "models": config["models"],
        }
        for provider_id, config in PROVIDERS.items()
    ]


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
        raise RuntimeError(f"API request failed ({exc.code}): {detail[:300]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not connect to AI provider: {exc.reason}") from exc


def _gemini_reply(prompt: str, api_key: str, model: str) -> str:
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        return response.text or "No response generated."
    finally:
        client.close()


def _openai_reply(prompt: str, api_key: str, model: str) -> str:
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
    return "\n".join(parts).strip() or "No response generated."


def _claude_reply(prompt: str, api_key: str, model: str) -> str:
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
    return "\n".join(
        block.get("text", "")
        for block in data.get("content", [])
        if block.get("type") == "text"
    ).strip() or "No response generated."


def _deepseek_reply(prompt: str, api_key: str, model: str) -> str:
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
    return choices[0].get("message", {}).get("content", "").strip() or "No response generated."


def _grok_reply(prompt: str, api_key: str, model: str) -> str:
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
    return choices[0].get("message", {}).get("content", "").strip() or "No response generated."


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
    api_key = (api_key or os.getenv(config["key_env"], "")).strip()
    if not api_key:
        raise RuntimeError(f"{config['name']} API key is not configured.")
    selected_model = model or os.getenv(config["model_env"], config["default_model"])

    callers = {
        "gemini": _gemini_reply,
        "openai": _openai_reply,
        "claude": _claude_reply,
        "deepseek": _deepseek_reply,
        "grok": _grok_reply,
    }
    return callers[provider](prompt, api_key, selected_model)
