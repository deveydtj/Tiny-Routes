"""Stable graph algorithms used by validation, generation, and simulation."""

from __future__ import annotations
from collections import deque
from .index import GraphIndex


def is_switchable(index: GraphIndex, node_id: str) -> bool:
    return len(index.outgoing_by_node_id[node_id]) >= 2


def reachable_node_ids(index: GraphIndex, start_node_id: str) -> tuple[str, ...]:
    if start_node_id not in index.nodes_by_id: return ()
    found, queue = {start_node_id}, deque([start_node_id])
    order: list[str] = []
    while queue:
        node_id = queue.popleft(); order.append(node_id)
        for edge in index.outgoing_by_node_id[node_id]:
            if edge.toNodeID not in found: found.add(edge.toNodeID); queue.append(edge.toNodeID)
    return tuple(order)


def cycle_node_ids(index: GraphIndex) -> tuple[str, ...]:
    color: dict[str, int] = {key: 0 for key in index.nodes_by_id}; cyclic: set[str] = set(); stack: list[str] = []
    def visit(node_id: str) -> None:
        color[node_id] = 1; stack.append(node_id)
        for edge in index.outgoing_by_node_id[node_id]:
            target = edge.toNodeID
            if color[target] == 0: visit(target)
            elif color[target] == 1: cyclic.update(stack[stack.index(target):])
        stack.pop(); color[node_id] = 2
    for node_id in sorted(index.nodes_by_id):
        if color[node_id] == 0: visit(node_id)
    return tuple(sorted(cyclic))


def rejoin_node_ids(index: GraphIndex, switch_node_id: str) -> tuple[str, ...]:
    branches = index.outgoing_by_node_id[switch_node_id]
    if len(branches) < 2: return ()
    sets = [set(reachable_node_ids(index, edge.toNodeID)) for edge in branches]
    return tuple(sorted(set.intersection(*sets)))


def required_route(index: GraphIndex, start_node_id: str, active_edges: dict[str, str], *, limit: int = 10_000) -> tuple[str, ...]:
    """Follow normalized active choices, returning node IDs including the start."""
    route, current = [start_node_id], start_node_id
    for _ in range(limit):
        outgoing = index.outgoing_by_node_id[current]
        if not outgoing: return tuple(route)
        chosen = next((edge for edge in outgoing if edge.id == active_edges.get(current)), outgoing[0])
        current = chosen.toNodeID; route.append(current)
        if current in route[:-1]: return tuple(route)
    return tuple(route)


def normalize_active_edges(index: GraphIndex, active_edges: dict[str, str] | None = None) -> dict[str, str]:
    requested = active_edges or {}; result: dict[str, str] = {}
    for node in index.graph.nodes:
        outgoing = index.outgoing_by_node_id[node.id]
        if outgoing:
            valid = {edge.id for edge in outgoing}
            result[node.id] = requested[node.id] if requested.get(node.id) in valid else outgoing[0].id
    return result
