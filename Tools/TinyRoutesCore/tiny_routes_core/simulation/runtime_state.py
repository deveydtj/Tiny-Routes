from __future__ import annotations
from dataclasses import dataclass, field
from tiny_routes_core.graph import GraphValidationError
from tiny_routes_core.models import LevelDocument, LevelRules
from .results import LevelOutcome
from .runtime_graph import RuntimeGraph

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
    visited_node_ids: list[str] = field(default_factory=list)

    @classmethod
    def initialize(cls, level: LevelDocument) -> "RuntimeState":
        package_collected = level.startNodeID == level.packageNodeID
        runtime_graph = RuntimeGraph.build(
            level.graph,
            package_collected=package_collected,
        )
        errors = []
        for label, node_id in (("start", level.startNodeID), ("package", level.packageNodeID),
                               ("destination", level.destinationNodeID)):
            if node_id not in runtime_graph.index.nodes_by_id: errors.append(f"missing_{label}_node:{node_id}")
        if errors: raise GraphValidationError(errors)
        current_edge = runtime_graph.active_edge_ids.get(level.startNodeID)
        return cls(level.rules, runtime_graph, level.startNodeID, current_edge, 0.0,
                   package_collected, 0.0, float(level.timeLimitSeconds),
                   0, LevelOutcome.IN_PROGRESS, 0.0, [level.startNodeID])

    @property
    def switch_active_edge_ids(self) -> dict[str, str]:
        return self.runtime_graph.active_edge_ids

    def clone(self) -> "RuntimeState":
        return RuntimeState(self.rules, self.runtime_graph.clone(), self.current_node_id,
                            self.current_edge_id, self.edge_progress, self.package_collected,
                            self.elapsed_time, self.remaining_time, self.accepted_tap_count,
                            self.outcome, self.tap_cooldown_remaining, self.visited_node_ids.copy())
