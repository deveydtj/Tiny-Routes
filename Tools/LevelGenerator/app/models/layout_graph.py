from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

from .composition_state import CompositionState
from .graph_recipe import GraphRecipe
from .motif_contract import MotifEdgeStateChangeKind


class SwitchPortDirection(str, Enum):
    NORTH = "north"
    NORTH_EAST = "north_east"
    EAST = "east"
    SOUTH_EAST = "south_east"
    SOUTH = "south"
    SOUTH_WEST = "south_west"
    WEST = "west"
    NORTH_WEST = "north_west"


class LayoutCorridorKind(str, Enum):
    PRIMARY = "primary"
    ALTERNATE = "alternate"
    FAILURE = "failure"
    RECOVERY = "recovery"


@dataclass(frozen=True, order=True)
class LayoutStateRelationship:
    """A route-state change the layout must communicate around one edge."""

    transition_id: str
    kind: MotifEdgeStateChangeKind

    def __post_init__(self) -> None:
        if not isinstance(self.transition_id, str) or not self.transition_id.strip():
            raise ValueError("transition_id must not be empty")
        object.__setattr__(self, "transition_id", self.transition_id.strip())
        if not isinstance(self.kind, MotifEdgeStateChangeKind):
            object.__setattr__(self, "kind", MotifEdgeStateChangeKind(self.kind))


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
    def for_outgoing_count(
        cls,
        outgoing_count: int,
        *,
        is_stateful_hub: bool = False,
    ) -> "NodeFootprint":
        # Multi-way switches need room for their icon and separated first segments.
        diameter = 1.6 if outgoing_count >= 4 else 1.35 if outgoing_count == 3 else 1.0
        if is_stateful_hub:
            diameter = max(diameter, 1.85)
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
    objective_phase_indices: tuple[int, ...] = ()
    is_revisited_hub: bool = False


@dataclass(frozen=True)
class LayoutGraphEdge:
    edge_id: str
    from_node_id: str
    to_node_id: str
    availability: str = "always"
    objective_phase_indices: tuple[int, ...] = ()
    corridor_kinds: tuple[LayoutCorridorKind, ...] = ()
    state_relationships: tuple[LayoutStateRelationship, ...] = ()


@dataclass(frozen=True)
class LayoutGraph:
    nodes: tuple[LayoutGraphNode, ...]
    edges: tuple[LayoutGraphEdge, ...]
    start_node_id: str
    destination_node_id: str
    primary_route: tuple[str, ...]

    @property
    def stateful_hub_node_ids(self) -> tuple[str, ...]:
        return tuple(node.node_id for node in self.nodes if node.is_revisited_hub)

    @property
    def objective_phase_count(self) -> int:
        indices = {
            phase_index
            for node in self.nodes
            for phase_index in node.objective_phase_indices
        }
        indices.update(
            phase_index
            for edge in self.edges
            for phase_index in edge.objective_phase_indices
        )
        return max(indices, default=-1) + 1

    @classmethod
    def from_recipe(
        cls,
        recipe: GraphRecipe,
        *,
        phase_routes: Sequence[Sequence[str]] | None = None,
        alternate_routes: Sequence[Sequence[str]] = (),
        failure_routes: Sequence[Sequence[str]] = (),
        recovery_routes: Sequence[Sequence[str]] = (),
    ) -> "LayoutGraph":
        resolved_phase_routes = cls._recipe_phase_routes(recipe, phase_routes)
        return cls._build(
            nodes=recipe.nodes,
            recipe_edges=recipe.edges,
            start_node_id="start",
            destination_node_id=recipe.destination_node_id,
            primary_route=recipe.required_path,
            phase_routes=resolved_phase_routes,
            alternate_routes=alternate_routes,
            failure_routes=failure_routes,
            recovery_routes=recovery_routes,
            relationship_by_edge=cls._legacy_state_relationships(recipe),
        )

    @classmethod
    def from_composition_state(
        cls,
        state: CompositionState,
        *,
        primary_route: Sequence[str],
        phase_routes: Sequence[Sequence[str]] | None = None,
        alternate_routes: Sequence[Sequence[str]] = (),
        failure_routes: Sequence[Sequence[str]] = (),
        recovery_routes: Sequence[Sequence[str]] = (),
        start_node_id: str = "start",
        destination_node_id: str = "destination",
    ) -> "LayoutGraph":
        """Adapt completed V3 composition evidence without discarding phase state."""

        if not isinstance(state, CompositionState):
            raise TypeError("state must be a CompositionState")
        resolved_phase_routes = (
            tuple(tuple(route) for route in phase_routes)
            if phase_routes is not None
            else cls._composition_phase_routes(state)
        )
        relationships: dict[tuple[str, str], list[LayoutStateRelationship]] = {}
        for effect in state.assigned_state_effects:
            relationships.setdefault(
                (effect.from_node_id, effect.to_node_id), []
            ).append(LayoutStateRelationship(effect.transition_id, effect.kind))
        return cls._build(
            nodes=state.current_graph.nodes,
            recipe_edges=state.current_graph.edges,
            start_node_id=start_node_id,
            destination_node_id=destination_node_id,
            primary_route=tuple(primary_route),
            phase_routes=resolved_phase_routes,
            alternate_routes=alternate_routes,
            failure_routes=failure_routes,
            recovery_routes=recovery_routes,
            relationship_by_edge={
                pair: tuple(values) for pair, values in relationships.items()
            },
        )

    @classmethod
    def _build(
        cls,
        *,
        nodes,
        recipe_edges,
        start_node_id: str,
        destination_node_id: str,
        primary_route: tuple[str, ...],
        phase_routes: Sequence[Sequence[str]],
        alternate_routes: Sequence[Sequence[str]],
        failure_routes: Sequence[Sequence[str]],
        recovery_routes: Sequence[Sequence[str]],
        relationship_by_edge: dict[
            tuple[str, str], tuple[LayoutStateRelationship, ...]
        ],
    ) -> "LayoutGraph":
        outgoing: dict[str, list[str]] = {node.id: [] for node in nodes}
        incoming: dict[str, list[str]] = {node.id: [] for node in nodes}
        node_phases: dict[str, set[int]] = {node.id: set() for node in nodes}
        edge_phases: dict[tuple[str, str], set[int]] = {}
        for phase_index, route in enumerate(phase_routes):
            for node_id in route:
                node_phases.setdefault(node_id, set()).add(phase_index)
            for pair in zip(route, route[1:]):
                edge_phases.setdefault(pair, set()).add(phase_index)

        corridor_edges = {
            LayoutCorridorKind.PRIMARY: cls._route_edges((primary_route,)),
            LayoutCorridorKind.ALTERNATE: cls._route_edges(alternate_routes),
            LayoutCorridorKind.FAILURE: cls._route_edges(failure_routes),
            LayoutCorridorKind.RECOVERY: cls._route_edges(recovery_routes),
        }
        edges: list[LayoutGraphEdge] = []
        for index, edge in enumerate(recipe_edges):
            outgoing.setdefault(edge.from_node_id, []).append(edge.to_node_id)
            incoming.setdefault(edge.to_node_id, []).append(edge.from_node_id)
            pair = (edge.from_node_id, edge.to_node_id)
            relationship = relationship_by_edge.get(pair, ())
            inferred_phases = set(edge_phases.get(pair, ()))
            if not inferred_phases:
                inferred_phases.update(node_phases.get(edge.from_node_id, ()))
            if edge.availability == "beforePackage":
                inferred_phases = {0}
            elif edge.availability == "afterPackage":
                inferred_phases = {max(1, max(inferred_phases, default=1))}
            edges.append(LayoutGraphEdge(
                f"layout_edge_{index}",
                edge.from_node_id,
                edge.to_node_id,
                edge.availability,
                tuple(sorted(inferred_phases)),
                tuple(
                    kind for kind in LayoutCorridorKind if pair in corridor_edges[kind]
                ),
                tuple(sorted(relationship)),
            ))
        layout_nodes: list[LayoutGraphNode] = []
        for node in nodes:
            phases = tuple(sorted(node_phases.get(node.id, ())))
            is_revisited_hub = len(phases) > 1 and len(outgoing.get(node.id, ())) >= 2
            layout_nodes.append(LayoutGraphNode(
                node_id=node.id,
                role=node.role,
                outgoing_node_ids=tuple(outgoing.get(node.id, ())),
                incoming_node_ids=tuple(incoming.get(node.id, ())),
                footprint=NodeFootprint.for_outgoing_count(
                    len(outgoing.get(node.id, ())),
                    is_stateful_hub=is_revisited_hub,
                ),
                objective_phase_indices=phases,
                is_revisited_hub=is_revisited_hub,
            ))
        return cls(
            tuple(layout_nodes),
            tuple(edges),
            start_node_id,
            destination_node_id,
            primary_route,
        )

    @staticmethod
    def _route_edges(routes: Iterable[Sequence[str]]) -> set[tuple[str, str]]:
        return {
            pair
            for route in routes
            for pair in zip(route, route[1:])
        }

    @classmethod
    def _recipe_phase_routes(
        cls,
        recipe: GraphRecipe,
        phase_routes: Sequence[Sequence[str]] | None,
    ) -> tuple[tuple[str, ...], ...]:
        if phase_routes is not None:
            return tuple(tuple(route) for route in phase_routes)
        if not recipe.required_path:
            return ()
        phases: list[list[str]] = [[]]
        for node_id in recipe.required_path:
            phases[-1].append(node_id)
            if node_id == recipe.package_node_id and node_id != recipe.destination_node_id:
                phases.append([node_id])
        return tuple(tuple(route) for route in phases if route)

    @staticmethod
    def _legacy_state_relationships(
        recipe: GraphRecipe,
    ) -> dict[tuple[str, str], tuple[LayoutStateRelationship, ...]]:
        relationships: dict[tuple[str, str], tuple[LayoutStateRelationship, ...]] = {}
        for edge in recipe.edges:
            kind = None
            if edge.availability == "afterPackage":
                kind = MotifEdgeStateChangeKind.OPEN
            elif edge.availability == "beforePackage":
                kind = MotifEdgeStateChangeKind.CLOSE
            if kind is not None:
                relationships[(edge.from_node_id, edge.to_node_id)] = (
                    LayoutStateRelationship(recipe.package_node_id, kind),
                )
        return relationships

    @classmethod
    def _composition_phase_routes(
        cls,
        state: CompositionState,
    ) -> tuple[tuple[str, ...], ...]:
        """Find nodes lying on a directed entry-to-exit corridor for each phase."""

        outgoing: dict[str, set[str]] = {}
        for edge in state.current_graph.edges:
            outgoing.setdefault(edge.from_node_id, set()).add(edge.to_node_id)

        def shortest_path(entry: str, exit_node: str) -> tuple[str, ...]:
            pending: list[tuple[str, ...]] = [(entry,)]
            seen = {entry}
            while pending:
                path = pending.pop(0)
                if path[-1] == exit_node:
                    return path
                for node_id in sorted(outgoing.get(path[-1], ())):
                    if node_id in seen:
                        continue
                    seen.add(node_id)
                    pending.append((*path, node_id))
            return (entry,) if entry == exit_node else (entry, exit_node)

        routes: list[tuple[str, ...]] = []
        for boundary in state.objective_phase_boundaries:
            if boundary.entry_node_id is None and boundary.exit_node_id is None:
                routes.append(())
                continue
            entry = boundary.entry_node_id or boundary.exit_node_id
            exit_node = boundary.exit_node_id or boundary.entry_node_id
            assert entry is not None and exit_node is not None
            routes.append(shortest_path(entry, exit_node))
        return tuple(routes)
