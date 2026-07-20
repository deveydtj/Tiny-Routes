"""Schema-aware structural transitions over canonical V3 puzzle states."""

from __future__ import annotations

import math
from dataclasses import dataclass

from tiny_routes_core.graph import GraphIndex
from tiny_routes_core.models import LevelDocument, RouteEdge, RouteObjectiveKind

from ..models.puzzle_state import PuzzleState, PuzzleTerminalOutcome


class PuzzleStateTransitionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class StructuralDecision:
    """A road selection at the state's current node."""

    node_id: str
    selected_edge_id: str
    tap_count: int


@dataclass(frozen=True)
class StructuralTransitionResult:
    """The canonical successor and observable evidence for one decision."""

    previous_state: PuzzleState
    state: PuzzleState
    decision: StructuralDecision
    traversed_edge_ids: tuple[str, ...]
    visited_node_ids: tuple[str, ...]
    completed_objective_ids: tuple[str, ...]
    route_distance: float
    failure_reason: str | None = None

    @property
    def next_state(self) -> PuzzleState:
        return self.state


class PuzzleStateTransitionService:
    """Apply one choice, then move to the next decision/objective boundary.

    Runtime timestamps and eligibility windows deliberately do not participate
    here. Authored road order, objective conditions, one-use consumption, and
    persistent switch selections use the same schema contracts as the runtime.
    """

    def initial_state(
        self,
        level: LevelDocument,
        *,
        active_switch_edge_ids: tuple[tuple[str, str], ...] = (),
    ) -> PuzzleState:
        index = GraphIndex.build(level.graph)
        if level.startNodeID not in index.nodes_by_id:
            raise PuzzleStateTransitionError(
                "structural_start_node_unknown",
                f"Unknown start node: {level.startNodeID}",
            )

        completed: tuple[str, ...] = ()
        objective_index = 0
        terminal = PuzzleTerminalOutcome.ACTIVE
        objective_index, completed, terminal, _ = self._process_objective_arrival(
            level,
            level.startNodeID,
            objective_index,
            completed,
        )
        available = self._available_edge_ids(level, index, completed, objective_index, ())
        switches = self._normalized_switches(
            level,
            index,
            available,
            dict(active_switch_edge_ids),
        )
        if terminal is PuzzleTerminalOutcome.ACTIVE and not self._usable_outgoing(
            index,
            level.startNodeID,
            available,
        ):
            terminal = PuzzleTerminalOutcome.FAILURE
        return PuzzleState(
            current_node_id=level.startNodeID,
            current_edge_id=None,
            objective_index=objective_index,
            completed_objective_ids=completed,
            available_edge_ids=available,
            active_switch_edge_ids=switches,
            visit_counts=((level.startNodeID, 1),),
            terminal_outcome=terminal,
        )

    def available_decisions(
        self,
        level: LevelDocument,
        state: PuzzleState,
    ) -> tuple[StructuralDecision, ...]:
        if state.is_terminal or state.current_node_id is None:
            return ()
        index = GraphIndex.build(level.graph)
        outgoing = self._usable_outgoing(
            index,
            state.current_node_id,
            state.available_edge_ids,
        )
        if not outgoing:
            return ()

        authored = index.outgoing_by_node_id[state.current_node_id]
        current_edge_id = state.active_switch_map.get(state.current_node_id)
        current_index = next(
            (position for position, edge in enumerate(outgoing) if edge.id == current_edge_id),
            0,
        )
        is_authored_switch = len(authored) >= 2
        return tuple(
            StructuralDecision(
                node_id=state.current_node_id,
                selected_edge_id=edge.id,
                tap_count=(position - current_index) % len(outgoing) if is_authored_switch else 0,
            )
            for position, edge in enumerate(outgoing)
        )

    # A concise alias for callers that treat pass-through movement as an action.
    available_actions = available_decisions

    def successors(
        self,
        level: LevelDocument,
        state: PuzzleState,
    ) -> tuple[StructuralTransitionResult, ...]:
        return tuple(
            self.transition(level, state, decision)
            for decision in self.available_decisions(level, state)
        )

    def apply_decision(
        self,
        level: LevelDocument,
        state: PuzzleState,
        selected_edge_id: str,
    ) -> StructuralTransitionResult:
        decision = next(
            (
                candidate
                for candidate in self.available_decisions(level, state)
                if candidate.selected_edge_id == selected_edge_id
            ),
            None,
        )
        if decision is None:
            raise PuzzleStateTransitionError(
                "structural_edge_not_selectable",
                f"Edge '{selected_edge_id}' is not selectable from the current state.",
            )
        return self.transition(level, state, decision)

    def transition(
        self,
        level: LevelDocument,
        state: PuzzleState,
        decision: StructuralDecision,
    ) -> StructuralTransitionResult:
        if state.is_terminal:
            raise PuzzleStateTransitionError(
                "structural_state_terminal",
                "A terminal puzzle state has no successors.",
            )
        expected = {
            candidate.selected_edge_id: candidate
            for candidate in self.available_decisions(level, state)
        }.get(decision.selected_edge_id)
        if expected is None or expected.node_id != decision.node_id:
            raise PuzzleStateTransitionError(
                "structural_decision_invalid",
                "The selected road is not available at the current node.",
            )
        if expected.tap_count != decision.tap_count:
            raise PuzzleStateTransitionError(
                "structural_tap_count_invalid",
                "The decision tap count does not match authored switch rotation.",
            )

        index = GraphIndex.build(level.graph)
        node_id = decision.node_id
        objective_index = state.objective_index
        completed = state.completed_objective_ids
        consumed = set(state.consumed_edge_ids)
        active_switches = state.active_switch_map
        if len(index.outgoing_by_node_id[node_id]) >= 2:
            active_switches[node_id] = decision.selected_edge_id
        visit_counts = state.visit_count_map
        traversed: list[str] = []
        visited: list[str] = []
        completed_during_transition: list[str] = []
        route_distance = 0.0
        next_edge_id = decision.selected_edge_id
        terminal = PuzzleTerminalOutcome.ACTIVE
        failure_reason: str | None = None
        available = state.available_edge_ids
        automatic_positions: set[
            tuple[str, str, int, tuple[str, ...], tuple[str, ...]]
        ] = set()

        while True:
            automatic_position = (
                node_id,
                next_edge_id,
                objective_index,
                completed,
                tuple(sorted(consumed)),
            )
            if automatic_position in automatic_positions:
                terminal = PuzzleTerminalOutcome.FAILURE
                failure_reason = "structural_automatic_cycle"
                break
            automatic_positions.add(automatic_position)
            edge = index.edges_by_id[next_edge_id]
            traversed.append(edge.id)
            route_distance += self._edge_distance(index, edge)
            rule = level.effective_edge_availability_rule(edge)
            if rule.usageLimit == 1:
                consumed.add(edge.id)

            node_id = edge.toNodeID
            visited.append(node_id)
            visit_counts[node_id] = visit_counts.get(node_id, 0) + 1
            (
                objective_index,
                completed,
                terminal,
                newly_completed,
            ) = self._process_objective_arrival(
                level,
                node_id,
                objective_index,
                completed,
            )
            completed_during_transition.extend(newly_completed)
            available = self._available_edge_ids(
                level,
                index,
                completed,
                objective_index,
                tuple(consumed),
            )
            active_switches = dict(
                self._normalized_switches(
                    level,
                    index,
                    available,
                    active_switches,
                )
            )
            if terminal is PuzzleTerminalOutcome.SUCCESS:
                break
            if terminal is PuzzleTerminalOutcome.FAILURE:
                failure_reason = "structural_destination_before_objective"
                break

            outgoing = self._usable_outgoing(index, node_id, available)
            if not outgoing:
                terminal = PuzzleTerminalOutcome.FAILURE
                failure_reason = "structural_dead_end"
                break
            if len(outgoing) >= 2:
                break
            next_edge_id = outgoing[0].id

        successor = PuzzleState(
            current_node_id=node_id,
            current_edge_id=None,
            objective_index=objective_index,
            completed_objective_ids=completed,
            available_edge_ids=available,
            consumed_edge_ids=tuple(consumed),
            active_switch_edge_ids=tuple(active_switches.items()),
            visit_counts=tuple(visit_counts.items()),
            accepted_tap_count=state.accepted_tap_count + decision.tap_count,
            elapsed_time_seconds=state.elapsed_time_seconds,
            terminal_outcome=terminal,
        )
        return StructuralTransitionResult(
            previous_state=state,
            state=successor,
            decision=decision,
            traversed_edge_ids=tuple(traversed),
            visited_node_ids=tuple(visited),
            completed_objective_ids=tuple(completed_during_transition),
            route_distance=round(route_distance, 9),
            failure_reason=failure_reason,
        )

    @staticmethod
    def _usable_outgoing(
        index: GraphIndex,
        node_id: str,
        available_edge_ids: tuple[str, ...],
    ) -> tuple[RouteEdge, ...]:
        available = set(available_edge_ids)
        return tuple(
            edge
            for edge in index.outgoing_by_node_id.get(node_id, ())
            if edge.id in available
        )

    def _available_edge_ids(
        self,
        level: LevelDocument,
        index: GraphIndex,
        completed_objective_ids: tuple[str, ...],
        objective_index: int,
        consumed_edge_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        completed = set(completed_objective_ids)
        consumed = set(consumed_edge_ids)
        active_index = objective_index if objective_index < len(level.effective_objectives) else None
        return tuple(
            edge.id
            for edge in index.graph.edges
            if edge.id not in consumed
            and level.effective_edge_availability_rule(edge).allows(
                completed,
                active_index,
                usage_count=0,
            )
        )

    def _normalized_switches(
        self,
        level: LevelDocument,
        index: GraphIndex,
        available_edge_ids: tuple[str, ...],
        requested: dict[str, str],
    ) -> tuple[tuple[str, str], ...]:
        del level  # The normalized order comes from the already-filtered graph.
        available = set(available_edge_ids)
        result: list[tuple[str, str]] = []
        for node in index.graph.nodes:
            authored = index.outgoing_by_node_id[node.id]
            if len(authored) < 2:
                continue
            usable = tuple(edge for edge in authored if edge.id in available)
            if not usable:
                continue
            valid = {edge.id for edge in usable}
            result.append(
                (
                    node.id,
                    requested[node.id] if requested.get(node.id) in valid else usable[0].id,
                )
            )
        return tuple(result)

    @staticmethod
    def _process_objective_arrival(
        level: LevelDocument,
        node_id: str,
        objective_index: int,
        completed_objective_ids: tuple[str, ...],
    ) -> tuple[int, tuple[str, ...], PuzzleTerminalOutcome, tuple[str, ...]]:
        objectives = sorted(level.effective_objectives, key=lambda value: value.sequenceIndex)
        completed = list(completed_objective_ids)
        newly_completed: list[str] = []
        terminal = PuzzleTerminalOutcome.ACTIVE
        if objective_index >= len(objectives):
            return objective_index, tuple(completed), terminal, ()

        active = objectives[objective_index]
        if node_id != active.nodeID:
            if level.schema_version < 3 and any(
                objective.nodeID == node_id
                and objective.kind is RouteObjectiveKind.DESTINATION
                for objective in objectives[objective_index + 1 :]
            ):
                terminal = PuzzleTerminalOutcome.FAILURE
            return objective_index, tuple(completed), terminal, ()

        while objective_index < len(objectives) and objectives[objective_index].nodeID == node_id:
            active = objectives[objective_index]
            completed.append(active.id)
            newly_completed.append(active.id)
            objective_index += 1
            if objective_index >= len(objectives):
                if active.kind is RouteObjectiveKind.DESTINATION:
                    terminal = PuzzleTerminalOutcome.SUCCESS
                break
            if level.schema_version >= 3:
                break
        return objective_index, tuple(completed), terminal, tuple(newly_completed)

    @staticmethod
    def _edge_distance(index: GraphIndex, edge: RouteEdge) -> float:
        start = index.nodes_by_id[edge.fromNodeID]
        end = index.nodes_by_id[edge.toNodeID]
        return math.hypot(float(end.x) - float(start.x), float(end.y) - float(start.y))
