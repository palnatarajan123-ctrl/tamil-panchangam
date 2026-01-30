"""Canonical PDF Report Builder - Single authoritative report pipeline."""

from .report_builder import build_canonical_report
from .config import REPORT_VERSION, PROMPT_VERSION

__all__ = ["build_canonical_report", "REPORT_VERSION", "PROMPT_VERSION"]
