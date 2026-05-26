from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GenerationQualityScore:
    total: float
    readability: float
    uniqueness: float
    difficulty_fit: float
    route_interest: float
    penalties: tuple[str, ...] = field(default_factory=tuple)
    details: dict[str, float | int | str] = field(default_factory=dict)
