from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GenerationBatchPlanEntry:
    level_number: int
    level_id: str
    difficulty: str
    template_weights: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationBatchPlan:
    entries: tuple[GenerationBatchPlanEntry, ...]
