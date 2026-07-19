"""Immutable search state for constraint-based V3 puzzle composition."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

from .graph_recipe import GraphRecipeEdge, GraphRecipeNode
from .motif_contract import MotifEdgeStateChangeKind
from .motif_port import MotifPort, MotifPortType
from .puzzle_blueprint import PuzzleBlueprint


def _normalized_identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value.strip()


def _non_negative_integer(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


@dataclass(frozen=True)
class CompositionGraph:
    """The graph realized by a partial composition.

    A partial graph intentionally has fewer invariants than ``GraphRecipe``:
    it need not yet contain a start, destination, package, or solved path.
    """

    nodes: tuple[GraphRecipeNode, ...] = ()
    edges: tuple[GraphRecipeEdge, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(node.id for node in self.nodes)

    @property
    def switch_count(self) -> int:
        outgoing_counts: dict[str, int] = {}
        for edge in self.edges:
            outgoing_counts[edge.from_node_id] = outgoing_counts.get(edge.from_node_id, 0) + 1
        return sum(count >= 2 for count in outgoing_counts.values())

    def validate(self) -> tuple[str, ...]:
        issues: list[str] = []
        node_ids = self.node_ids
        known = set(node_ids)
        if len(node_ids) != len(known):
            issues.append("composition_graph_node_ids_not_unique")
        for node in self.nodes:
            if not isinstance(node, GraphRecipeNode):
                issues.append("composition_graph_node_invalid")
                continue
            if not isinstance(node.id, str) or not node.id.strip():
                issues.append("composition_graph_node_id_empty")
        for edge in self.edges:
            if not isinstance(edge, GraphRecipeEdge):
                issues.append("composition_graph_edge_invalid")
                continue
            if edge.from_node_id not in known:
                issues.append(f"composition_graph_edge_from_unknown:{edge.from_node_id}")
            if edge.to_node_id not in known:
                issues.append(f"composition_graph_edge_to_unknown:{edge.to_node_id}")
            if edge.availability not in {"always", "beforePackage", "afterPackage"}:
                issues.append(
                    "composition_graph_edge_availability_invalid:"
                    f"{edge.from_node_id}:{edge.to_node_id}:{edge.availability}"
                )
            if edge.usage_limit is not None and (
                not isinstance(edge.usage_limit, int)
                or isinstance(edge.usage_limit, bool)
                or edge.usage_limit <= 0
            ):
                issues.append(
                    f"composition_graph_edge_usage_limit_invalid:"
                    f"{edge.from_node_id}:{edge.to_node_id}"
                )
        return tuple(issues)


@dataclass(frozen=True)
class OpenCompositionPort:
    """A motif port qualified with its composed instance and objective phase."""

    instance_id: str
    port: MotifPort
    objective_phase_index: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "instance_id",
            _normalized_identifier(self.instance_id, "instance_id"),
        )
        if not isinstance(self.port, MotifPort):
            raise TypeError("port must be a MotifPort")
        _non_negative_integer(self.objective_phase_index, "objective_phase_index")

    @property
    def id(self) -> str:
        return f"{self.instance_id}:{self.port.id}"

    @property
    def node_id(self) -> str:
        return self.port.node_id

    @property
    def port_type(self) -> MotifPortType:
        return self.port.port_type

    def validate(self) -> tuple[str, ...]:
        return tuple(f"composition_open_{issue}" for issue in self.port.validate())


@dataclass(frozen=True)
class ObjectivePhaseBoundary:
    """Realization status for one ordered blueprint objective phase."""

    objective_id: str
    phase_index: int
    entry_node_id: str | None = None
    exit_node_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "objective_id",
            _normalized_identifier(self.objective_id, "objective_id"),
        )
        _non_negative_integer(self.phase_index, "phase_index")
        for field_name in ("entry_node_id", "exit_node_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _normalized_identifier(value, field_name))


@dataclass(frozen=True)
class AssignedStateEffect:
    """One blueprint route-state effect already assigned to a concrete edge."""

    transition_id: str
    edge_role: str
    from_node_id: str
    to_node_id: str
    kind: MotifEdgeStateChangeKind

    def __post_init__(self) -> None:
        for field_name in (
            "transition_id",
            "edge_role",
            "from_node_id",
            "to_node_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        if not isinstance(self.kind, MotifEdgeStateChangeKind):
            object.__setattr__(self, "kind", MotifEdgeStateChangeKind(self.kind))


@dataclass(frozen=True)
class LayoutFootprintEstimate:
    width: int = 0
    height: int = 0

    def __post_init__(self) -> None:
        _non_negative_integer(self.width, "width")
        _non_negative_integer(self.height, "height")

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(frozen=True)
class PartialStrategicMetrics:
    """Monotonic strategic evidence known for a partial graph."""

    meaningful_decision_count: int = 0
    adaptive_decision_count: int = 0
    dependency_depth: int = 0
    revisit_count: int = 0
    recovery_count: int = 0

    def __post_init__(self) -> None:
        for field_name in (
            "meaningful_decision_count",
            "adaptive_decision_count",
            "dependency_depth",
            "revisit_count",
            "recovery_count",
        ):
            _non_negative_integer(getattr(self, field_name), field_name)


@dataclass(frozen=True)
class CompositionState:
    """Complete deterministic state for one composition-search branch."""

    blueprint_id: str
    unfulfilled_decision_ids: tuple[str, ...]
    open_ports: tuple[OpenCompositionPort, ...]
    objective_phase_boundaries: tuple[ObjectivePhaseBoundary, ...]
    current_graph: CompositionGraph = CompositionGraph()
    assigned_state_effects: tuple[AssignedStateEffect, ...] = ()
    placed_motif_ids: tuple[str, ...] = ()
    cycle_count: int = 0
    rejoin_count: int = 0
    estimated_layout_footprint: LayoutFootprintEstimate = LayoutFootprintEstimate()
    partial_strategic_metrics: PartialStrategicMetrics = PartialStrategicMetrics()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "blueprint_id",
            _normalized_identifier(self.blueprint_id, "blueprint_id"),
        )
        for field_name in (
            "unfulfilled_decision_ids",
            "open_ports",
            "objective_phase_boundaries",
            "assigned_state_effects",
            "placed_motif_ids",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        _non_negative_integer(self.cycle_count, "cycle_count")
        _non_negative_integer(self.rejoin_count, "rejoin_count")
        if not isinstance(self.current_graph, CompositionGraph):
            raise TypeError("current_graph must be a CompositionGraph")
        if not isinstance(self.estimated_layout_footprint, LayoutFootprintEstimate):
            raise TypeError("estimated_layout_footprint must be a LayoutFootprintEstimate")
        if not isinstance(self.partial_strategic_metrics, PartialStrategicMetrics):
            raise TypeError("partial_strategic_metrics must be PartialStrategicMetrics")

    @classmethod
    def initial(cls, blueprint: PuzzleBlueprint) -> "CompositionState":
        """Create the sole canonical empty state for a validated blueprint."""

        if not isinstance(blueprint, PuzzleBlueprint):
            raise TypeError("blueprint must be a PuzzleBlueprint")
        issues = blueprint.validate()
        if issues:
            raise ValueError(f"blueprint is invalid: {issues[0]}")
        return cls(
            blueprint_id=blueprint.id,
            unfulfilled_decision_ids=blueprint.decision_ids,
            open_ports=(),
            objective_phase_boundaries=tuple(
                ObjectivePhaseBoundary(objective.id, objective.sequence_index)
                for objective in blueprint.objectives
            ),
        )

    @property
    def node_count(self) -> int:
        return len(self.current_graph.nodes)

    @property
    def switch_count(self) -> int:
        return self.current_graph.switch_count

    @property
    def is_complete(self) -> bool:
        return not self.unfulfilled_decision_ids and all(
            boundary.entry_node_id is not None and boundary.exit_node_id is not None
            for boundary in self.objective_phase_boundaries
        )

    @property
    def signature(self) -> str:
        """Return a stable signature suitable for visited-state deduplication."""

        payload = {
            "blueprint": self.blueprint_id,
            "unfulfilledDecisions": self.unfulfilled_decision_ids,
            "openPorts": tuple(
                (
                    port.instance_id,
                    port.port.id,
                    port.node_id,
                    port.port_type.value,
                    port.objective_phase_index,
                )
                for port in self.open_ports
            ),
            "phaseBoundaries": tuple(
                (
                    boundary.objective_id,
                    boundary.phase_index,
                    boundary.entry_node_id,
                    boundary.exit_node_id,
                )
                for boundary in self.objective_phase_boundaries
            ),
            "nodes": tuple((node.id, node.role) for node in self.current_graph.nodes),
            "edges": tuple(
                (
                    edge.from_node_id,
                    edge.to_node_id,
                    edge.availability,
                    edge.usage_limit,
                )
                for edge in self.current_graph.edges
            ),
            "stateEffects": tuple(
                (
                    effect.transition_id,
                    effect.edge_role,
                    effect.from_node_id,
                    effect.to_node_id,
                    effect.kind.value,
                )
                for effect in self.assigned_state_effects
            ),
            "motifs": self.placed_motif_ids,
            "cycles": self.cycle_count,
            "rejoins": self.rejoin_count,
            "footprint": (
                self.estimated_layout_footprint.width,
                self.estimated_layout_footprint.height,
            ),
            "metrics": (
                self.partial_strategic_metrics.meaningful_decision_count,
                self.partial_strategic_metrics.adaptive_decision_count,
                self.partial_strategic_metrics.dependency_depth,
                self.partial_strategic_metrics.revisit_count,
                self.partial_strategic_metrics.recovery_count,
            ),
        }
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def evolve(self, **changes: object) -> "CompositionState":
        """Return a validated successor without mutating the search branch."""

        successor = replace(self, **changes)
        issues = successor.validate()
        if issues:
            raise ValueError(f"invalid composition state: {issues[0]}")
        return successor

    def validate(self) -> tuple[str, ...]:
        issues = list(self.current_graph.validate())
        graph_nodes = set(self.current_graph.node_ids)

        if len(self.unfulfilled_decision_ids) != len(set(self.unfulfilled_decision_ids)):
            issues.append("composition_unfulfilled_decisions_not_unique")
        if any(
            not isinstance(decision_id, str) or not decision_id.strip()
            for decision_id in self.unfulfilled_decision_ids
        ):
            issues.append("composition_unfulfilled_decision_id_empty")

        port_ids: set[str] = set()
        for open_port in self.open_ports:
            if not isinstance(open_port, OpenCompositionPort):
                issues.append("composition_open_port_invalid")
                continue
            issues.extend(open_port.validate())
            if open_port.id in port_ids:
                issues.append(f"composition_open_port_duplicate:{open_port.id}")
            port_ids.add(open_port.id)
            if open_port.node_id not in graph_nodes:
                issues.append(
                    f"composition_open_port_node_unknown:{open_port.id}:{open_port.node_id}"
                )

        boundary_indices = tuple(
            boundary.phase_index
            for boundary in self.objective_phase_boundaries
            if isinstance(boundary, ObjectivePhaseBoundary)
        )
        if len(boundary_indices) != len(self.objective_phase_boundaries):
            issues.append("composition_phase_boundary_invalid")
        elif boundary_indices != tuple(range(len(boundary_indices))):
            issues.append("composition_phase_boundaries_not_contiguous")
        objective_ids = tuple(
            boundary.objective_id
            for boundary in self.objective_phase_boundaries
            if isinstance(boundary, ObjectivePhaseBoundary)
        )
        if len(objective_ids) != len(set(objective_ids)):
            issues.append("composition_phase_objectives_not_unique")
        for boundary in self.objective_phase_boundaries:
            if not isinstance(boundary, ObjectivePhaseBoundary):
                continue
            for node_id in (boundary.entry_node_id, boundary.exit_node_id):
                if node_id is not None and node_id not in graph_nodes:
                    issues.append(
                        f"composition_phase_boundary_node_unknown:"
                        f"{boundary.objective_id}:{node_id}"
                    )

        effect_keys: set[tuple[str, str]] = set()
        edge_pairs = {
            (edge.from_node_id, edge.to_node_id) for edge in self.current_graph.edges
        }
        for effect in self.assigned_state_effects:
            if not isinstance(effect, AssignedStateEffect):
                issues.append("composition_state_effect_invalid")
                continue
            key = (effect.transition_id, effect.edge_role)
            if key in effect_keys:
                issues.append(
                    f"composition_state_effect_duplicate:{effect.transition_id}:{effect.edge_role}"
                )
            effect_keys.add(key)
            if (effect.from_node_id, effect.to_node_id) not in edge_pairs:
                issues.append(
                    f"composition_state_effect_edge_unknown:{effect.transition_id}:"
                    f"{effect.from_node_id}:{effect.to_node_id}"
                )

        if any(
            not isinstance(motif_id, str) or not motif_id.strip()
            for motif_id in self.placed_motif_ids
        ):
            issues.append("composition_placed_motif_id_empty")
        return tuple(issues)
