# app/llm/token_estimator.py
"""
Token Estimator v1.0

Estimates token counts for LLM calls using character heuristics.
Used to enforce guardrails before making OpenAI API calls.

Hard limits:
- max_completion_tokens = 800
- Refuse call if estimated total tokens > 1500
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAX_COMPLETION_TOKENS = 800
MAX_TOTAL_TOKENS = 1500
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using character heuristics.
    Uses ~4 characters per token as a conservative estimate.
    """
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_prompt_tokens(prompt: str, context: Dict[str, Any]) -> int:
    """
    Estimate total prompt tokens including system prompt and context.
    """
    import json
    context_str = json.dumps(context, default=str)
    total_chars = len(prompt) + len(context_str)
    return estimate_tokens(str(total_chars))


def check_token_limits(
    prompt: str,
    context: Dict[str, Any],
    max_completion: int = MAX_COMPLETION_TOKENS
) -> Dict[str, Any]:
    """
    Check if the request would exceed token limits.
    
    Returns:
        dict with keys:
        - allowed: bool - whether the request can proceed
        - estimated_prompt_tokens: int
        - max_completion_tokens: int
        - estimated_total: int
        - reason: str or None
    """
    import json
    
    context_str = json.dumps(context, default=str)
    prompt_tokens = estimate_tokens(prompt + context_str)
    estimated_total = prompt_tokens + max_completion
    
    result = {
        "allowed": True,
        "estimated_prompt_tokens": prompt_tokens,
        "max_completion_tokens": max_completion,
        "estimated_total": estimated_total,
        "reason": None
    }
    
    if estimated_total > MAX_TOTAL_TOKENS:
        result["allowed"] = False
        result["reason"] = f"Estimated total tokens ({estimated_total}) exceeds limit ({MAX_TOTAL_TOKENS})"
        logger.warning(
            f"Token limit exceeded: {estimated_total} > {MAX_TOTAL_TOKENS}"
        )
    
    return result


def get_max_completion_tokens() -> int:
    """Return the configured max completion tokens."""
    return MAX_COMPLETION_TOKENS


def get_max_total_tokens() -> int:
    """Return the configured max total tokens."""
    return MAX_TOTAL_TOKENS
