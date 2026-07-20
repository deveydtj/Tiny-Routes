"""Build the legacy decision-profile view from exact V3 strategy evidence."""

from __future__ import annotations

from collections import Counter
from statistics import fmean

from tiny_routes_core.models import LevelDocument

from ..models.decision_profile import DecisionProfile
from ..models.runtime_solution_search import RuntimeSolutionSearchResult
from ..models.static_policy import StaticPolicySearchResult
from ..models.strategy_search import (
    FailureRecoveryReport,
    MeaningfulChoiceOutcomeKind,
    StrategyAction,
    StrategySearchResult,
)
from .failure_recovery_classification_service import (
    FailureRecoveryClassificationService,
)


class ExactDecisionProfileAdapterService:
    """Adapt exact structural proof results to the V2 ``DecisionProfile`` API.

    The adapter deliberately consumes search and classification evidence instead
    of enumerating ``GraphRecipe`` routes. This keeps existing report and scoring
    consumers working while schema-3 generation moves to ordered objectives.
    """

    def __init__(
        self,
        failure_recovery_service: FailureRecoveryClassificationService | None = None,
    ) -> None:
        self.failure_recovery_service = (
            failure_recovery_service or FailureRecoveryClassificationService()
        )

    def adapt(
        self,
        level: LevelDocument,
        strategy_search: StrategySearchResult,
        static_policy_search: StaticPolicySearchResult,
        runtime_solution: RuntimeSolutionSearchResult | None = None,
        *,
        failure_recovery: FailureRecoveryReport | None = None,
    ) -> DecisionProfile:
        report = failure_recovery or self.failure_recovery_service.classify(
            level,
            strategy_search,
        )
        optimal = strategy_search.canonical_optimal_strategy
        actions = optimal.actions if optimal is not None else ()
        decisions = tuple(action for action in actions if action.meaningful_decision)
        decision_counts = Counter(action.node_id for action in decisions)
        repeated_count = sum(count - 1 for count in decision_counts.values())
        revisit_changes = self._switch_state_changes(decisions)
        dependencies = self._ordered_dependencies(decisions)
        independent = max(0, len(decisions) - len(dependencies))
        path = self._visited_path(level, actions)
        windows, tap_times, multi_taps = self._runtime_metrics(runtime_solution)
        classifications = report.classifications
        failure_kinds = tuple(
            item.kind
            for item in classifications
            if not item.canonical_trace.succeeded
        )
        failure_type_names = tuple(
            sorted({self._legacy_failure_name(kind) for kind in failure_kinds})
        )
        opened_edges = {
            edge_id
            for action in actions
            if action.state_transition is not None
            for edge_id in action.state_transition.opened_edge_ids
        }
        closed_edges = {
            edge_id
            for action in actions
            if action.state_transition is not None
            for edge_id in action.state_transition.closed_edge_ids
        }
        objective_transition_count = sum(
            len(action.state_transition.completed_objective_ids)
            for action in actions
            if action.state_transition is not None
        )

        return DecisionProfile(
            required_decision_count=len(decisions),
            unique_switch_count=len(decision_counts),
            repeated_switch_decision_count=repeated_count,
            switch_state_change_on_revisit_count=revisit_changes,
            ordered_dependency_count=len(dependencies),
            independent_decision_ratio=(
                round(independent / len(decisions), 4) if decisions else 0.0
            ),
            equivalent_minimum_solution_count=len(
                strategy_search.equal_cost_optimal_strategies
            ),
            successful_alternate_route_count=sum(
                item.canonical_trace.succeeded for item in classifications
            ),
            failure_route_count=len(failure_kinds),
            failure_outcome_types=failure_type_names,
            dead_end_choice_count=sum(
                kind is MeaningfulChoiceOutcomeKind.IMMEDIATE_DEAD_END
                for kind in failure_kinds
            ),
            destination_before_package_choice_count=sum(
                kind is MeaningfulChoiceOutcomeKind.OBJECTIVE_ORDER_FAILURE
                for kind in failure_kinds
            ),
            recoverable_mistake_count=sum(
                item.kind is MeaningfulChoiceOutcomeKind.RECOVERABLE_DETOUR
                for item in classifications
            ),
            route_revisit_count=self._route_revisit_count(path),
            package_phase_decisions_before=sum(
                self._objective_index(action) == 0 for action in decisions
            ),
            package_phase_decisions_after=sum(
                self._objective_index(action) > 0 for action in decisions
            ),
            package_phase_transition_count=objective_transition_count,
            state_dependent_route_change_count=revisit_changes,
            roads_opened_after_package_count=len(opened_edges),
            roads_closed_after_package_count=len(closed_edges),
            minimum_window_seconds=min(windows) if windows else None,
            average_window_seconds=round(fmean(windows), 4) if windows else None,
            minimum_decision_spacing_seconds=min(self._spacings(tap_times), default=None),
            average_decision_spacing_seconds=(
                round(fmean(self._spacings(tap_times)), 4)
                if len(tap_times) > 1
                else None
            ),
            multiple_taps_in_window_count=multi_taps,
            front_loaded_legacy_solution_possible=bool(
                static_policy_search.successful_policies
            ),
            # Gameplay-equivalent exact traces are collapsed before this view is
            # built, so they cannot be counted as meaningful legacy choices.
            no_op_or_equivalent_choice_count=0,
        )

    @staticmethod
    def _objective_index(action: StrategyAction) -> int:
        transition = action.state_transition
        return transition.objective_index_before if transition is not None else 0

    @classmethod
    def _ordered_dependencies(
        cls,
        actions: tuple[StrategyAction, ...],
    ) -> set[tuple[int, int]]:
        dependencies: set[tuple[int, int]] = set()
        for later, action in enumerate(actions):
            for earlier in range(later):
                previous = actions[earlier]
                if previous.node_id == action.node_id:
                    dependencies.add((earlier, later))
                elif cls._objective_index(previous) != cls._objective_index(action):
                    dependencies.add((earlier, later))
                    break
        return dependencies

    @staticmethod
    def _switch_state_changes(actions: tuple[StrategyAction, ...]) -> int:
        previous_edges: dict[str, str] = {}
        changes = 0
        for action in actions:
            prior = previous_edges.get(action.node_id)
            if prior is not None and prior != action.selected_edge_id:
                changes += 1
            previous_edges[action.node_id] = action.selected_edge_id
        return changes

    @staticmethod
    def _visited_path(
        level: LevelDocument,
        actions: tuple[StrategyAction, ...],
    ) -> tuple[str, ...]:
        return (
            level.startNodeID,
            *(node_id for action in actions for node_id in action.visited_node_ids),
        )

    @staticmethod
    def _route_revisit_count(path: tuple[str, ...]) -> int:
        return sum(count - 1 for count in Counter(path).values() if count > 1)

    @staticmethod
    def _legacy_failure_name(kind: MeaningfulChoiceOutcomeKind) -> str:
        return {
            MeaningfulChoiceOutcomeKind.IMMEDIATE_DEAD_END: "dead_end",
            MeaningfulChoiceOutcomeKind.OBJECTIVE_ORDER_FAILURE: (
                "destination_before_package"
            ),
            MeaningfulChoiceOutcomeKind.LOOP_UNTIL_TIME_EXPIRES: (
                "loop_or_step_limit"
            ),
            MeaningfulChoiceOutcomeKind.STATE_TRAP: "state_trap",
        }[kind]

    @staticmethod
    def _runtime_metrics(
        result: RuntimeSolutionSearchResult | None,
    ) -> tuple[tuple[float, ...], tuple[float, ...], int]:
        if result is None:
            return (), (), 0
        windows = tuple(
            diagnostic.window_close_seconds - diagnostic.window_open_seconds
            for diagnostic in result.diagnostics
            if diagnostic.window_open_seconds is not None
            and diagnostic.window_close_seconds is not None
            and diagnostic.window_close_seconds >= diagnostic.window_open_seconds
        )
        tap_times = tuple(action.time_seconds for action in result.actions)
        multi_taps = sum(
            diagnostic.rotation_count > 1 for diagnostic in result.diagnostics
        )
        return windows, tap_times, multi_taps

    @staticmethod
    def _spacings(times: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(
            round(later - earlier, 4)
            for earlier, later in zip(times, times[1:])
        )
