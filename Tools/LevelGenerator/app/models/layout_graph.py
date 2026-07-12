from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .graph_recipe import GraphRecipe


class SwitchPortDirection(str, Enum):
    NORTH = "north"
    NORTH_EAST = "north_east"
    EAST = "east"
    SOUTH_EAST = "south_east"
    SOUTH = "south"
    SOUTH_WEST = "south_west"
    WEST = "west"
    NORTH_WEST = "north_west"


@dataclass(frozen=True, order=True)
class GridCell:
    column: int
    row: int


@dataclass(frozen=True, order=True)
class Lane:
    index: int
    kind: str = "primary"


@dataclass(frozen=True)
class NodeFootprint:
    width: float
    height: float

    @classmethod
    def for_outgoing_count(cls, outgoing_count: int) -> "NodeFootprint":
        # Multi-way switches need room for their icon and separated first segments.
        diameter = 1.6 if outgoing_count >= 4 else 1.35 if outgoing_count == 3 else 1.0
        return cls(width=diameter, height=diameter)


@dataclass(frozen=True)
class CandidateBendPoint:
    edge_id: str
    cell: GridCell
    priority: int = 0


@dataclass(frozen=True)
class LayoutGraphNode:
    node_id: str
    role: str
    outgoing_node_ids: tuple[str, ...]
    incoming_node_ids: tuple[str, ...]
    footprint: NodeFootprint


@dataclass(frozen=True)
class LayoutGraphEdge:
    edge_id: str
    from_node_id: str
    to_node_id: str


@dataclass(frozen=True)
class LayoutGraph:
    nodes: tuple[LayoutGraphNode, ...]
    edges: tuple[LayoutGraphEdge, ...]
    start_node_id: str
    destination_node_id: str
    primary_route: tuple[str, ...]

    @classmethod
    def from_recipe(cls, recipe: GraphRecipe) -> "LayoutGraph":
        outgoing: dict[str, list[str]] = {node.id: [] for node in recipe.nodes}
        incoming: dict[str, list[str]] = {node.id: [] for node in recipe.nodes}
        edges: list[LayoutGraphEdge] = []
        for index, edge in enumerate(recipe.edges):
            outgoing.setdefault(edge.from_node_id, []).append(edge.to_node_id)
            incoming.setdefault(edge.to_node_id, []).append(edge.from_node_id)
            edges.append(LayoutGraphEdge(f"layout_edge_{index}", edge.from_node_id, edge.to_node_id))
        nodes = tuple(
            LayoutGraphNode(
                node_id=node.id,
                role=node.role,
                outgoing_node_ids=tuple(outgoing.get(node.id, ())),
                incoming_node_ids=tuple(incoming.get(node.id, ())),
                footprint=NodeFootprint.for_outgoing_count(len(outgoing.get(node.id, ()))),
            )
            for node in recipe.nodes
        )
        return cls(nodes, tuple(edges), "start", recipe.destination_node_id, recipe.required_path)
