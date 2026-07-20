"""Feasibility pruning for partial V3 puzzle compositions."""

from __future__ import annotations

from collections import Counter

from ..models.composition_pruning import (
    CompositionPruningAssessment,
    CompositionStrategicConstraints,
)
from ..models.composition_state import CompositionState


class CompositionStrategicPruningService:
    """Reject branches that already violate or can no longer reach hard bounds."""

    def __init__(self, constraints: CompositionStrategicConstraints) -> None:
        if not isinstance(constraints, CompositionStrategicConstraints):
            raise TypeError("constraints must be CompositionStrategicConstraints")
        self.constraints = constraints

    def assess(self, state: CompositionState) -> CompositionPruningAssessment:
        if not isinstance(state, CompositionState):
            raise TypeError("state must be a CompositionState")
        if state.blueprint_id != self.constraints.blueprint_id:
            return CompositionPruningAssessment(
                (
                    "composition_prune_blueprint_mismatch:"
                    f"{state.blueprint_id}:{self.constraints.blueprint_id}",
                )
            )

        reasons: list[str] = []
        remaining_ids = set(state.unfulfilled_decision_ids)
        remaining_count = len(remaining_ids)
        metrics = state.partial_strategic_metrics

        self._check_reachable_range(
            reasons,
            "meaningful_decision",
            metrics.meaningful_decision_count,
            metrics.meaningful_decision_count + remaining_count,
            self.constraints.meaningful_decision_range,
            state.is_complete,
        )
        remaining_adaptive = len(
            remaining_ids.intersection(self.constraints.adaptive_decision_ids)
        )
        self._check_minimum(
            reasons,
            "adaptive_decision",
            metrics.adaptive_decision_count,
            metrics.adaptive_decision_count + remaining_adaptive,
            self.constraints.adaptive_decision_minimum,
            state.is_complete,
        )
        self._check_reachable_range(
            reasons,
            "dependency_depth",
            metrics.dependency_depth,
            metrics.dependency_depth + remaining_count,
            self.constraints.dependency_depth_range,
            state.is_complete,
        )
        remaining_revisits = len(
            remaining_ids.intersection(self.constraints.revisit_decision_ids)
        )
        self._check_reachable_range(
            reasons,
            "revisit",
            metrics.revisit_count,
            metrics.revisit_count + remaining_revisits,
            self.constraints.revisit_range,
            state.is_complete,
        )
        self._check_reachable_range(
            reasons,
            "recovery",
            metrics.recovery_count,
            metrics.recovery_count + remaining_count,
            self.constraints.recovery_range,
            state.is_complete,
        )

        bound_objectives = sum(
            boundary.entry_node_id is not None and boundary.exit_node_id is not None
            for boundary in state.objective_phase_boundaries
        )
        self._check_reachable_range(
            reasons,
            "objective_count",
            bound_objectives,
            len(state.objective_phase_boundaries),
            self.constraints.objective_count_range,
            state.is_complete,
        )

        maximum_future_switches = (
            state.switch_count
            + remaining_count
            * self.constraints.maximum_switches_per_remaining_decision
        )
        self._check_reachable_range(
            reasons,
            "switch_count",
            state.switch_count,
            maximum_future_switches,
            self.constraints.switch_count_range,
            state.is_complete,
        )
        outgoing = Counter(edge.from_node_id for edge in state.current_graph.edges)
        maximum_degree = max(outgoing.values(), default=0)
        if maximum_degree > self.constraints.maximum_switch_degree:
            reasons.append(
                "composition_prune_switch_degree_max_exceeded:"
                f"{maximum_degree}:{self.constraints.maximum_switch_degree}"
            )

        self._check_layout_dimension(
            reasons,
            "layout_width",
            state.estimated_layout_footprint.width,
            self.constraints.layout_width_range,
            state.is_complete,
        )
        self._check_layout_dimension(
            reasons,
            "layout_height",
            state.estimated_layout_footprint.height,
            self.constraints.layout_height_range,
            state.is_complete,
        )
        return CompositionPruningAssessment(tuple(reasons))

    def rejection_reasons(self, state: CompositionState) -> tuple[str, ...]:
        """Callback shape consumed directly by composition backtracking."""

        return self.assess(state).rejection_reasons

    @staticmethod
    def _check_reachable_range(
        reasons: list[str],
        name: str,
        current: int,
        reachable_maximum: int,
        target: tuple[int, int],
        complete: bool,
    ) -> None:
        minimum, maximum = target
        if current > maximum:
            reasons.append(
                f"composition_prune_{name}_max_exceeded:{current}:{maximum}"
            )
        if reachable_maximum < minimum:
            reasons.append(
                f"composition_prune_{name}_minimum_unreachable:"
                f"{reachable_maximum}:{minimum}"
            )
        elif complete and current < minimum:
            reasons.append(
                f"composition_prune_{name}_minimum_not_met:{current}:{minimum}"
            )

    @staticmethod
    def _check_minimum(
        reasons: list[str],
        name: str,
        current: int,
        reachable_maximum: int,
        minimum: int,
        complete: bool,
    ) -> None:
        if reachable_maximum < minimum:
            reasons.append(
                f"composition_prune_{name}_minimum_unreachable:"
                f"{reachable_maximum}:{minimum}"
            )
        elif complete and current < minimum:
            reasons.append(
                f"composition_prune_{name}_minimum_not_met:{current}:{minimum}"
            )

    @staticmethod
    def _check_layout_dimension(
        reasons: list[str],
        name: str,
        current: int,
        target: tuple[int, int],
        complete: bool,
    ) -> None:
        minimum, maximum = target
        if current > maximum:
            reasons.append(
                f"composition_prune_{name}_max_exceeded:{current}:{maximum}"
            )
        elif complete and current < minimum:
            reasons.append(
                f"composition_prune_{name}_minimum_not_met:{current}:{minimum}"
            )
