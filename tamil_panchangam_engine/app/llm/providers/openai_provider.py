# app/llm/providers/openai_provider.py
"""
Backward-compatibility shim.

All logic has moved to anthropic_provider.py.
This module re-exports everything so existing imports keep working.
"""

from app.llm.providers.anthropic_provider import (  # noqa: F401
    MODEL,
    PROVIDER_NAME,
    is_available,
    get_provider_info,
    call_llm,
    call_openai,
)
