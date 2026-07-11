"""Validated deterministic indexes over a route graph."""

from __future__ import annotations
from dataclasses import dataclass
from tiny_routes_core.models import RouteEdge, RouteGraph, RouteNode


class GraphValidationError(ValueError):
    def __init__(self, codes: list[str]):
        self.codes = tuple(codes)
        super().__init__(";".join(codes))


@dataclass(frozen=True)
class GraphIndex:
    graph: RouteGraph
    nodes_by_id: dict[str, RouteNode]
    edges_by_id: dict[str, RouteEdge]
    outgoing_by_node_id: dict[str, tuple[RouteEdge, ...]]
    incoming_by_node_id: dict[str, tuple[RouteEdge, ...]]

    @classmethod
    def build(cls, graph: RouteGraph) -> "GraphIndex":
        errors: list[str] = []
        nodes: dict[str, RouteNode] = {}
        edges: dict[str, RouteEdge] = {}
        for node in graph.nodes:
            if node.id in nodes: errors.append(f"duplicate_node_id:{node.id}")
            else: nodes[node.id] = node
        for edge in graph.edges:
            if edge.id in edges: errors.append(f"duplicate_edge_id:{edge.id}")
            else: edges[edge.id] = edge
        if errors: raise GraphValidationError(errors)
        outgoing: dict[str, tuple[RouteEdge, ...]] = {}
        incoming_lists: dict[str, list[RouteEdge]] = {node_id: [] for node_id in nodes}
        for edge in graph.edges:
            if edge.fromNodeID not in nodes: errors.append(f"edge_unknown_from_node:{edge.id}:{edge.fromNodeID}")
            if edge.toNodeID not in nodes: errors.append(f"edge_unknown_to_node:{edge.id}:{edge.toNodeID}")
            if edge.toNodeID in incoming_lists: incoming_lists[edge.toNodeID].append(edge)
        for node in graph.nodes:
            seen: set[str] = set()
            ordered: list[RouteEdge] = []
            for edge_id in node.outgoingEdgeIDs:
                if edge_id in seen: errors.append(f"duplicate_outgoing_edge_id:{node.id}:{edge_id}"); continue
                seen.add(edge_id)
                edge = edges.get(edge_id)
                if edge is None: errors.append(f"missing_outgoing_edge:{node.id}:{edge_id}")
                elif edge.fromNodeID != node.id: errors.append(f"outgoing_edge_wrong_source:{node.id}:{edge_id}")
                else: ordered.append(edge)
            outgoing[node.id] = tuple(ordered)
        if errors: raise GraphValidationError(errors)
        return cls(graph, nodes, edges, outgoing,
                   {key: tuple(value) for key, value in incoming_lists.items()})
