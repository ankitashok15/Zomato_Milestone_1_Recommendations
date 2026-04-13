from __future__ import annotations

import hashlib


def assign_variant(subject_id: str, rollout_b_percent: int = 50) -> str:
    rollout_b_percent = max(0, min(100, rollout_b_percent))
    digest = hashlib.sha256(subject_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return "B" if bucket < rollout_b_percent else "A"
