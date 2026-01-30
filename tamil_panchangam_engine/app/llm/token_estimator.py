# app/llm/token_estimator.py
"""
Token Estimator v1.1

Estimates token counts for LLM calls.
Falls back to character heuristic if tiktoken unavailable.
Used to enforce guardrails before making OpenAI API calls.

Hard limits:
- max_completion_tokens = 1500
- max_total_tokens = 6000
- Refuse call if estimated total tokens exceeds limit
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAX_COMPLETION_TOKENS = 1500
MAX_TOTAL_TOKENS = 6000

_encoding = None

def _get_encoding():
    """Get or create the tiktoken encoding for gpt-4o-mini."""
    global _encoding
    if _encoding is None:
        try:
            import tiktoken
            _encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoding: {e}, using fallback")
            _encoding = "fallback"
    return _encoding


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using tiktoken for accurate counts.
    Falls back to character heuristic if tiktoken unavailable.
    """
    if not text:
        return 0
    
    encoding = _get_encoding()
    if encoding == "fallback":
        return max(1, len(text) // 4)
    
    try:
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"tiktoken encode failed: {e}, using fallback")
        return max(1, len(text) // 4)


def estimate_prompt_tokens(prompt: str, context: Dict[str, Any]) -> int:
    """
    Estimate total prompt tokens including system prompt and context.
    """
    import json
    context_str = json.dumps(context, default=str)
    combined_text = prompt + context_str
    return estimate_tokens(combined_text)


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
