"""Deterministic weighted search for canonical structural strategies."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from itertools import count

from tiny_routes_core.models import LevelDocument

from ..models.puzzle_state import PuzzleState, PuzzleTerminalOutcome
from ..models.strategy_search import (
    StrategyAction,
    StrategyCost,
    StrategySearchResult,
    StrategyStateTransition,
    StrategyTrace,
)
from .puzzle_state_transition_service import PuzzleStateTransitionService
from .strategy_equivalence_service import StrategyEquivalenceService


@dataclass(frozen=True)
class StrategySearchConfig:
    maximum_explored_states: int = 50_000
    maximum_actions_per_strategy: int = 64
    near_optimal_tap_margin: int = 2
    near_optimal_time_margin_seconds: float | None = None
    movement_speed: float = 1.0

    def __post_init__(self) -> None:
        if self.maximum_explored_states < 1:
            raise ValueError("maximum_explored_states must be positive")
        if self.maximum_actions_per_strategy < 1:
            raise ValueError("maximum_actions_per_strategy must be positive")
        if self.near_optimal_tap_margin < 0:
            raise ValueError("near_optimal_tap_margin must be non-negative")
        if self.near_optimal_time_margin_seconds is not None and self.near_optimal_time_margin_seconds < 0:
            raise ValueError("near_optimal_time_margin_seconds must be non-negative")
        if self.movement_speed <= 0:
            raise ValueError("movement_speed must be positive")


class StrategySearchService:
    """Run Dijkstra search using the locked tap/time/distance cost order."""

    def __init__(
        self,
        transition_service: PuzzleStateTransitionService | None = None,
        equivalence_service: StrategyEquivalenceService | None = None,
    ) -> None:
        self.transition_service = transition_service or PuzzleStateTransitionService()
        self.equivalence_service = equivalence_service or StrategyEquivalenceService()

    def search(
        self,
        level: LevelDocument,
        *,
        initial_state: PuzzleState | None = None,
        config: StrategySearchConfig | None = None,
    ) -> StrategySearchResult:
        config = config or StrategySearchConfig()
        start = initial_state or self.transition_service.initial_state(level)
        if start.terminal_outcome is PuzzleTerminalOutcome.SUCCESS:
            trace = StrategyTrace((), StrategyCost(), start, "success")
            return StrategySearchResult(
                StrategyCost(), trace, (trace,), (), (), (), 1, True, ()
            )
        if start.terminal_outcome is PuzzleTerminalOutcome.FAILURE:
            trace = StrategyTrace((), StrategyCost(), start, "structural_initial_dead_end")
            return StrategySearchResult(
                None, None, (), (), (), (trace,), 1, True, ()
            )

        serial = count()
        queue: list[
            tuple[
                StrategyCost,
                tuple[tuple[object, ...], ...],
                int,
                PuzzleState,
                tuple[StrategyAction, ...],
            ]
        ] = []
        heapq.heappush(queue, (StrategyCost(), (), next(serial), start, ()))
        best_cost_by_state: dict[PuzzleState, StrategyCost] = {start: StrategyCost()}
        queued_trace_signatures: set[tuple[PuzzleState, tuple[tuple[object, ...], ...]]] = {
            (start, ())
        }
        successes: list[StrategyTrace] = []
        failures: list[StrategyTrace] = []
        explored = 0
        limit_reasons: set[str] = set()

        while queue:
            if explored >= config.maximum_explored_states:
                limit_reasons.add("strategy_state_limit_reached")
                break
            cost_value, _, _, state, actions = heapq.heappop(queue)
            if cost_value > best_cost_by_state.get(state, cost_value):
                continue
            explored += 1
            decisions = self.transition_service.available_decisions(level, state)
            if not decisions:
                failed_state = state.evolve(terminal_outcome=PuzzleTerminalOutcome.FAILURE)
                failures.append(
                    StrategyTrace(actions, cost_value, failed_state, "structural_dead_end")
                )
                continue
            if len(actions) >= config.maximum_actions_per_strategy:
                limit_reasons.add("strategy_action_limit_reached")
                failed_state = state.evolve(terminal_outcome=PuzzleTerminalOutcome.FAILURE)
                failures.append(
                    StrategyTrace(actions, cost_value, failed_state, "strategy_action_limit_reached")
                )
                continue

            for decision in decisions:
                transition = self.transition_service.transition(level, state, decision)
                added_time = transition.route_distance / config.movement_speed
                next_cost = cost_value.adding(
                    accepted_taps=decision.tap_count,
                    travel_time_seconds=added_time,
                    route_distance=transition.route_distance,
                )
                action = StrategyAction(
                    node_id=decision.node_id,
                    selected_edge_id=decision.selected_edge_id,
                    tap_count=decision.tap_count,
                    traversed_edge_ids=transition.traversed_edge_ids,
                    visited_node_ids=transition.visited_node_ids,
                    completed_objective_ids=transition.completed_objective_ids,
                    meaningful_decision=len(decisions) >= 2,
                    state_transition=self._state_transition(state, transition.state),
                )
                next_actions = (*actions, action)
                outcome_code = transition.failure_reason or (
                    "success"
                    if transition.state.terminal_outcome is PuzzleTerminalOutcome.SUCCESS
                    else "active"
                )
                trace = StrategyTrace(next_actions, next_cost, transition.state, outcome_code)
                if transition.state.terminal_outcome is PuzzleTerminalOutcome.SUCCESS:
                    successes.append(trace)
                    continue
                if transition.state.terminal_outcome is PuzzleTerminalOutcome.FAILURE:
                    failures.append(trace)
                    continue

                previous_best = best_cost_by_state.get(transition.state)
                if previous_best is not None and next_cost > previous_best:
                    continue
                if previous_best is None or next_cost < previous_best:
                    best_cost_by_state[transition.state] = next_cost
                signature = trace.signature
                queue_key = (transition.state, signature)
                if queue_key in queued_trace_signatures:
                    continue
                queued_trace_signatures.add(queue_key)
                heapq.heappush(
                    queue,
                    (next_cost, signature, next(serial), transition.state, next_actions),
                )

        if queue:
            limit_reasons.add("strategy_search_incomplete")

        successes = self._unique_sorted(level, successes)
        failures = self._unique_sorted(level, failures)
        if not successes:
            return StrategySearchResult(
                optimal_cost=None,
                canonical_optimal_strategy=None,
                equal_cost_optimal_strategies=(),
                near_optimal_strategies=(),
                longer_successful_strategies=(),
                failure_outcomes=tuple(failures),
                explored_state_count=explored,
                exhaustive=not limit_reasons,
                limit_reasons=tuple(sorted(limit_reasons)),
            )

        optimal_cost = successes[0].cost
        equal = tuple(trace for trace in successes if trace.cost == optimal_cost)
        remaining = tuple(trace for trace in successes if trace.cost != optimal_cost)
        near = tuple(
            trace
            for trace in remaining
            if self._is_near_optimal(trace.cost, optimal_cost, config)
        )
        near_signatures = {trace.signature for trace in near}
        longer = tuple(trace for trace in remaining if trace.signature not in near_signatures)
        return StrategySearchResult(
            optimal_cost=optimal_cost,
            canonical_optimal_strategy=equal[0],
            equal_cost_optimal_strategies=equal,
            near_optimal_strategies=near,
            longer_successful_strategies=longer,
            failure_outcomes=tuple(failures),
            explored_state_count=explored,
            exhaustive=not limit_reasons,
            limit_reasons=tuple(sorted(limit_reasons)),
        )

    def _unique_sorted(
        self,
        level: LevelDocument,
        traces: list[StrategyTrace],
    ) -> list[StrategyTrace]:
        return [
            strategy_class.canonical_trace
            for strategy_class in self.equivalence_service.classify(traces, level=level)
        ]

    @staticmethod
    def _state_transition(
        before: PuzzleState,
        after: PuzzleState,
    ) -> StrategyStateTransition:
        available_before = set(before.available_edge_ids)
        available_after = set(after.available_edge_ids)
        newly_consumed = set(after.consumed_edge_ids).difference(before.consumed_edge_ids)
        return StrategyStateTransition(
            objective_index_before=before.objective_index,
            objective_index_after=after.objective_index,
            completed_objective_ids=tuple(
                objective_id
                for objective_id in after.completed_objective_ids
                if objective_id not in before.completed_objective_ids
            ),
            opened_edge_ids=tuple(sorted(available_after.difference(available_before))),
            closed_edge_ids=tuple(
                sorted(available_before.difference(available_after, newly_consumed))
            ),
            consumed_edge_ids=tuple(sorted(newly_consumed)),
        )

    @staticmethod
    def _is_near_optimal(
        cost_value: StrategyCost,
        optimal: StrategyCost,
        config: StrategySearchConfig,
    ) -> bool:
        if cost_value.accepted_taps > optimal.accepted_taps + config.near_optimal_tap_margin:
            return False
        margin = config.near_optimal_time_margin_seconds
        return margin is None or cost_value.travel_time_seconds <= optimal.travel_time_seconds + margin
