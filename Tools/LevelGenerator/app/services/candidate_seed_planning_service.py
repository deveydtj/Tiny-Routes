from __future__ import annotations

from ..random_source import RandomSource


class CandidateSeedPlanningService:
    """Derives deterministic stage seeds without coupling stages to the batch loop."""

    def __init__(self, base_seed: int) -> None:
        self._base = RandomSource(base_seed)

    def candidate_seed(
        self, difficulty: str, template_name: str | None, level_id: str, attempt: int
    ) -> int:
        return self._base.child_seed(difficulty, template_name, level_id, attempt)

    def map_seed(self, level_id: str, attempt: int, candidate_index: int) -> int:
        return self._base.child_seed(level_id, attempt, candidate_index, "map")
