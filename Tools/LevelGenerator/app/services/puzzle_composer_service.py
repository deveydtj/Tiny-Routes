"""Deterministic graph operations used by the V3 puzzle composer."""

from __future__ import annotations

from dataclasses import replace

from ..models.composition_state import (
    AssignedStateEffect,
    CompositionGraph,
    CompositionState,
    LayoutFootprintEstimate,
    OpenCompositionPort,
    PartialStrategicMetrics,
)
from ..models.graph_recipe import GraphRecipeEdge, GraphRecipeNode
from ..models.motif_contract import MotifDependencyEffect
from ..models.motif_port import MotifPort, MotifPortType
from ..models.puzzle_motif import PuzzleMotif
from .typed_port_connection_validator import (
    PortConnectionKind,
    TypedPortConnectionValidator,
)


class PuzzleCompositionError(ValueError):
    """A composition operation failed before mutating its immutable input."""


class PuzzleComposerService:
    """Apply deterministic, immutable topology changes to composition states.

    These operations are deliberately independent from motif selection and
    backtracking.  A later search layer can therefore try them speculatively,
    discard a rejected successor, and retain the exact prior state.
    """

    def __init__(
        self,
        port_validator: TypedPortConnectionValidator | None = None,
    ) -> None:
        self.port_validator = port_validator or TypedPortConnectionValidator()

    def insert_motif_into_edge(
        self,
        state: CompositionState,
        *,
        motif: PuzzleMotif,
        instance_id: str,
        objective_phase_index: int,
        edge_index: int | None = None,
        edge: GraphRecipeEdge | None = None,
        exit_port_id: str | None = None,
        fulfilled_decision_ids: tuple[str, ...] = (),
    ) -> CompositionState:
        """Replace one edge with ``source -> motif -> target``.

        The original edge's availability and usage limit remain on the edge
        entering the inserted motif.  This preserves when the original route
        can be entered while avoiding accidental duplication of a one-use
        constraint across both new connector edges.
        """

        self._require_state_and_motif(state, motif)
        selected_index, selected_edge = self._resolve_edge(
            state.current_graph.edges,
            edge_index=edge_index,
            edge=edge,
        )
        qualified_nodes, node_id_by_local = self._qualify_nodes(
            state,
            motif,
            instance_id,
        )
        qualified_ports = self._qualify_ports(
            motif,
            instance_id,
            objective_phase_index,
            node_id_by_local,
        )
        entry = self._single_port(qualified_ports, MotifPortType.MAIN_ROUTE_ENTRY)
        exit = self._selected_exit(qualified_ports, exit_port_id)

        qualified_edges = self._qualify_edges(motif, node_id_by_local)
        entering_edge = GraphRecipeEdge(
            selected_edge.from_node_id,
            entry.node_id,
            selected_edge.availability,
            selected_edge.usage_limit,
        )
        leaving_edge = GraphRecipeEdge(exit.node_id, selected_edge.to_node_id)
        existing_edges = state.current_graph.edges
        successor_edges = (
            *existing_edges[:selected_index],
            entering_edge,
            *qualified_edges,
            leaving_edge,
            *existing_edges[selected_index + 1 :],
        )
        successor_graph = CompositionGraph(
            nodes=(*state.current_graph.nodes, *qualified_nodes),
            edges=successor_edges,
        )

        consumed_ids = {entry.id, exit.id}
        open_ports = (
            *state.open_ports,
            *(port for port in qualified_ports if port.id not in consumed_ids),
        )
        assigned_effects = tuple(
            replace(effect, to_node_id=entry.node_id)
            if (
                effect.from_node_id == selected_edge.from_node_id
                and effect.to_node_id == selected_edge.to_node_id
            )
            else effect
            for effect in state.assigned_state_effects
        )
        return self._successor(
            state,
            motif,
            successor_graph,
            open_ports,
            fulfilled_decision_ids,
            assigned_state_effects=assigned_effects,
        )

    def insert_edge(self, *args: object, **kwargs: object) -> CompositionState:
        """Task-name alias for :meth:`insert_motif_into_edge`."""

        return self.insert_motif_into_edge(*args, **kwargs)  # type: ignore[arg-type]

    def expand_branch(
        self,
        state: CompositionState,
        *,
        source_port: OpenCompositionPort | str,
        motif: PuzzleMotif,
        instance_id: str,
        objective_phase_index: int | None = None,
        fulfilled_decision_ids: tuple[str, ...] = (),
        availability: str = "always",
        usage_limit: int | None = None,
    ) -> CompositionState:
        """Attach a motif to an open branch-insertion port.

        The source node must already lead somewhere; adding the connector then
        creates an actual alternate branch instead of merely appending a serial
        fragment.  The consumed source and motif entry ports are removed while
        every other qualified motif port remains available for nested work.
        """

        self._require_state_and_motif(state, motif)
        source = self._resolve_open_port(state, source_port)
        phase_index = (
            source.objective_phase_index
            if objective_phase_index is None
            else objective_phase_index
        )
        qualified_nodes, node_id_by_local = self._qualify_nodes(
            state,
            motif,
            instance_id,
        )
        qualified_ports = self._qualify_ports(
            motif,
            instance_id,
            phase_index,
            node_id_by_local,
        )
        entry = self._single_port(qualified_ports, MotifPortType.MAIN_ROUTE_ENTRY)
        validation = self.port_validator.validate(
            source,
            entry,
            target_phase_index=phase_index,
        )
        if not validation.is_valid:
            raise PuzzleCompositionError(validation.issues[0])
        if validation.kind is not PortConnectionKind.BRANCH_EXPANSION:
            raise PuzzleCompositionError("composition_operation_not_branch_expansion")
        if not any(
            edge.from_node_id == source.node_id
            for edge in state.current_graph.edges
        ):
            raise PuzzleCompositionError(
                f"composition_branch_source_has_no_existing_route:{source.id}"
            )
        self._validate_connector_attributes(availability, usage_limit)

        connector = GraphRecipeEdge(
            source.node_id,
            entry.node_id,
            availability,
            usage_limit,
        )
        successor_graph = CompositionGraph(
            nodes=(*state.current_graph.nodes, *qualified_nodes),
            edges=(
                *state.current_graph.edges,
                connector,
                *self._qualify_edges(motif, node_id_by_local),
            ),
        )
        open_ports = (
            *(port for port in state.open_ports if port.id != source.id),
            *(port for port in qualified_ports if port.id != entry.id),
        )
        return self._successor(
            state,
            motif,
            successor_graph,
            open_ports,
            fulfilled_decision_ids,
        )

    def expand_branch_with_motif(
        self,
        *args: object,
        **kwargs: object,
    ) -> CompositionState:
        """Descriptive alias for :meth:`expand_branch`."""

        return self.expand_branch(*args, **kwargs)  # type: ignore[arg-type]

    @staticmethod
    def _require_state_and_motif(
        state: CompositionState,
        motif: PuzzleMotif,
    ) -> None:
        if not isinstance(state, CompositionState):
            raise TypeError("state must be a CompositionState")
        state_issues = state.validate()
        if state_issues:
            raise PuzzleCompositionError(f"composition_state_invalid:{state_issues[0]}")
        if not isinstance(motif, PuzzleMotif):
            raise TypeError("motif must be a PuzzleMotif")
        motif_issues = motif.validate()
        if motif_issues:
            raise PuzzleCompositionError(f"composition_motif_invalid:{motif_issues[0]}")
        if not motif.ports:
            raise PuzzleCompositionError(
                f"composition_motif_typed_ports_required:{motif.motif_id}"
            )

    @staticmethod
    def _resolve_edge(
        edges: tuple[GraphRecipeEdge, ...],
        *,
        edge_index: int | None,
        edge: GraphRecipeEdge | None,
    ) -> tuple[int, GraphRecipeEdge]:
        if (edge_index is None) == (edge is None):
            raise PuzzleCompositionError(
                "composition_edge_selector_requires_exactly_one_value"
            )
        if edge_index is not None:
            if (
                not isinstance(edge_index, int)
                or isinstance(edge_index, bool)
                or not 0 <= edge_index < len(edges)
            ):
                raise PuzzleCompositionError(f"composition_edge_index_invalid:{edge_index}")
            return edge_index, edges[edge_index]
        if not isinstance(edge, GraphRecipeEdge):
            raise TypeError("edge must be a GraphRecipeEdge")
        matches = tuple(index for index, candidate in enumerate(edges) if candidate == edge)
        if not matches:
            raise PuzzleCompositionError("composition_edge_not_found")
        if len(matches) > 1:
            raise PuzzleCompositionError("composition_edge_selector_ambiguous")
        return matches[0], edge

    @staticmethod
    def _qualify_nodes(
        state: CompositionState,
        motif: PuzzleMotif,
        instance_id: str,
    ) -> tuple[tuple[GraphRecipeNode, ...], dict[str, str]]:
        if not isinstance(instance_id, str) or not instance_id.strip():
            raise PuzzleCompositionError("composition_instance_id_empty")
        normalized = instance_id.strip()
        node_id_by_local = {
            node.id: f"{normalized}__{node.id}" for node in motif.nodes
        }
        existing = set(state.current_graph.node_ids)
        collisions = sorted(existing.intersection(node_id_by_local.values()))
        if collisions:
            raise PuzzleCompositionError(
                f"composition_instance_node_collision:{collisions[0]}"
            )
        return (
            tuple(
                GraphRecipeNode(node_id_by_local[node.id], node.role)
                for node in motif.nodes
            ),
            node_id_by_local,
        )

    @staticmethod
    def _qualify_edges(
        motif: PuzzleMotif,
        node_id_by_local: dict[str, str],
    ) -> tuple[GraphRecipeEdge, ...]:
        return tuple(
            GraphRecipeEdge(
                node_id_by_local[edge.from_node_id],
                node_id_by_local[edge.to_node_id],
                edge.availability,
                edge.usage_limit,
            )
            for edge in motif.edges
        )

    @staticmethod
    def _qualify_ports(
        motif: PuzzleMotif,
        instance_id: str,
        objective_phase_index: int,
        node_id_by_local: dict[str, str],
    ) -> tuple[OpenCompositionPort, ...]:
        if (
            not isinstance(objective_phase_index, int)
            or isinstance(objective_phase_index, bool)
            or objective_phase_index < 0
        ):
            raise PuzzleCompositionError(
                f"composition_objective_phase_invalid:{objective_phase_index}"
            )
        return tuple(
            OpenCompositionPort(
                instance_id,
                MotifPort(port.id, node_id_by_local[port.node_id], port.port_type),
                objective_phase_index,
            )
            for port in motif.ports
        )

    @staticmethod
    def _single_port(
        ports: tuple[OpenCompositionPort, ...],
        port_type: MotifPortType,
    ) -> OpenCompositionPort:
        matches = tuple(port for port in ports if port.port_type is port_type)
        if len(matches) != 1:
            raise PuzzleCompositionError(
                f"composition_port_count_invalid:{port_type.value}:{len(matches)}"
            )
        return matches[0]

    @staticmethod
    def _selected_exit(
        ports: tuple[OpenCompositionPort, ...],
        exit_port_id: str | None,
    ) -> OpenCompositionPort:
        exits = tuple(
            port for port in ports if port.port_type is MotifPortType.MAIN_ROUTE_EXIT
        )
        if exit_port_id is None:
            if not exits:
                raise PuzzleCompositionError("composition_main_route_exit_missing")
            return exits[0]
        matches = tuple(port for port in exits if port.port.id == exit_port_id)
        if len(matches) != 1:
            raise PuzzleCompositionError(
                f"composition_main_route_exit_unknown:{exit_port_id}"
            )
        return matches[0]

    @staticmethod
    def _resolve_open_port(
        state: CompositionState,
        value: OpenCompositionPort | str,
    ) -> OpenCompositionPort:
        port_id = value.id if isinstance(value, OpenCompositionPort) else value
        if not isinstance(port_id, str) or not port_id.strip():
            raise PuzzleCompositionError("composition_source_port_id_empty")
        matches = tuple(port for port in state.open_ports if port.id == port_id)
        if len(matches) != 1:
            raise PuzzleCompositionError(f"composition_source_port_not_open:{port_id}")
        return matches[0]

    @staticmethod
    def _validate_connector_attributes(
        availability: str,
        usage_limit: int | None,
    ) -> None:
        if availability not in {"always", "beforePackage", "afterPackage"}:
            raise PuzzleCompositionError(
                f"composition_connector_availability_invalid:{availability}"
            )
        if usage_limit is not None and (
            not isinstance(usage_limit, int)
            or isinstance(usage_limit, bool)
            or usage_limit <= 0
        ):
            raise PuzzleCompositionError(
                f"composition_connector_usage_limit_invalid:{usage_limit}"
            )

    def _successor(
        self,
        state: CompositionState,
        motif: PuzzleMotif,
        graph: CompositionGraph,
        open_ports: tuple[OpenCompositionPort, ...],
        fulfilled_decision_ids: tuple[str, ...],
        *,
        assigned_state_effects: tuple[AssignedStateEffect, ...] | None = None,
    ) -> CompositionState:
        fulfilled = self._fulfilled_decisions(state, fulfilled_decision_ids)
        metrics = self._updated_metrics(state.partial_strategic_metrics, motif)
        footprint = self._updated_footprint(
            state.estimated_layout_footprint,
            motif,
        )
        previous_rejoins = self._rejoin_count(state.current_graph)
        next_rejoins = self._rejoin_count(graph)
        cycle_delta = int(motif.may_introduce_cycle)
        return state.evolve(
            unfulfilled_decision_ids=tuple(
                decision_id
                for decision_id in state.unfulfilled_decision_ids
                if decision_id not in fulfilled
            ),
            open_ports=open_ports,
            current_graph=graph,
            assigned_state_effects=(
                state.assigned_state_effects
                if assigned_state_effects is None
                else assigned_state_effects
            ),
            placed_motif_ids=(*state.placed_motif_ids, motif.motif_id),
            cycle_count=state.cycle_count + cycle_delta,
            rejoin_count=state.rejoin_count + max(0, next_rejoins - previous_rejoins),
            estimated_layout_footprint=footprint,
            partial_strategic_metrics=metrics,
        )

    @staticmethod
    def _fulfilled_decisions(
        state: CompositionState,
        values: tuple[str, ...],
    ) -> set[str]:
        values = tuple(values)
        if len(values) != len(set(values)):
            raise PuzzleCompositionError("composition_fulfilled_decisions_not_unique")
        unknown = sorted(set(values).difference(state.unfulfilled_decision_ids))
        if unknown:
            raise PuzzleCompositionError(
                f"composition_fulfilled_decision_unknown:{unknown[0]}"
            )
        return set(values)

    @staticmethod
    def _updated_metrics(
        current: PartialStrategicMetrics,
        motif: PuzzleMotif,
    ) -> PartialStrategicMetrics:
        effects = motif.effects
        if effects is None:
            return current
        dependency = effects.expected_downstream_dependency
        dependent = dependency is not MotifDependencyEffect.NONE
        return PartialStrategicMetrics(
            meaningful_decision_count=(
                current.meaningful_decision_count + len(effects.decision_node_ids)
            ),
            adaptive_decision_count=(
                current.adaptive_decision_count
                + (len(effects.decision_node_ids) if dependent else 0)
            ),
            dependency_depth=current.dependency_depth + int(dependent),
            revisit_count=current.revisit_count + int(effects.introduces_revisit),
            recovery_count=current.recovery_count + int(effects.introduces_recovery_exit),
        )

    @staticmethod
    def _updated_footprint(
        current: LayoutFootprintEstimate,
        motif: PuzzleMotif,
    ) -> LayoutFootprintEstimate:
        if motif.effects is None:
            motif_width, motif_height = max(1, len(motif.nodes)), 1
        else:
            motif_width, motif_height = motif.effects.minimum_layout_footprint
        return LayoutFootprintEstimate(
            width=current.width + motif_width,
            height=max(current.height, motif_height),
        )

    @staticmethod
    def _rejoin_count(graph: CompositionGraph) -> int:
        incoming: dict[str, int] = {}
        for edge in graph.edges:
            incoming[edge.to_node_id] = incoming.get(edge.to_node_id, 0) + 1
        return sum(count >= 2 for count in incoming.values())
