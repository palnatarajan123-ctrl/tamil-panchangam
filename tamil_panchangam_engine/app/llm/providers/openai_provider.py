# app/llm/providers/openai_provider.py
"""
OpenAI Provider v1.2

Language-only interpretation using OpenAI's API via urllib (no external packages needed).
Model: gpt-4o-mini
Temperature: 0.7
JSON-only responses enforced
No retries - fail fast to deterministic fallback

If API key missing -> skip LLM entirely.
"""

import os
import logging
import json
import urllib.request
import urllib.error
import ssl
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"
TEMPERATURE = 0.7
PROVIDER_NAME = "openai"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


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
    Call OpenAI API for language interpretation using urllib.
    
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
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(OPENAI_API_URL, data=data, headers=headers, method='POST')
        
        ctx = ssl.create_default_context()
        
        with urllib.request.urlopen(req, timeout=60, context=ctx) as response:
            response_data = json.loads(response.read().decode('utf-8'))
        
        content = response_data["choices"][0]["message"]["content"]
        usage = response_data.get("usage", {})
        
        usage_info = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": response_data.get("model", MODEL),
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
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ''
        try:
            error_data = json.loads(error_body)
            error_msg = error_data.get("error", {}).get("message", error_body[:200])
        except json.JSONDecodeError:
            error_msg = error_body[:200]
        logger.error(f"OpenAI API error {e.code}: {error_msg}")
        return None, None, f"api_error_{e.code}: {error_msg}"
    except urllib.error.URLError as e:
        logger.error(f"OpenAI request error: {e.reason}")
        return None, None, f"request_error: {str(e.reason)}"
    except TimeoutError:
        logger.error("OpenAI API timeout")
        return None, None, "api_timeout"
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return None, None, f"api_error: {str(e)}"
