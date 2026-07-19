from __future__ import annotations
from dataclasses import dataclass, field
from tiny_routes_core.graph import GraphValidationError
from tiny_routes_core.models import LevelDocument, LevelRules, RouteObjective, RouteObjectiveKind
from .results import LevelOutcome
from .runtime_graph import RuntimeGraph


@dataclass(frozen=True)
class ObjectiveProgressEvent:
    kind: str
    objective_id: str
    sequence_index: int
    node_id: str
    objective_kind: RouteObjectiveKind


@dataclass
class RuntimeState:
    rules: LevelRules
    runtime_graph: RuntimeGraph
    current_node_id: str
    current_edge_id: str | None
    edge_progress: float
    package_collected: bool
    elapsed_time: float
    remaining_time: float
    accepted_tap_count: int
    outcome: LevelOutcome
    tap_cooldown_remaining: float
    objectives: list[RouteObjective] = field(default_factory=list)
    active_objective_index: int | None = None
    completed_objective_ids: set[str] = field(default_factory=set)
    revealed_objective_ids: set[str] = field(default_factory=set)
    objective_events: list[ObjectiveProgressEvent] = field(default_factory=list)
    visited_node_ids: list[str] = field(default_factory=list)

    @classmethod
    def initialize(cls, level: LevelDocument) -> "RuntimeState":
        objectives = sorted(level.effective_objectives, key=lambda objective: objective.sequenceIndex)
        package_collected = False
        runtime_graph = RuntimeGraph.build(
            level.graph,
            package_collected=package_collected,
        )
        errors = []
        for label, node_id in (("start", level.startNodeID), ("package", level.packageNodeID),
                               ("destination", level.destinationNodeID)):
            if node_id not in runtime_graph.index.nodes_by_id: errors.append(f"missing_{label}_node:{node_id}")
        if errors: raise GraphValidationError(errors)
        state = cls(
            rules=level.rules,
            runtime_graph=runtime_graph,
            current_node_id=level.startNodeID,
            current_edge_id=None,
            edge_progress=0.0,
            package_collected=package_collected,
            elapsed_time=0.0,
            remaining_time=float(level.timeLimitSeconds),
            accepted_tap_count=0,
            outcome=LevelOutcome.IN_PROGRESS,
            tap_cooldown_remaining=0.0,
            objectives=objectives,
            active_objective_index=0 if objectives else None,
            visited_node_ids=[level.startNodeID],
        )
        state._initialize_objective_visibility()
        state.process_objective_arrival(
            level.startNodeID,
            preserve_legacy_destination_failure=level.schema_version < 3,
            cascade_legacy_same_node=level.schema_version < 3,
        )
        state.current_edge_id = state.runtime_graph.active_edge_ids.get(level.startNodeID)
        return state

    @property
    def active_objective(self) -> RouteObjective | None:
        if self.active_objective_index is None:
            return None
        if not 0 <= self.active_objective_index < len(self.objectives):
            return None
        return self.objectives[self.active_objective_index]

    def _initialize_objective_visibility(self) -> None:
        for objective in self.objectives:
            if objective.revealPolicy == "always":
                self._reveal(objective)
        if self.active_objective is not None:
            self._reveal(self.active_objective)
            self._record_objective_event("objective_activated", self.active_objective)

    def process_objective_arrival(
        self,
        node_id: str,
        *,
        preserve_legacy_destination_failure: bool,
        cascade_legacy_same_node: bool = False,
    ) -> list[ObjectiveProgressEvent]:
        """Apply one arrival boundary and return its normalized objective events.

        Schema-3 levels ignore an early visit to a future objective and record it.
        Legacy levels retain the historical destination-before-package failure and
        same-node package/destination completion behavior.
        """

        event_start = len(self.objective_events)
        active = self.active_objective
        if active is None:
            return []

        if node_id != active.nodeID:
            future = next(
                (
                    objective
                    for objective in self.objectives[active.sequenceIndex + 1 :]
                    if objective.nodeID == node_id
                ),
                None,
            )
            if future is not None:
                if preserve_legacy_destination_failure and future.kind is RouteObjectiveKind.DESTINATION:
                    self.outcome = LevelOutcome.FAILED_MISSING_PACKAGE
                else:
                    self._record_objective_event("future_objective_visited", future)
            return self.objective_events[event_start:]

        while active is not None and node_id == active.nodeID:
            self.completed_objective_ids.add(active.id)
            if active.kind is RouteObjectiveKind.PICKUP:
                self.package_collected = True
            self._record_objective_event("objective_completed", active)
            self.runtime_graph.normalize_for_package_state(self.package_collected)

            next_index = active.sequenceIndex + 1
            if next_index >= len(self.objectives):
                self.active_objective_index = None
                if active.kind is RouteObjectiveKind.DESTINATION:
                    self.outcome = LevelOutcome.COMPLETED
                break

            self.active_objective_index = next_index
            active = self.active_objective
            if active is not None:
                self._reveal(active)
                self._record_objective_event("objective_activated", active)
            if not cascade_legacy_same_node:
                break

        return self.objective_events[event_start:]

    def _reveal(self, objective: RouteObjective) -> None:
        if objective.id in self.revealed_objective_ids:
            return
        self.revealed_objective_ids.add(objective.id)
        self._record_objective_event("objective_revealed", objective)

    def _record_objective_event(self, kind: str, objective: RouteObjective) -> None:
        self.objective_events.append(ObjectiveProgressEvent(
            kind=kind,
            objective_id=objective.id,
            sequence_index=objective.sequenceIndex,
            node_id=objective.nodeID,
            objective_kind=objective.kind,
        ))

    @property
    def switch_active_edge_ids(self) -> dict[str, str]:
        return self.runtime_graph.active_edge_ids

    def clone(self) -> "RuntimeState":
        return RuntimeState(
            rules=self.rules,
            runtime_graph=self.runtime_graph.clone(),
            current_node_id=self.current_node_id,
            current_edge_id=self.current_edge_id,
            edge_progress=self.edge_progress,
            package_collected=self.package_collected,
            elapsed_time=self.elapsed_time,
            remaining_time=self.remaining_time,
            accepted_tap_count=self.accepted_tap_count,
            outcome=self.outcome,
            tap_cooldown_remaining=self.tap_cooldown_remaining,
            objectives=[objective.clone() for objective in self.objectives],
            active_objective_index=self.active_objective_index,
            completed_objective_ids=self.completed_objective_ids.copy(),
            revealed_objective_ids=self.revealed_objective_ids.copy(),
            objective_events=self.objective_events.copy(),
            visited_node_ids=self.visited_node_ids.copy(),
        )
