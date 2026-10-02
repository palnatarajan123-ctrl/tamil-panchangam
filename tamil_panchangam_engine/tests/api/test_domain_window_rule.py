# tests/api/test_domain_window_rule.py
"""
Regression for the 2026-10-01 cross-domain window bug: with no wealth
windows in context, chat.py presented the 7th-lord (marriage) Venus window
as a financial window and family.py presented the 6th-lord (health) Mercury
window as a "financial breakthrough" window. Both chat implementations must
carry the same domain-window rule (one shared constant, not two copies).
"""
from app.api.chat import DOMAIN_WINDOW_RULE, SYSTEM_PROMPT_TEMPLATE
from app.api.family import _FAMILY_CHAT_SYSTEM_PROMPT


def test_chat_prompt_carries_domain_window_rule():
    assert DOMAIN_WINDOW_RULE in SYSTEM_PROMPT_TEMPLATE


def test_family_prompt_carries_same_domain_window_rule():
    assert DOMAIN_WINDOW_RULE in _FAMILY_CHAT_SYSTEM_PROMPT


def test_rule_forbids_signification_stretching():
    assert "general significations" in DOMAIN_WINDOW_RULE


def test_rule_has_no_format_braces():
    # Concatenated into templates that are later .format()-ed.
    assert "{" not in DOMAIN_WINDOW_RULE and "}" not in DOMAIN_WINDOW_RULE
