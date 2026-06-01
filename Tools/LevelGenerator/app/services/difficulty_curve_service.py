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
                return {"straight_delivery_intro": 7, "straight_delivery": 2}
            return {
                "straight_delivery_intro": 4,
                "package_before_destination_intro": 4,
                "single_switch_intro": 3,
                "single_switch_wrong_dead_end": 2,
                "straight_delivery": 2,
                "single_switch": 1,
            }
        if difficulty == "easy":
            if level_number <= 5:
                return {
                    "single_switch_package_choice": 5,
                    "safe_dead_end_choice": 3,
                    "short_detour_gate": 2,
                    "single_switch": 1,
                }
            return {
                "single_switch_package_choice": 3,
                "two_switch_order_intro": 4,
                "short_detour_gate": 3,
                "safe_dead_end_choice": 2,
                "package_gate_simple": 4,
                "package_gate": 1,
            }
        if difficulty == "medium":
            if level_number <= 15:
                return {
                    "multi_switch_order": 4,
                    "package_gate_double_choice": 4,
                    "split_path_rejoin": 3,
                    "fake_shortcut": 2,
                    "package_gate": 1,
                }
            return {
                "multi_switch_order": 3,
                "package_gate_double_choice": 3,
                "return_loop_intro": 4,
                "split_path_rejoin": 2,
                "fake_shortcut": 2,
                "hub_choice": 3,
                "return_loop": 1,
            }
        if difficulty == "hard":
            if level_number <= 30:
                return {
                    "two_phase_route": 5,
                    "return_loop_with_gate": 3,
                    "branch_then_rejoin_with_wrong_order": 3,
                    "multi_switch_revisit": 2,
                    "multi_switch_chain": 1,
                }
            return {
                "ring_route_gate": 4,
                "package_inside_loop": 3,
                "multi_switch_revisit": 3,
                "return_loop_with_gate": 2,
                "two_phase_route": 2,
                "ring_route": 1,
            }
        if difficulty == "expert":
            if level_number <= 45:
                return {
                    "four_way_intro": 5,
                    "four_way_package_gate": 4,
                    "controlled_repeated_taps": 3,
                    "four_way_intersection": 1,
                }
            return {
                "four_way_package_gate": 4,
                "four_way_ring": 4,
                "multi_four_way_route": 3,
                "controlled_repeated_taps": 3,
                "late_route_reversal": 3,
                "four_way_intersection": 1,
            }
        return {}
