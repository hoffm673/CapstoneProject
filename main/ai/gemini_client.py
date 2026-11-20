"""Thin wrapper around the google-genai SDK.

Everything that talks to Gemini goes through `generate_json()` so that
retries, timeouts, logging and cost tracking live in exactly one place.
"""
import logging
from functools import lru_cache

from django.conf import settings
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class GeminiNotConfigured(RuntimeError):
    """Raised when GEMINI_API_KEY is missing. Callers should degrade gracefully."""


class GeminiCallFailed(RuntimeError):
    """Raised when the API call or response parsing fails after retries."""


@lru_cache(maxsize=1)
def get_client():
    """Build one client per process and reuse it (it holds an HTTP connection pool)."""
    # Imported lazily so the rest of the site works even if the package isn't installed.
    from google import genai
    from google.genai import types

    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        raise GeminiNotConfigured("GEMINI_API_KEY is not set")

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=settings.GEMINI_TIMEOUT_MS,
            # SDK-level retry with exponential backoff + jitter.
            # 429 = rate limited, 5xx = transient server errors. Never retry 400s.
            retry_options=types.HttpRetryOptions(
                attempts=4,
                initial_delay=2.0,
                max_delay=30.0,
                exp_base=2.0,
                jitter=1.0,
                http_status_codes=[429, 500, 502, 503, 504],
            ),
        ),
    )


def generate_json(*, system_instruction: str, prompt: str, schema: type[BaseModel],
                  model: str | None = None, max_output_tokens: int = 800):
    """Call Gemini with structured (JSON) output and return a validated `schema` instance.

    Returns (parsed_object, usage_dict).
    """
    from google.genai import errors, types

    model = model or settings.GEMINI_MODEL
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=schema,              # Pydantic model -> JSON schema, enforced by the API
        temperature=0.2,                     # low = consistent, factual summaries
        max_output_tokens=max_output_tokens, # hard cap on cost per call
        thinking_config=types.ThinkingConfig(thinking_level="low"),  # summarizing doesn't need deep reasoning
    )

    try:
        response = get_client().models.generate_content(
            model=model, contents=prompt, config=config,
        )
    except errors.APIError as exc:
        # exc.code is the HTTP status; retries already happened in the SDK.
        logger.warning("Gemini API error %s: %s", exc.code, exc.message)
        raise GeminiCallFailed(f"Gemini API error {exc.code}") from exc

    usage = _usage(response)
    logger.info("Gemini call model=%s in=%s out=%s", model, usage["input_tokens"], usage["output_tokens"])

    # Prefer the SDK's parsed object; fall back to validating the raw text ourselves.
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, schema):
        return parsed, usage
    try:
        return schema.model_validate_json(response.text or ""), usage
    except ValidationError as exc:
        # Usually means output got cut off by max_output_tokens or the response was blocked.
        logger.warning("Gemini returned unparseable output: %s", exc)
        raise GeminiCallFailed("Unparseable model output") from exc


def _usage(response) -> dict:
    meta = getattr(response, "usage_metadata", None)
    return {
        "input_tokens": getattr(meta, "prompt_token_count", 0) or 0,
        "output_tokens": (getattr(meta, "candidates_token_count", 0) or 0)
                         + (getattr(meta, "thoughts_token_count", 0) or 0),  # thinking tokens bill as output
    }
