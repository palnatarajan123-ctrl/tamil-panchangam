import hashlib
import json

def compute_chart_checksum(chart: dict) -> str:
    """
    Deterministic checksum for immutable base chart
    """
    canonical = json.dumps(chart, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
