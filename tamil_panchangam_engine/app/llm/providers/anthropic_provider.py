# app/llm/providers/anthropic_provider.py
"""
Anthropic Claude Provider

LLM interpretation using the official Anthropic Python SDK.
Model: claude-sonnet-4-6
JSON-only responses enforced via system prompt instruction.
No retries — fail fast to deterministic fallback.

If ANTHROPIC_API_KEY is missing → skip LLM entirely.
"""

import os
import logging
import json
import re
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
PROVIDER_NAME = "anthropic"


# ---------------------------------------------------------------------------
# JSON repair helpers (same logic as before, model-agnostic)
# ---------------------------------------------------------------------------

def _repair_json(content: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to repair common JSON issues from LLM output.
    Returns parsed dict if successful, None if repair fails.
    """
    repaired = content.strip()

    # Strip markdown code fences
    if repaired.startswith("```json"):
        repaired = repaired[7:]
    if repaired.startswith("```"):
        repaired = repaired[3:]
    if repaired.endswith("```"):
        repaired = repaired[:-3]
    repaired = repaired.strip()

    # Remove trailing commas before closing brackets
    repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)
    # Fill empty values
    repaired = re.sub(r':\s*,', ': null,', repaired)
    repaired = re.sub(r':\s*}', ': null}', repaired)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Try closing unclosed braces/brackets
    brace_count = repaired.count('{') - repaired.count('}')
    bracket_count = repaired.count('[') - repaired.count(']')
    if brace_count > 0 or bracket_count > 0:
        repaired += '}' * brace_count + ']' * bracket_count
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_available() -> bool:
    """Check if the Anthropic API key is configured."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    return bool(api_key and api_key.strip())


def get_provider_info() -> Dict[str, Any]:
    """Return provider metadata."""
    return {
        "provider": PROVIDER_NAME,
        "model": MODEL,
        "available": is_available(),
    }


def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1500,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """
    Call Anthropic Claude and return a parsed JSON response.

    Args:
        system_prompt: System instructions for the model.
        user_prompt:   User message containing the astrological context.
        max_tokens:    Maximum completion tokens.

    Returns:
        (response_json, usage_info, error_message)
        - response_json : parsed dict on success, None on failure
        - usage_info    : token-usage dict or None
        - error_message : error string on failure, None on success
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, None, "anthropic_key_missing"

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Enforce JSON-only output via the system prompt.
        json_instruction = (
            "\n\nIMPORTANT: Your response must be valid JSON only. "
            "Do not include markdown code fences, explanatory text, or anything "
            "outside the JSON object."
        )

        response = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system_prompt + json_instruction,
            messages=[{"role": "user", "content": user_prompt}],
        )

        content = response.content[0].text
        stop_reason = response.stop_reason

        usage_info = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            "model": MODEL,
            "provider": PROVIDER_NAME,
        }

        if stop_reason == "max_tokens":
            logger.warning(
                "Anthropic response TRUNCATED (stop_reason=max_tokens). "
                "Used %d completion tokens out of %d limit. Output may be incomplete.",
                usage_info["completion_tokens"],
                max_tokens,
            )

        try:
            parsed_json = json.loads(content)
            logger.info(
                "Anthropic call success: %d tokens (stop_reason=%s)",
                usage_info["total_tokens"],
                stop_reason,
            )
            return parsed_json, usage_info, None

        except json.JSONDecodeError as exc:
            logger.warning("JSON parse failed, attempting repair: %s", exc)
            logger.debug("Raw LLM content (first 500 chars): %s", content[:500])

            repaired = _repair_json(content)
            if repaired is not None:
                logger.info(
                    "JSON repair successful: %d tokens", usage_info["total_tokens"]
                )
                return repaired, usage_info, None

            logger.error("Anthropic returned invalid JSON after repair attempt.")
            logger.debug("Raw LLM content (last 200 chars): %s", content[-200:])
            return None, usage_info, "json_parse_error"

    except Exception as exc:
        try:
            import anthropic as _anthropic

            if isinstance(exc, _anthropic.AuthenticationError):
                logger.error("Anthropic authentication failed — check ANTHROPIC_API_KEY")
                return None, None, "api_auth_error"
            if isinstance(exc, _anthropic.RateLimitError):
                logger.error("Anthropic rate limit exceeded")
                return None, None, "api_rate_limit"
            if isinstance(exc, _anthropic.APIConnectionError):
                logger.error("Anthropic connection error: %s", exc)
                return None, None, "api_connection_error"
            if isinstance(exc, _anthropic.APIStatusError):
                logger.error("Anthropic API error %d: %s", exc.status_code, exc.message)
                return None, None, f"api_error_{exc.status_code}"
        except ImportError:
            pass

        logger.error("Anthropic API error: %s", exc)
        return None, None, f"api_error: {exc}"


# ---------------------------------------------------------------------------
# Backward-compatibility alias
# ---------------------------------------------------------------------------

def call_openai(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1500,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """Alias for call_llm — kept for backward compatibility."""
    return call_llm(system_prompt, user_prompt, max_tokens)
