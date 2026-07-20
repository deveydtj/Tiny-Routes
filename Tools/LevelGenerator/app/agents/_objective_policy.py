"""Shared visible-map helpers for objective-directed policy agents."""

from __future__ import annotations

import math

from tiny_routes_core.graph import GraphIndex
from tiny_routes_core.models import LevelDocument

from ..models.puzzle_state import PuzzleState
from ..services.puzzle_state_transition_service import StructuralDecision


class ObjectivePolicyContext:
    """A stable projection of the authored map used by heuristic agents.

    Tiny Routes displays the road graph, node positions, and ordered current
    objective to the player. This helper exposes only those map facts and the
    canonical visible puzzle state; it never reads an embedded solution.
    """

    def __init__(self, level: LevelDocument) -> None:
        self.level = level.clone()
        self.index = GraphIndex.build(self.level.graph)
        self.objectives = tuple(
            sorted(
                self.level.effective_objectives,
                key=lambda objective: objective.sequenceIndex,
            )
        )

    def remaining_objective_count(self, state: PuzzleState) -> int:
        return max(0, len(self.objectives) - state.objective_index)

    def distance_to_current_objective(
        self,
        state: PuzzleState,
        *,
        node_id: str | None = None,
    ) -> float:
        if state.objective_index >= len(self.objectives):
            return 0.0
        position_node_id = node_id if node_id is not None else state.current_node_id
        if position_node_id is None:
            return math.inf
        objective = self.objectives[state.objective_index]
        return self._distance(position_node_id, objective.nodeID)

    def action_endpoint_distance(
        self,
        state: PuzzleState,
        action: StructuralDecision,
    ) -> float:
        edge = self.index.edges_by_id.get(action.selected_edge_id)
        if edge is None or edge.fromNodeID != action.node_id:
            raise ValueError("the observed action does not belong to the policy map")
        return self.distance_to_current_objective(state, node_id=edge.toNodeID)

    def _distance(self, first_node_id: str, second_node_id: str) -> float:
        try:
            first = self.index.nodes_by_id[first_node_id]
            second = self.index.nodes_by_id[second_node_id]
        except KeyError as error:
            raise ValueError(
                f"the policy map references unknown node '{error.args[0]}'"
            ) from error
        return math.hypot(second.x - first.x, second.y - first.y)
