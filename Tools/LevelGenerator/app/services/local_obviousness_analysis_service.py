"""Reject strategies whose meaningful choices all follow simple local rules."""

from __future__ import annotations

import math

from tiny_routes_core.graph import GraphIndex
from tiny_routes_core.models import LevelDocument

from ..models.local_obviousness import (
    LocalObviousnessDecision,
    LocalObviousnessKind,
    LocalObviousnessReport,
)
from ..models.puzzle_state import PuzzleState, PuzzleTerminalOutcome
from ..models.strategy_search import StrategySearchResult
from .puzzle_state_transition_service import (
    PuzzleStateTransitionService,
    StructuralDecision,
)
from .strategy_search_service import StrategySearchConfig, StrategySearchService


_EPSILON = 1e-9
_DIRECTION_VECTORS: tuple[tuple[str, tuple[float, float]], ...] = (
    ("north", (0.0, 1.0)),
    ("east", (1.0, 0.0)),
    ("south", (0.0, -1.0)),
    ("west", (-1.0, 0.0)),
)


class LocalObviousnessAnalysisService:
    """Assess every meaningful action on an exhaustive optimal trace."""

    def __init__(
        self,
        *,
        transition_service: PuzzleStateTransitionService | None = None,
        search_service: StrategySearchService | None = None,
    ) -> None:
        self._transitions = transition_service or PuzzleStateTransitionService()
        self._search = search_service or StrategySearchService(
            transition_service=self._transitions,
        )

    def assess(
        self,
        level: LevelDocument,
        search_result: StrategySearchResult | None = None,
        *,
        search_config: StrategySearchConfig | None = None,
    ) -> LocalObviousnessReport:
        initial_state = self._transitions.initial_state(level)
        proof = search_result or self._search.search(
            level,
            initial_state=initial_state,
            config=search_config,
        )
        self._require_optimum(proof)
        trace = proof.canonical_optimal_strategy
        assert trace is not None
        index = GraphIndex.build(level.graph)
        replay = self._replay(level, initial_state, proof)
        meaningful = tuple(item for item in replay if len(item[2]) >= 2)
        fixed_directions = self._successful_fixed_directions(index, meaningful)
        decisions = tuple(
            self._classify_decision(
                level,
                index,
                ordinal,
                state,
                optimal,
                actions,
                incoming_edge_id,
                fixed_directions,
            )
            for ordinal, state, actions, optimal, incoming_edge_id in meaningful
        )
        all_obvious = bool(decisions) and all(
            decision.is_locally_obvious for decision in decisions
        )
        if not decisions:
            reasons = ("local_obviousness_no_meaningful_decisions",)
        elif all_obvious:
            reasons = ("all_optimal_decisions_locally_obvious",)
        else:
            reasons = ()
        return LocalObviousnessReport(
            level_id=level.id,
            decisions=decisions,
            successful_fixed_direction_rules=fixed_directions,
            strategy_proof_exhaustive=proof.exhaustive,
            accepted=not reasons,
            rejection_reasons=reasons,
        )

    def _classify_decision(
        self,
        level: LevelDocument,
        index: GraphIndex,
        ordinal: int,
        state: PuzzleState,
        optimal: StructuralDecision,
        actions: tuple[StructuralDecision, ...],
        incoming_edge_id: str | None,
        fixed_directions: tuple[str, ...],
    ) -> LocalObviousnessDecision:
        rules: list[LocalObviousnessKind] = []
        if self._uniquely_closest_to_objective(level, index, state, actions) == optimal.selected_edge_id:
            rules.append(LocalObviousnessKind.EUCLIDEAN_OBJECTIVE_CLOSENESS)
        if self._only_non_dead_end(level, state, actions) == optimal.selected_edge_id:
            rules.append(LocalObviousnessKind.ONLY_NON_DEAD_END_ROAD)
        if self._only_non_backward(index, actions, incoming_edge_id) == optimal.selected_edge_id:
            rules.append(LocalObviousnessKind.ONLY_NON_BACKWARD_ROAD)
        if actions[0].selected_edge_id == optimal.selected_edge_id:
            rules.append(LocalObviousnessKind.FIRST_OUTGOING_EDGE)
        if fixed_directions:
            rules.append(LocalObviousnessKind.FIXED_DIRECTION_RULE)
        return LocalObviousnessDecision(
            decision_ordinal=ordinal,
            objective_index=state.objective_index,
            node_id=optimal.node_id,
            optimal_edge_id=optimal.selected_edge_id,
            matched_rules=tuple(rules),
        )

    @staticmethod
    def _uniquely_closest_to_objective(
        level: LevelDocument,
        index: GraphIndex,
        state: PuzzleState,
        actions: tuple[StructuralDecision, ...],
    ) -> str | None:
        objectives = sorted(level.effective_objectives, key=lambda item: item.sequenceIndex)
        if state.objective_index >= len(objectives):
            return None
        objective_node = index.nodes_by_id.get(objectives[state.objective_index].nodeID)
        if objective_node is None:
            return None
        distances = tuple(
            (
                action.selected_edge_id,
                math.hypot(
                    index.nodes_by_id[index.edges_by_id[action.selected_edge_id].toNodeID].x
                    - objective_node.x,
                    index.nodes_by_id[index.edges_by_id[action.selected_edge_id].toNodeID].y
                    - objective_node.y,
                ),
            )
            for action in actions
        )
        minimum = min(distance for _, distance in distances)
        closest = tuple(edge_id for edge_id, distance in distances if abs(distance - minimum) <= _EPSILON)
        return closest[0] if len(closest) == 1 else None

    def _only_non_dead_end(
        self,
        level: LevelDocument,
        state: PuzzleState,
        actions: tuple[StructuralDecision, ...],
    ) -> str | None:
        viable = tuple(
            action.selected_edge_id
            for action in actions
            if self._transitions.transition(level, state, action).state.terminal_outcome
            is not PuzzleTerminalOutcome.FAILURE
        )
        return viable[0] if len(viable) == 1 else None

    @staticmethod
    def _only_non_backward(
        index: GraphIndex,
        actions: tuple[StructuralDecision, ...],
        incoming_edge_id: str | None,
    ) -> str | None:
        if incoming_edge_id is None:
            return None
        incoming = index.edges_by_id.get(incoming_edge_id)
        if incoming is None:
            return None
        previous = index.nodes_by_id[incoming.fromNodeID]
        current = index.nodes_by_id[incoming.toNodeID]
        incoming_vector = (current.x - previous.x, current.y - previous.y)
        if math.hypot(*incoming_vector) <= _EPSILON:
            return None
        non_backward: list[str] = []
        for action in actions:
            edge = index.edges_by_id[action.selected_edge_id]
            destination = index.nodes_by_id[edge.toNodeID]
            outgoing_vector = (destination.x - current.x, destination.y - current.y)
            dot = (
                incoming_vector[0] * outgoing_vector[0]
                + incoming_vector[1] * outgoing_vector[1]
            )
            if dot >= -_EPSILON:
                non_backward.append(action.selected_edge_id)
        return non_backward[0] if len(non_backward) == 1 else None

    @staticmethod
    def _successful_fixed_directions(
        index: GraphIndex,
        meaningful: tuple[
            tuple[
                int,
                PuzzleState,
                tuple[StructuralDecision, ...],
                StructuralDecision,
                str | None,
            ],
            ...,
        ],
    ) -> tuple[str, ...]:
        successful: list[str] = []
        for name, direction in _DIRECTION_VECTORS:
            if all(
                LocalObviousnessAnalysisService._unique_direction_choice(
                    index,
                    actions,
                    direction,
                )
                == optimal.selected_edge_id
                for _, _, actions, optimal, _ in meaningful
            ):
                successful.append(name)
        return tuple(successful) if meaningful else ()

    @staticmethod
    def _unique_direction_choice(
        index: GraphIndex,
        actions: tuple[StructuralDecision, ...],
        direction: tuple[float, float],
    ) -> str | None:
        scores: list[tuple[str, float]] = []
        for action in actions:
            edge = index.edges_by_id[action.selected_edge_id]
            source = index.nodes_by_id[edge.fromNodeID]
            destination = index.nodes_by_id[edge.toNodeID]
            scores.append(
                (
                    action.selected_edge_id,
                    (destination.x - source.x) * direction[0]
                    + (destination.y - source.y) * direction[1],
                )
            )
        maximum = max(score for _, score in scores)
        winners = tuple(edge_id for edge_id, score in scores if abs(score - maximum) <= _EPSILON)
        return winners[0] if len(winners) == 1 else None

    def _replay(
        self,
        level: LevelDocument,
        initial_state: PuzzleState,
        proof: StrategySearchResult,
    ) -> tuple[
        tuple[
            int,
            PuzzleState,
            tuple[StructuralDecision, ...],
            StructuralDecision,
            str | None,
        ],
        ...,
    ]:
        trace = proof.canonical_optimal_strategy
        assert trace is not None
        state = initial_state
        incoming_edge_id: str | None = None
        result = []
        for ordinal, strategy_action in enumerate(trace.actions):
            actions = self._transitions.available_actions(level, state)
            optimal = next(
                (
                    action
                    for action in actions
                    if action.selected_edge_id == strategy_action.selected_edge_id
                ),
                None,
            )
            if optimal is None:
                raise ValueError("optimal strategy contains a non-visible decision")
            result.append((ordinal, state, actions, optimal, incoming_edge_id))
            transition = self._transitions.transition(level, state, optimal)
            incoming_edge_id = (
                transition.traversed_edge_ids[-1]
                if transition.traversed_edge_ids
                else None
            )
            state = transition.state
        if state != trace.final_state:
            raise ValueError("optimal strategy cannot be replayed for local-obviousness analysis")
        return tuple(result)

    @staticmethod
    def _require_optimum(result: StrategySearchResult) -> None:
        if not result.exhaustive:
            raise ValueError("local-obviousness analysis requires an exhaustive proof")
        if result.canonical_optimal_strategy is None:
            raise ValueError("local-obviousness analysis requires a successful strategy")

    analyze = assess
    gate = assess


LocalObviousnessService = LocalObviousnessAnalysisService
