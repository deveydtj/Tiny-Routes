"""Resolve locked V3 production difficulty bands into experience targets."""

from __future__ import annotations

from ..models.puzzle_experience_target import PuzzleExperienceTarget


class DifficultyTargetResolver:
    """Provide immutable targets from the V3 player-experience matrix.

    Tutorial generation is intentionally absent. The production V3 contract
    starts at easy and never permits the zero- or one-decision tutorial shapes
    retained by the legacy generator.
    """

    band_order = ("easy", "medium", "hard", "expert")

    def __init__(self) -> None:
        self._targets = {
            "easy": PuzzleExperienceTarget(
                difficulty="easy",
                objective_count_range=(2, 3),
                meaningful_decision_range=(2, 3),
                planning_decision_minimum=1,
                adaptive_decision_minimum=1,
                dependency_depth_range=(1, 3),
                state_change_range=(1, 2),
                revisit_range=(0, 1),
                successful_route_class_range=(1, 2),
                recoverable_mistake_range=(1, 2),
                fatal_mistake_cap=1,
                decision_window_targets=(2.25, 4.0),
                allowed_mechanic_categories=(
                    "objective_gate",
                    "ordered_checkpoint",
                    "unlock_shortcut",
                    "close_behind",
                    "recoverable_detour",
                    "hub_revisit",
                ),
                layout_complexity_target=0.40,
                desired_solve_time_range=(15.0, 35.0),
            ),
            "medium": PuzzleExperienceTarget(
                difficulty="medium",
                objective_count_range=(3, 4),
                meaningful_decision_range=(3, 5),
                planning_decision_minimum=2,
                adaptive_decision_minimum=1,
                dependency_depth_range=(2, 5),
                state_change_range=(1, 2),
                revisit_range=(1, 2),
                successful_route_class_range=(1, 3),
                recoverable_mistake_range=(1, 3),
                fatal_mistake_cap=2,
                decision_window_targets=(1.80, 4.0),
                allowed_mechanic_categories=(
                    "objective_gate",
                    "ordered_checkpoint",
                    "unlock_shortcut",
                    "close_behind",
                    "recoverable_detour",
                    "hub_revisit",
                    "split_commitment",
                    "route_reversal",
                ),
                layout_complexity_target=0.58,
                desired_solve_time_range=(25.0, 55.0),
            ),
            "hard": PuzzleExperienceTarget(
                difficulty="hard",
                objective_count_range=(3, 5),
                meaningful_decision_range=(5, 7),
                planning_decision_minimum=3,
                adaptive_decision_minimum=2,
                dependency_depth_range=(3, 7),
                state_change_range=(2, 3),
                revisit_range=(1, 3),
                successful_route_class_range=(1, 4),
                recoverable_mistake_range=(2, 4),
                fatal_mistake_cap=2,
                decision_window_targets=(1.45, 4.0),
                allowed_mechanic_categories=(
                    "objective_gate",
                    "ordered_checkpoint",
                    "unlock_shortcut",
                    "close_behind",
                    "recoverable_detour",
                    "hub_revisit",
                    "split_commitment",
                    "route_reversal",
                    "stateful_ring",
                    "delayed_consequence",
                    "competing_routes",
                    "one_use_connector",
                ),
                layout_complexity_target=0.72,
                desired_solve_time_range=(40.0, 85.0),
            ),
            "expert": PuzzleExperienceTarget(
                difficulty="expert",
                objective_count_range=(4, 6),
                meaningful_decision_range=(6, 10),
                planning_decision_minimum=4,
                adaptive_decision_minimum=3,
                dependency_depth_range=(4, 10),
                state_change_range=(3, 5),
                revisit_range=(2, 4),
                successful_route_class_range=(1, 5),
                recoverable_mistake_range=(2, 5),
                fatal_mistake_cap=3,
                decision_window_targets=(1.20, 4.0),
                allowed_mechanic_categories=(
                    "objective_gate",
                    "ordered_checkpoint",
                    "unlock_shortcut",
                    "close_behind",
                    "recoverable_detour",
                    "hub_revisit",
                    "split_commitment",
                    "route_reversal",
                    "stateful_ring",
                    "delayed_consequence",
                    "competing_routes",
                    "one_use_connector",
                    "multi_hub_relay",
                ),
                layout_complexity_target=0.84,
                desired_solve_time_range=(55.0, 120.0),
            ),
        }

    @property
    def valid_names(self) -> list[str]:
        return list(self.band_order)

    def resolve(self, difficulty: str) -> PuzzleExperienceTarget:
        if not isinstance(difficulty, str):
            raise ValueError("difficulty must be a production V3 difficulty name")
        key = difficulty.strip().lower()
        try:
            return self._targets[key]
        except KeyError as exc:
            if key == "tutorial":
                raise ValueError(
                    "tutorial is not a production_v3 difficulty; use v2_legacy "
                    "for tutorial fixtures"
                ) from exc
            raise ValueError(f"Unknown production V3 difficulty target: {difficulty}") from exc

    def get_target(self, difficulty: str) -> PuzzleExperienceTarget:
        """Compatibility spelling for callers that use existing service APIs."""

        return self.resolve(difficulty)


DifficultyTargetResolverService = DifficultyTargetResolver
