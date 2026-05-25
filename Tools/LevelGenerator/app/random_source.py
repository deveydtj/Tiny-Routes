from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


class RandomSource:
    """Small wrapper around random.Random for deterministic generator choices."""

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else 0
        self._random = random.Random(self.seed)

    def randint(self, start: int, end: int) -> int:
        return self._random.randint(start, end)

    def uniform(self, start: float, end: float) -> float:
        return self._random.uniform(start, end)

    def bool(self, probability: float = 0.5) -> bool:
        return self._random.random() < probability

    def choice(self, values: Sequence[T]) -> T:
        if not values:
            raise ValueError("Cannot choose from an empty sequence")
        return self._random.choice(values)

    def weighted_choice(self, weighted_values: Sequence[tuple[T, int | float]]) -> T:
        if not weighted_values:
            raise ValueError("Cannot choose from an empty sequence")
        total = sum(max(weight, 0) for _, weight in weighted_values)
        if total <= 0:
            return weighted_values[0][0]
        target = self._random.uniform(0, total)
        running = 0.0
        for value, weight in weighted_values:
            running += max(weight, 0)
            if target <= running:
                return value
        return weighted_values[-1][0]

    def coordinate(self, minimum: float, maximum: float, grid: float = 0.05) -> float:
        raw = self.uniform(minimum, maximum)
        return round(round(raw / grid) * grid, 4)

    def road_shape(self) -> str:
        return self.choice(["horizontalFirst", "verticalFirst"])

    def child_seed(self, *parts: int | str) -> int:
        value = self.seed & 0xFFFFFFFF
        for part in parts:
            for character in str(part):
                value = ((value * 131) + ord(character)) & 0xFFFFFFFF
        return value
