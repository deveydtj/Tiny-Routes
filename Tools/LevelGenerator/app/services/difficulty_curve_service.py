from __future__ import annotations

from ..level_numbering import format_level_id
from ..models.generation_batch_plan import GenerationBatchPlan, GenerationBatchPlanEntry


class DifficultyCurveService:
    """Defines mechanic unlocks before timing pressure increases."""

    def build_plan(
        self,
        start_level_number: int,
        count: int,
        difficulty: str,
    ) -> GenerationBatchPlan:
        normalized_difficulty = difficulty.strip().lower()
        entries = []
        for offset in range(count):
            level_number = start_level_number + offset
            if normalized_difficulty == "auto":
                resolved_difficulty = self.difficulty_for_level(level_number)
            elif normalized_difficulty == "progressive":
                resolved_difficulty = self.production_difficulty_for_level(
                    level_number
                )
            else:
                resolved_difficulty = normalized_difficulty
            entries.append(
                GenerationBatchPlanEntry(
                    level_number=level_number,
                    level_id=format_level_id(level_number),
                    difficulty=resolved_difficulty,
                    template_weights=self.template_weights_for_level(level_number, resolved_difficulty),
                )
            )
        return GenerationBatchPlan(entries=tuple(entries))

    def production_difficulty_for_level(self, level_number: int) -> str:
        """Return the V3 band for a campaign position, starting safely at easy."""

        if level_number <= 10:
            return "easy"
        if level_number <= 25:
            return "medium"
        if level_number <= 40:
            return "hard"
        return "expert"

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
            if level_number == 2:
                return {
                    "package_before_destination_intro": 7,
                    "straight_delivery_intro": 2,
                }
            return {
                "single_switch_intro": 7,
                "package_before_destination_intro": 2,
                "single_switch_wrong_dead_end": 2,
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
            weights = {
                "ring_route_gate": 4,
                "package_inside_loop": 3,
                "multi_switch_revisit": 3,
                "return_loop_with_gate": 2,
                "two_phase_route": 2,
                "ring_route": 1,
            }
            # Level 36 is deliberately less punitive after the first late-hard
            # run, giving players space to consolidate the new state patterns.
            if level_number % 6 == 0:
                weights.update({"two_phase_route": 6, "ring_route_gate": 2})
            return weights
        if difficulty == "expert":
            if level_number <= 45:
                return {
                    "four_way_intro": 5,
                    "four_way_package_gate": 4,
                    "controlled_repeated_taps": 3,
                    "four_way_intersection": 1,
                }
            weights = {
                "four_way_package_gate": 4,
                "four_way_ring": 4,
                "multi_four_way_route": 3,
                "controlled_repeated_taps": 3,
                "late_route_reversal": 3,
                "four_way_intersection": 1,
            }
            # Regular recovery beats retain state complexity while easing the
            # densest repeated-tap/four-way combinations.
            if level_number % 5 == 0:
                weights.update({"four_way_package_gate": 6, "multi_four_way_route": 1})
            return weights
        return {}
