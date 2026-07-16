from dataclasses import dataclass
from tiny_routes_core.graph import (
    GraphIndex,
    GraphValidationError,
    normalize_active_edges,
    usable_outgoing_edges,
)
from tiny_routes_core.models import RouteGraph

@dataclass
class RuntimeGraph:
    index: GraphIndex
    active_edge_ids: dict[str, str]

    @classmethod
    def build(
        cls,
        graph: RouteGraph,
        active_edge_ids: dict[str, str] | None = None,
        *,
        package_collected: bool = False,
    ):
        index = GraphIndex.build(graph)
        errors: list[str] = []
        for node in graph.nodes:
            authored = index.outgoing_by_node_id[node.id]
            if not authored:
                continue
            for collected, phase in ((False, "before_package"), (True, "after_package")):
                if not usable_outgoing_edges(index, node.id, collected):
                    errors.append(f"conditional_road_dead_end:{node.id}:{phase}")
        if errors:
            raise GraphValidationError(errors)
        return cls(
            index,
            normalize_active_edges(
                index,
                active_edge_ids,
                package_collected=package_collected,
            ),
        )

    def normalize_for_package_state(self, package_collected: bool) -> None:
        self.active_edge_ids = normalize_active_edges(
            self.index,
            self.active_edge_ids,
            package_collected=package_collected,
        )

    def usable_outgoing(self, node_id: str, package_collected: bool):
        return usable_outgoing_edges(self.index, node_id, package_collected)

    def clone(self):
        return RuntimeGraph(self.index, self.active_edge_ids.copy())
