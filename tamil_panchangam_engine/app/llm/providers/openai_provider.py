# app/llm/providers/openai_provider.py
"""
OpenAI Provider v1.0

Language-only interpretation using OpenAI's API.
Model: gpt-4o-mini
Temperature: 0.7
JSON-only responses enforced
No retries - fail fast to deterministic fallback

If API key missing -> skip LLM entirely.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"
TEMPERATURE = 0.7
PROVIDER_NAME = "openai"


def is_available() -> bool:
    """Check if OpenAI API key is configured."""
    api_key = os.environ.get("OPENAI_API_KEY")
    return bool(api_key and api_key.strip())


def get_provider_info() -> Dict[str, Any]:
    """Return provider metadata."""
    return {
        "provider": PROVIDER_NAME,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "available": is_available()
    }


def call_openai(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 800
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """
    Call OpenAI API for language interpretation.
    
    Args:
        system_prompt: The system instructions
        user_prompt: The user message with context
        max_tokens: Maximum completion tokens
        
    Returns:
        Tuple of (response_json, usage_info, error_message)
        - response_json: Parsed JSON response or None
        - usage_info: Token usage dict or None
        - error_message: Error string if failed, None if success
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None, None, "openai_key_missing"
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=TEMPERATURE,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        usage = response.usage
        
        usage_info = {
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
            "model": response.model,
            "provider": PROVIDER_NAME
        }
        
        try:
            parsed_json = json.loads(content)
            logger.info(
                f"OpenAI call success: {usage_info['total_tokens']} tokens"
            )
            return parsed_json, usage_info, None
        except json.JSONDecodeError as e:
            logger.error(f"OpenAI returned invalid JSON: {e}")
            return None, usage_info, "json_parse_error"
            
    except ImportError:
        logger.error("openai package not installed")
        return None, None, "openai_not_installed"
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return None, None, f"api_error: {str(e)}"
