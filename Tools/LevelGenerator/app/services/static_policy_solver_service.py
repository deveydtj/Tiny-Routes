"""Exhaustive bounded solver for permanent state-oblivious switch policies."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count, product
from math import prod

from tiny_routes_core.graph import GraphIndex
from tiny_routes_core.models import LevelDocument

from ..models.puzzle_state import PuzzleState, PuzzleTerminalOutcome
from ..models.static_policy import (
    StaticPolicyAssignment,
    StaticPolicySearchResult,
    StaticPolicySolution,
)
from ..models.strategy_search import (
    StrategyAction,
    StrategyCost,
    StrategyStateTransition,
    StrategyTrace,
)
from .puzzle_state_transition_service import PuzzleStateTransitionService


@dataclass(frozen=True)
class StaticPolicySearchConfig:
    maximum_policy_assignments: int = 100_000
    maximum_actions_per_policy: int = 128
    movement_speed: float = 1.0

    def __post_init__(self) -> None:
        if self.maximum_policy_assignments < 1:
            raise ValueError("maximum_policy_assignments must be positive")
        if self.maximum_actions_per_policy < 1:
            raise ValueError("maximum_actions_per_policy must be positive")
        if self.movement_speed <= 0:
            raise ValueError("movement_speed must be positive")


class StaticPolicySolverService:
    """Prove whether one fixed outgoing edge per switch can solve a level.

    A policy has no objective phase or visit count in its key. The same authored
    edge must therefore be selected every time its switch is reached. Conditional
    road state may make that selection unavailable, in which case that policy
    fails rather than adapting.
    """

    def __init__(
        self,
        transition_service: PuzzleStateTransitionService | None = None,
    ) -> None:
        self.transition_service = transition_service or PuzzleStateTransitionService()

    def solve(
        self,
        level: LevelDocument,
        *,
        config: StaticPolicySearchConfig | None = None,
    ) -> StaticPolicySearchResult:
        config = config or StaticPolicySearchConfig()
        domains = self._policy_domains(level)
        total_policy_count = prod(len(edges) for _, edges in domains)
        successful: list[StaticPolicySolution] = []
        tested = 0
        limit_reasons: set[str] = set()

        assignments_iter = product(*(edges for _, edges in domains))
        for selected_edges in assignments_iter:
            if tested >= config.maximum_policy_assignments:
                limit_reasons.add("static_policy_assignment_limit_reached")
                break
            assignments = tuple(
                StaticPolicyAssignment(node_id, edge_id)
                for (node_id, _), edge_id in zip(domains, selected_edges, strict=True)
            )
            tested += 1
            trace, action_limited = self._run_policy(level, assignments, config)
            if action_limited:
                limit_reasons.add("static_policy_action_limit_reached")
            if trace.succeeded:
                successful.append(StaticPolicySolution(assignments, trace))

        exhaustive = tested == total_policy_count and not limit_reasons
        return StaticPolicySearchResult(
            successful_policies=tuple(successful),
            tested_policy_count=tested,
            total_policy_count=total_policy_count,
            exhaustive=exhaustive,
            limit_reasons=tuple(limit_reasons),
        )

    # Search is a familiar alias alongside StrategySearchService.search().
    search = solve

    @staticmethod
    def _policy_domains(
        level: LevelDocument,
    ) -> tuple[tuple[str, tuple[str, ...]], ...]:
        index = GraphIndex.build(level.graph)
        return tuple(
            (node.id, tuple(edge.id for edge in index.outgoing_by_node_id[node.id]))
            for node in index.graph.nodes
            if len(index.outgoing_by_node_id[node.id]) >= 2
        )

    def _run_policy(
        self,
        level: LevelDocument,
        assignments: tuple[StaticPolicyAssignment, ...],
        config: StaticPolicySearchConfig,
    ) -> tuple[StrategyTrace, bool]:
        policy = {item.node_id: item.selected_edge_id for item in assignments}
        state = self.transition_service.initial_state(level)
        actions: list[StrategyAction] = []
        cost_value = StrategyCost()
        seen_states: set[tuple[object, ...]] = set()

        if state.terminal_outcome is PuzzleTerminalOutcome.SUCCESS:
            return StrategyTrace((), cost_value, state, "success"), False
        if state.terminal_outcome is PuzzleTerminalOutcome.FAILURE:
            return StrategyTrace((), cost_value, state, "structural_initial_dead_end"), False

        for _ in count():
            policy_state = self._policy_state_key(state)
            if policy_state in seen_states:
                failed = state.evolve(terminal_outcome=PuzzleTerminalOutcome.FAILURE)
                return StrategyTrace(
                    tuple(actions),
                    cost_value,
                    failed,
                    "static_policy_loop",
                ), False
            seen_states.add(policy_state)

            if len(actions) >= config.maximum_actions_per_policy:
                failed = state.evolve(terminal_outcome=PuzzleTerminalOutcome.FAILURE)
                return StrategyTrace(
                    tuple(actions),
                    cost_value,
                    failed,
                    "static_policy_action_limit_reached",
                ), True

            decisions = self.transition_service.available_decisions(level, state)
            if not decisions:
                failed = state.evolve(terminal_outcome=PuzzleTerminalOutcome.FAILURE)
                return StrategyTrace(
                    tuple(actions),
                    cost_value,
                    failed,
                    "structural_dead_end",
                ), False

            desired_edge_id = policy.get(decisions[0].node_id, decisions[0].selected_edge_id)
            decision = next(
                (
                    candidate
                    for candidate in decisions
                    if candidate.selected_edge_id == desired_edge_id
                ),
                None,
            )
            if decision is None:
                failed = state.evolve(terminal_outcome=PuzzleTerminalOutcome.FAILURE)
                return StrategyTrace(
                    tuple(actions),
                    cost_value,
                    failed,
                    "static_policy_selected_edge_unavailable",
                ), False

            transition = self.transition_service.transition(level, state, decision)
            before = state
            state = transition.state
            cost_value = cost_value.adding(
                accepted_taps=decision.tap_count,
                travel_time_seconds=transition.route_distance / config.movement_speed,
                route_distance=transition.route_distance,
            )
            actions.append(
                StrategyAction(
                    node_id=decision.node_id,
                    selected_edge_id=decision.selected_edge_id,
                    tap_count=decision.tap_count,
                    traversed_edge_ids=transition.traversed_edge_ids,
                    visited_node_ids=transition.visited_node_ids,
                    completed_objective_ids=transition.completed_objective_ids,
                    meaningful_decision=len(decisions) >= 2,
                    state_transition=self._observable_state_transition(before, state),
                )
            )
            if state.terminal_outcome is PuzzleTerminalOutcome.SUCCESS:
                return StrategyTrace(tuple(actions), cost_value, state, "success"), False
            if state.terminal_outcome is PuzzleTerminalOutcome.FAILURE:
                return StrategyTrace(
                    tuple(actions),
                    cost_value,
                    state,
                    transition.failure_reason or "structural_dead_end",
                ), False

        raise AssertionError("unreachable static policy loop")

    @staticmethod
    def _policy_state_key(state: PuzzleState) -> tuple[object, ...]:
        """Discard counters that cannot change a permanent policy's behavior."""

        return (
            state.current_node_id,
            state.current_edge_id,
            state.objective_index,
            state.completed_objective_ids,
            state.available_edge_ids,
            state.consumed_edge_ids,
        )

    @staticmethod
    def _observable_state_transition(
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
