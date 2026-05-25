from __future__ import annotations

from app.random_source import RandomSource


def test_same_seed_produces_same_sequence() -> None:
    first = RandomSource(123)
    second = RandomSource(123)

    assert [first.randint(1, 10) for _ in range(5)] == [second.randint(1, 10) for _ in range(5)]
    assert first.child_seed("easy", "single_switch", 12) == second.child_seed("easy", "single_switch", 12)
