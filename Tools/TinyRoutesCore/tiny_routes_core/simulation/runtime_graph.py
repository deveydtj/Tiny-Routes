from dataclasses import dataclass, field
from tiny_routes_core.graph import (
    GraphIndex,
    GraphValidationError,
)
from tiny_routes_core.models import EdgeAvailabilityRule, LevelDocument, RouteEdge

@dataclass
class RuntimeGraph:
    index: GraphIndex
    active_edge_ids: dict[str, str]
    availability_rules_by_edge_id: dict[str, EdgeAvailabilityRule] = field(default_factory=dict)
    edge_usage_counts: dict[str, int] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        level: LevelDocument,
        active_edge_ids: dict[str, str] | None = None,
        *,
        completed_objective_ids: set[str] | None = None,
        active_objective_index: int | None = 0,
    ):
        graph = level.graph
        index = GraphIndex.build(graph)
        rules = {
            edge.id: level.effective_edge_availability_rule(edge)
            for edge in graph.edges
        }
        runtime = cls(index, {}, rules, {})

        objectives = sorted(
            level.effective_objectives,
            key=lambda objective: objective.sequenceIndex,
        )
        if level.schema_version < 3 or not objectives:
            package_objective_id = (
                objectives[0].id if objectives else "legacy_pickup"
            )
            validation_states = (
                (set(), 0, "before_package"),
                ({package_objective_id}, 1, "after_package"),
            )
        else:
            validation_states = tuple(
                (
                    {objective.id for objective in objectives[:index_value]},
                    index_value,
                    f"objective_{index_value}",
                )
                for index_value in range(len(objectives))
            )

        errors: list[str] = []
        for node in graph.nodes:
            authored = index.outgoing_by_node_id[node.id]
            if not authored:
                continue
            for completed, objective_index, phase in validation_states:
                if not runtime.usable_outgoing(node.id, completed, objective_index):
                    errors.append(f"conditional_road_dead_end:{node.id}:{phase}")
        if errors:
            raise GraphValidationError(errors)
        runtime.active_edge_ids = runtime._normalized_active_edges(
            active_edge_ids,
            completed_objective_ids or set(),
            active_objective_index,
        )
        return runtime

    def edge_is_usable(
        self,
        edge: RouteEdge,
        completed_objective_ids: set[str],
        active_objective_index: int | None,
    ) -> bool:
        return self.availability_rules_by_edge_id[edge.id].allows(
            completed_objective_ids,
            active_objective_index,
            usage_count=self.edge_usage_counts.get(edge.id, 0),
        )

    def usable_outgoing(
        self,
        node_id: str,
        completed_objective_ids: set[str],
        active_objective_index: int | None,
    ) -> tuple[RouteEdge, ...]:
        """Filter roads in authored rotation order for the current runtime state."""

        return tuple(
            edge
            for edge in self.index.outgoing_by_node_id[node_id]
            if self.edge_is_usable(
                edge,
                completed_objective_ids,
                active_objective_index,
            )
        )

    def normalize_for_objective_state(
        self,
        completed_objective_ids: set[str],
        active_objective_index: int | None,
    ) -> None:
        self.active_edge_ids = self._normalized_active_edges(
            self.active_edge_ids,
            completed_objective_ids,
            active_objective_index,
        )

    def _normalized_active_edges(
        self,
        requested: dict[str, str] | None,
        completed_objective_ids: set[str],
        active_objective_index: int | None,
    ) -> dict[str, str]:
        requested = requested or {}
        result: dict[str, str] = {}
        for node in self.index.graph.nodes:
            outgoing = self.usable_outgoing(
                node.id,
                completed_objective_ids,
                active_objective_index,
            )
            if outgoing:
                valid = {edge.id for edge in outgoing}
                result[node.id] = (
                    requested[node.id]
                    if requested.get(node.id) in valid
                    else outgoing[0].id
                )
        return result

    def record_edge_traversal(self, edge_id: str) -> int:
        """Commit one deterministic use and return the updated traversal count."""

        count = self.edge_usage_counts.get(edge_id, 0) + 1
        self.edge_usage_counts[edge_id] = count
        return count

    def clone(self):
        return RuntimeGraph(
            self.index,
            self.active_edge_ids.copy(),
            self.availability_rules_by_edge_id,
            self.edge_usage_counts.copy(),
        )
