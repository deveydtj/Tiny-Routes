from dataclasses import dataclass
from tiny_routes_core.graph import GraphIndex, normalize_active_edges
from tiny_routes_core.models import RouteGraph

@dataclass
class RuntimeGraph:
    index: GraphIndex
    active_edge_ids: dict[str, str]

    @classmethod
    def build(cls, graph: RouteGraph, active_edge_ids: dict[str, str] | None = None):
        index = GraphIndex.build(graph)
        return cls(index, normalize_active_edges(index, active_edge_ids))

    def clone(self):
        return RuntimeGraph(self.index, self.active_edge_ids.copy())
