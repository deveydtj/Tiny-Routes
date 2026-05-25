from __future__ import annotations


def format_level_id(number: int) -> str:
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        raise ValueError("Level number must be a positive integer")
    return f"level_{number:03d}"
