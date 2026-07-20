"""Deterministic graph operations used by the V3 puzzle composer."""

from __future__ import annotations

from dataclasses import replace

from ..models.composition_state import (
    AssignedStateEffect,
    CompositionGraph,
    CompositionState,
    LayoutFootprintEstimate,
    ObjectivePhaseBoundary,
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

    def attach_rejoin(
        self,
        state: CompositionState,
        *,
        target_port: OpenCompositionPort | str,
        source_ports: tuple[OpenCompositionPort | str, ...] = (),
        source_port: OpenCompositionPort | str | None = None,
        fulfilled_decision_ids: tuple[str, ...] = (),
        availability: str = "always",
        usage_limit: int | None = None,
    ) -> CompositionState:
        """Connect one or more branch exits to a real merge point.

        ``source_port`` is a convenience selector for the common case where
        the target node already has an incoming main route. ``source_ports``
        supports attaching two or more disconnected branches atomically. The
        target is consumed only after every connector has been validated.
        """

        self._require_state(state)
        sources = self._resolve_source_ports(
            state,
            source_ports=source_ports,
            source_port=source_port,
        )
        target = self._resolve_open_port(state, target_port, role="target")
        if target.id in {source.id for source in sources}:
            raise PuzzleCompositionError(f"composition_rejoin_same_port:{target.id}")

        for source in sources:
            validation = self.port_validator.validate(source, target, state=state)
            if not validation.is_valid:
                raise PuzzleCompositionError(validation.issues[0])
            if validation.kind is not PortConnectionKind.REJOIN:
                raise PuzzleCompositionError("composition_operation_not_rejoin")
        self._validate_connector_attributes(availability, usage_limit)

        connectors = tuple(
            GraphRecipeEdge(source.node_id, target.node_id, availability, usage_limit)
            for source in sources
        )
        self._require_new_connectors(state.current_graph, connectors, "rejoin")
        graph = CompositionGraph(
            nodes=state.current_graph.nodes,
            edges=(*state.current_graph.edges, *connectors),
        )
        incoming_sources = {
            edge.from_node_id
            for edge in graph.edges
            if edge.to_node_id == target.node_id
        }
        if len(incoming_sources) < 2:
            raise PuzzleCompositionError(
                f"composition_rejoin_requires_two_branches:{target.id}"
            )

        consumed_ids = {target.id, *(source.id for source in sources)}
        return self._connection_successor(
            state,
            graph,
            tuple(port for port in state.open_ports if port.id not in consumed_ids),
            fulfilled_decision_ids,
        )

    def connect_rejoin(
        self,
        *args: object,
        **kwargs: object,
    ) -> CompositionState:
        """Task-name alias for :meth:`attach_rejoin`."""

        return self.attach_rejoin(*args, **kwargs)  # type: ignore[arg-type]

    def connect_cross_phase_return(
        self,
        state: CompositionState,
        *,
        source_port: OpenCompositionPort | str,
        target_port: OpenCompositionPort | str,
        fulfilled_decision_ids: tuple[str, ...] = (),
        availability: str = "afterPackage",
        usage_limit: int | None = None,
    ) -> CompositionState:
        """Connect a later objective phase back to a reachable earlier hub."""

        self._require_state(state)
        source = self._resolve_open_port(state, source_port, role="source")
        target = self._resolve_open_port(state, target_port, role="target")
        validation = self.port_validator.validate(source, target, state=state)
        if not validation.is_valid:
            raise PuzzleCompositionError(validation.issues[0])
        if validation.kind is not PortConnectionKind.RETURN_PATH:
            raise PuzzleCompositionError("composition_operation_not_return_path")
        self._validate_connector_attributes(availability, usage_limit)

        connector = GraphRecipeEdge(
            source.node_id,
            target.node_id,
            availability,
            usage_limit,
        )
        self._require_new_connectors(
            state.current_graph,
            (connector,),
            "return_path",
        )
        if not self._is_reachable(
            state.current_graph,
            target.node_id,
            source.node_id,
        ):
            raise PuzzleCompositionError(
                "composition_return_path_does_not_close_cycle:"
                f"{source.id}:{target.id}"
            )

        graph = CompositionGraph(
            nodes=state.current_graph.nodes,
            edges=(*state.current_graph.edges, connector),
        )
        consumed_ids = {source.id, target.id}
        metrics = replace(
            state.partial_strategic_metrics,
            revisit_count=state.partial_strategic_metrics.revisit_count + 1,
        )
        return self._connection_successor(
            state,
            graph,
            tuple(port for port in state.open_ports if port.id not in consumed_ids),
            fulfilled_decision_ids,
            cycle_delta=1,
            metrics=metrics,
        )

    def connect_return_path(
        self,
        *args: object,
        **kwargs: object,
    ) -> CompositionState:
        """Short alias for :meth:`connect_cross_phase_return`."""

        return self.connect_cross_phase_return(*args, **kwargs)  # type: ignore[arg-type]

    def attach_objective(
        self,
        state: CompositionState,
        *,
        objective_id: str,
        objective_port: OpenCompositionPort | str | None = None,
        source_port: OpenCompositionPort | str | None = None,
        target_port: OpenCompositionPort | str | None = None,
        phase_entry_node_id: str | None = None,
        phase_exit_node_id: str | None = None,
        fulfilled_decision_ids: tuple[str, ...] = (),
        availability: str = "always",
        usage_limit: int | None = None,
    ) -> CompositionState:
        """Bind one blueprint objective phase to concrete composed nodes.

        Existing stateful motifs expose an objective node directly through
        ``objective_port``.  Composition can therefore bind that node without
        introducing a decorative connector.  The two-port form connects a
        separately composed objective branch from ``source_port`` to
        ``target_port`` and records those nodes as the phase entry and exit.

        Both forms consume their selected ports and update the matching
        ``ObjectivePhaseBoundary`` in the same immutable successor.  A failed
        validation leaves the input state untouched.
        """

        self._require_state(state)
        boundary_index, boundary = self._resolve_objective_boundary(
            state,
            objective_id,
        )
        single_port_mode = objective_port is not None
        paired_port_mode = source_port is not None or target_port is not None
        if single_port_mode == paired_port_mode:
            raise PuzzleCompositionError(
                "composition_objective_selector_requires_single_or_paired_ports"
            )

        graph = state.current_graph
        consumed_ids: set[str]
        if single_port_mode:
            assert objective_port is not None
            if availability != "always" or usage_limit is not None:
                raise PuzzleCompositionError(
                    "composition_objective_connector_attributes_require_paired_ports"
                )
            attached = self._resolve_open_port(
                state,
                objective_port,
                role="objective",
            )
            if attached.port_type is not MotifPortType.OBJECTIVE_ATTACHMENT:
                raise PuzzleCompositionError(
                    "composition_objective_port_type_invalid:"
                    f"{attached.id}:{attached.port_type.value}"
                )
            if attached.objective_phase_index != boundary.phase_index:
                raise PuzzleCompositionError(
                    "composition_objective_phase_mismatch:"
                    f"{boundary.phase_index}:{attached.objective_phase_index}"
                )
            entry_node_id = self._objective_boundary_node(
                phase_entry_node_id,
                attached.node_id,
                "entry",
            )
            exit_node_id = self._objective_boundary_node(
                phase_exit_node_id,
                attached.node_id,
                "exit",
            )
            consumed_ids = {attached.id}
        else:
            if source_port is None or target_port is None:
                raise PuzzleCompositionError(
                    "composition_objective_paired_ports_incomplete"
                )
            source = self._resolve_open_port(state, source_port, role="source")
            target = self._resolve_open_port(state, target_port, role="target")
            validation = self.port_validator.validate(source, target, state=state)
            if not validation.is_valid:
                raise PuzzleCompositionError(validation.issues[0])
            if validation.kind is not PortConnectionKind.OBJECTIVE_ATTACHMENT:
                raise PuzzleCompositionError(
                    "composition_operation_not_objective_attachment"
                )
            if target.objective_phase_index != boundary.phase_index:
                raise PuzzleCompositionError(
                    "composition_objective_phase_mismatch:"
                    f"{boundary.phase_index}:{target.objective_phase_index}"
                )
            self._validate_connector_attributes(availability, usage_limit)
            connector = GraphRecipeEdge(
                source.node_id,
                target.node_id,
                availability,
                usage_limit,
            )
            self._require_new_connectors(
                state.current_graph,
                (connector,),
                "objective_attachment",
            )
            graph = CompositionGraph(
                nodes=state.current_graph.nodes,
                edges=(*state.current_graph.edges, connector),
            )
            entry_node_id = self._objective_boundary_node(
                phase_entry_node_id,
                source.node_id,
                "entry",
            )
            exit_node_id = self._objective_boundary_node(
                phase_exit_node_id,
                target.node_id,
                "exit",
            )
            consumed_ids = {source.id, target.id}

        known_nodes = set(graph.node_ids)
        for role, node_id in (
            ("entry", entry_node_id),
            ("exit", exit_node_id),
        ):
            if node_id not in known_nodes:
                raise PuzzleCompositionError(
                    f"composition_objective_{role}_node_unknown:{node_id}"
                )
        if not self._is_reachable(graph, entry_node_id, exit_node_id):
            raise PuzzleCompositionError(
                "composition_objective_boundary_not_reachable:"
                f"{entry_node_id}:{exit_node_id}"
            )
        self._require_objective_node_available(
            state,
            objective_id=boundary.objective_id,
            objective_node_id=exit_node_id,
        )

        boundaries = list(state.objective_phase_boundaries)
        boundaries[boundary_index] = ObjectivePhaseBoundary(
            boundary.objective_id,
            boundary.phase_index,
            entry_node_id,
            exit_node_id,
        )
        return self._connection_successor(
            state,
            graph,
            tuple(port for port in state.open_ports if port.id not in consumed_ids),
            fulfilled_decision_ids,
            objective_phase_boundaries=tuple(boundaries),
        )

    def attach_objective_to_port(
        self,
        *args: object,
        **kwargs: object,
    ) -> CompositionState:
        """Descriptive alias for the single-port objective operation."""

        return self.attach_objective(*args, **kwargs)  # type: ignore[arg-type]

    def connect_objective_attachment(
        self,
        *args: object,
        **kwargs: object,
    ) -> CompositionState:
        """Task-name alias supporting the paired-port objective operation."""

        return self.attach_objective(*args, **kwargs)  # type: ignore[arg-type]

    @staticmethod
    def _require_state_and_motif(
        state: CompositionState,
        motif: PuzzleMotif,
    ) -> None:
        PuzzleComposerService._require_state(state)
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
    def _require_state(state: CompositionState) -> None:
        if not isinstance(state, CompositionState):
            raise TypeError("state must be a CompositionState")
        state_issues = state.validate()
        if state_issues:
            raise PuzzleCompositionError(f"composition_state_invalid:{state_issues[0]}")

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
        *,
        role: str = "source",
    ) -> OpenCompositionPort:
        port_id = value.id if isinstance(value, OpenCompositionPort) else value
        if not isinstance(port_id, str) or not port_id.strip():
            raise PuzzleCompositionError(f"composition_{role}_port_id_empty")
        matches = tuple(port for port in state.open_ports if port.id == port_id)
        if len(matches) != 1:
            raise PuzzleCompositionError(f"composition_{role}_port_not_open:{port_id}")
        return matches[0]

    @staticmethod
    def _resolve_objective_boundary(
        state: CompositionState,
        objective_id: str,
    ) -> tuple[int, ObjectivePhaseBoundary]:
        if not isinstance(objective_id, str) or not objective_id.strip():
            raise PuzzleCompositionError("composition_objective_id_empty")
        normalized = objective_id.strip()
        matches = tuple(
            (index, boundary)
            for index, boundary in enumerate(state.objective_phase_boundaries)
            if boundary.objective_id == normalized
        )
        if len(matches) != 1:
            raise PuzzleCompositionError(
                f"composition_objective_boundary_unknown:{normalized}"
            )
        index, boundary = matches[0]
        if boundary.entry_node_id is not None or boundary.exit_node_id is not None:
            raise PuzzleCompositionError(
                f"composition_objective_already_attached:{normalized}"
            )
        return index, boundary

    @staticmethod
    def _require_objective_node_available(
        state: CompositionState,
        *,
        objective_id: str,
        objective_node_id: str,
    ) -> None:
        for boundary in state.objective_phase_boundaries:
            if boundary.objective_id == objective_id:
                continue
            if boundary.exit_node_id == objective_node_id:
                raise PuzzleCompositionError(
                    "composition_objective_node_already_assigned:"
                    f"{objective_node_id}:{boundary.objective_id}"
                )

    @staticmethod
    def _objective_boundary_node(
        explicit_node_id: str | None,
        default_node_id: str,
        role: str,
    ) -> str:
        if explicit_node_id is None:
            return default_node_id
        if not isinstance(explicit_node_id, str) or not explicit_node_id.strip():
            raise PuzzleCompositionError(
                f"composition_objective_{role}_node_id_empty"
            )
        return explicit_node_id.strip()

    @classmethod
    def _resolve_source_ports(
        cls,
        state: CompositionState,
        *,
        source_ports: tuple[OpenCompositionPort | str, ...],
        source_port: OpenCompositionPort | str | None,
    ) -> tuple[OpenCompositionPort, ...]:
        values = tuple(source_ports)
        if source_port is not None:
            if values:
                raise PuzzleCompositionError(
                    "composition_rejoin_source_selector_ambiguous"
                )
            values = (source_port,)
        if not values:
            raise PuzzleCompositionError("composition_rejoin_source_ports_empty")
        resolved = tuple(cls._resolve_open_port(state, value) for value in values)
        ids = tuple(port.id for port in resolved)
        if len(ids) != len(set(ids)):
            duplicate_id = next(
                port_id
                for index, port_id in enumerate(ids)
                if port_id in ids[:index]
            )
            raise PuzzleCompositionError(
                f"composition_rejoin_source_port_duplicate:{duplicate_id}"
            )
        return resolved

    @staticmethod
    def _require_new_connectors(
        graph: CompositionGraph,
        connectors: tuple[GraphRecipeEdge, ...],
        operation: str,
    ) -> None:
        existing_pairs = {
            (edge.from_node_id, edge.to_node_id) for edge in graph.edges
        }
        new_pairs: set[tuple[str, str]] = set()
        for connector in connectors:
            pair = (connector.from_node_id, connector.to_node_id)
            if connector.from_node_id == connector.to_node_id:
                raise PuzzleCompositionError(
                    f"composition_{operation}_self_loop:{connector.from_node_id}"
                )
            if pair in existing_pairs or pair in new_pairs:
                raise PuzzleCompositionError(
                    f"composition_{operation}_edge_exists:"
                    f"{connector.from_node_id}:{connector.to_node_id}"
                )
            new_pairs.add(pair)

    @staticmethod
    def _is_reachable(
        graph: CompositionGraph,
        start_node_id: str,
        target_node_id: str,
    ) -> bool:
        outgoing: dict[str, list[str]] = {}
        for edge in graph.edges:
            outgoing.setdefault(edge.from_node_id, []).append(edge.to_node_id)
        pending = [start_node_id]
        visited: set[str] = set()
        while pending:
            node_id = pending.pop()
            if node_id == target_node_id:
                return True
            if node_id in visited:
                continue
            visited.add(node_id)
            pending.extend(reversed(outgoing.get(node_id, ())))
        return False

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

    def _connection_successor(
        self,
        state: CompositionState,
        graph: CompositionGraph,
        open_ports: tuple[OpenCompositionPort, ...],
        fulfilled_decision_ids: tuple[str, ...],
        *,
        cycle_delta: int = 0,
        metrics: PartialStrategicMetrics | None = None,
        objective_phase_boundaries: tuple[ObjectivePhaseBoundary, ...] | None = None,
    ) -> CompositionState:
        fulfilled = self._fulfilled_decisions(state, fulfilled_decision_ids)
        previous_rejoins = self._rejoin_count(state.current_graph)
        next_rejoins = self._rejoin_count(graph)
        return state.evolve(
            unfulfilled_decision_ids=tuple(
                decision_id
                for decision_id in state.unfulfilled_decision_ids
                if decision_id not in fulfilled
            ),
            open_ports=open_ports,
            objective_phase_boundaries=(
                state.objective_phase_boundaries
                if objective_phase_boundaries is None
                else objective_phase_boundaries
            ),
            current_graph=graph,
            cycle_count=state.cycle_count + cycle_delta,
            rejoin_count=state.rejoin_count + max(0, next_rejoins - previous_rejoins),
            partial_strategic_metrics=(
                state.partial_strategic_metrics if metrics is None else metrics
            ),
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
