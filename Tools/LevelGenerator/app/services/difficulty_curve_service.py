from __future__ import annotations

from ..level_numbering import format_level_id
from ..models.generation_batch_plan import GenerationBatchPlan, GenerationBatchPlanEntry


class DifficultyCurveService:
    def build_plan(self, start_level_number: int, count: int, difficulty: str) -> GenerationBatchPlan:
        entries = []
        for offset in range(count):
            level_number = start_level_number + offset
            resolved_difficulty = (
                self.difficulty_for_level(level_number)
                if difficulty.strip().lower() == "auto"
                else difficulty.strip().lower()
            )
            entries.append(
                GenerationBatchPlanEntry(
                    level_number=level_number,
                    level_id=format_level_id(level_number),
                    difficulty=resolved_difficulty,
                    template_weights=self.template_weights_for_level(level_number, resolved_difficulty),
                )
            )
        return GenerationBatchPlan(entries=tuple(entries))

    def difficulty_for_level(self, level_number: int) -> str:
        if level_number <= 3:
            return "tutorial"
        if level_number <= 10:
            return "easy"
        if level_number <= 25:
            return "medium"
        if level_number <= 40:
            return "hard"
        return "expert"

    def template_weights_for_level(self, level_number: int, difficulty: str) -> dict[str, int]:
        if difficulty == "tutorial":
            if level_number <= 1:
                return {"straight_delivery": 7}
            return {"straight_delivery": 5, "single_switch": 2}
        if difficulty == "easy":
            if level_number <= 5:
                return {"single_switch": 5, "package_gate": 1}
            return {"single_switch": 4, "package_gate": 3}
        if difficulty == "medium":
            if level_number <= 15:
                return {"package_gate": 5, "multi_switch_chain": 2}
            return {"package_gate": 2, "multi_switch_chain": 4, "return_loop": 3}
        if difficulty == "hard":
            if level_number <= 30:
                return {"multi_switch_chain": 5, "return_loop": 2, "ring_route": 1}
            return {"multi_switch_chain": 4, "return_loop": 1, "ring_route": 3}
        if difficulty == "expert":
            if level_number <= 45:
                return {"four_way_intersection": 3, "multi_switch_chain": 3, "ring_route": 2}
            return {"four_way_intersection": 5, "multi_switch_chain": 2, "ring_route": 2}
        return {}
