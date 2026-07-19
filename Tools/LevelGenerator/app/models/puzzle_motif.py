from __future__ import annotations

from dataclasses import dataclass, field

from .graph_recipe import GraphRecipeEdge, GraphRecipeNode
from .motif_contract import (
    MotifEffectContract,
    MotifEdgeStateChangeKind,
    MotifGameplayEffect,
    MotifIncomingObjectiveState,
    MotifPreconditionContract,
    MotifStructuralEffect,
)
from .motif_port import MotifPort, MotifPortType


@dataclass(frozen=True)
class MotifCompatibilityConstraints:
    required_entry_roles: tuple[str, ...] = ()
    required_exit_roles: tuple[str, ...] = ()
    incompatible_motif_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PuzzleMotif:
    motif_id: str
    entry_connector: str
    exit_connectors: tuple[str, ...]
    nodes: tuple[GraphRecipeNode, ...]
    edges: tuple[GraphRecipeEdge, ...]
    intended_decision_effect: str
    allowed_difficulties: tuple[str, ...]
    ports: tuple[MotifPort, ...] = ()
    preconditions: MotifPreconditionContract | None = None
    effects: MotifEffectContract | None = None
    may_introduce_cycle: bool = False
    may_introduce_rejoin: bool = False
    may_introduce_revisit: bool = False
    may_introduce_dead_end: bool = False
    compatibility: MotifCompatibilityConstraints = field(default_factory=MotifCompatibilityConstraints)
    mechanic_metadata: tuple[tuple[str, str], ...] = ()

    @property
    def main_route_entry_connector(self) -> str:
        typed = tuple(port for port in self.ports if port.port_type is MotifPortType.MAIN_ROUTE_ENTRY)
        return typed[0].node_id if typed else self.entry_connector

    @property
    def main_route_exit_connectors(self) -> tuple[str, ...]:
        typed = tuple(
            port.node_id for port in self.ports if port.port_type is MotifPortType.MAIN_ROUTE_EXIT
        )
        return typed or self.exit_connectors

    def validate(self) -> tuple[str, ...]:
        issues: list[str] = []
        node_ids = [node.id for node in self.nodes]
        known = set(node_ids)
        if not self.motif_id.strip():
            issues.append("motif_id_empty")
        if len(known) != len(node_ids):
            issues.append("motif_node_ids_not_unique")
        if self.entry_connector not in known:
            issues.append(f"motif_entry_connector_unknown:{self.entry_connector}")
        if not self.exit_connectors:
            issues.append("motif_exit_connectors_empty")
        for connector in self.exit_connectors:
            if connector not in known:
                issues.append(f"motif_exit_connector_unknown:{connector}")
        port_ids: set[str] = set()
        for port in self.ports:
            if not isinstance(port, MotifPort):
                issues.append("motif_port_invalid")
                continue
            issues.extend(port.validate())
            if port.id in port_ids:
                issues.append(f"motif_port_id_duplicate:{port.id}")
            port_ids.add(port.id)
            if port.node_id not in known:
                issues.append(f"motif_port_node_unknown:{port.id}:{port.node_id}")
        if self.ports:
            typed_entries = tuple(
                port for port in self.ports if port.port_type is MotifPortType.MAIN_ROUTE_ENTRY
            )
            typed_exits = tuple(
                port for port in self.ports if port.port_type is MotifPortType.MAIN_ROUTE_EXIT
            )
            if len(typed_entries) != 1:
                issues.append("motif_main_route_entry_port_count_invalid")
            elif typed_entries[0].node_id != self.entry_connector:
                issues.append("motif_main_route_entry_port_connector_mismatch")
            if not typed_exits:
                issues.append("motif_main_route_exit_ports_empty")
            elif tuple(port.node_id for port in typed_exits) != self.exit_connectors:
                issues.append("motif_main_route_exit_port_connectors_mismatch")
        for edge in self.edges:
            if edge.from_node_id not in known:
                issues.append(f"motif_edge_unknown_from_node:{edge.from_node_id}")
            if edge.to_node_id not in known:
                issues.append(f"motif_edge_unknown_to_node:{edge.to_node_id}")
            if edge.availability not in {"always", "beforePackage", "afterPackage"}:
                issues.append(
                    f"motif_edge_unknown_availability:{edge.from_node_id}:"
                    f"{edge.to_node_id}:{edge.availability}"
                )
            if edge.usage_limit is not None and (
                not isinstance(edge.usage_limit, int)
                or isinstance(edge.usage_limit, bool)
                or edge.usage_limit <= 0
            ):
                issues.append(
                    f"motif_edge_usage_limit_invalid:{edge.from_node_id}:{edge.to_node_id}"
                )
        if not self.intended_decision_effect.strip():
            issues.append("motif_intended_decision_effect_empty")
        if not self.allowed_difficulties:
            issues.append("motif_allowed_difficulties_empty")
        if self.preconditions is not None:
            if not isinstance(self.preconditions, MotifPreconditionContract):
                issues.append("motif_preconditions_invalid")
            else:
                issues.extend(self.preconditions.validate())
        if self.effects is not None:
            if not isinstance(self.effects, MotifEffectContract):
                issues.append("motif_effects_invalid")
            else:
                issues.extend(self.effects.validate())
                issues.extend(self._validate_effect_contract(known))
        embedded_package_node = dict(self.mechanic_metadata).get("embeddedPackageNode")
        if embedded_package_node is not None:
            if embedded_package_node not in known:
                issues.append(f"motif_embedded_package_unknown:{embedded_package_node}")
            elif next(node for node in self.nodes if node.id == embedded_package_node).role != "package":
                issues.append(f"motif_embedded_package_role_invalid:{embedded_package_node}")
        return tuple(issues)

    def validate_composition_context(
        self,
        *,
        difficulty: str,
        objective_phase_index: int,
        incoming_objective_state: MotifIncomingObjectiveState | str,
        completed_objective_roles: tuple[str, ...] = (),
        existing_motif_ids: tuple[str, ...] = (),
        existing_effects: tuple[str, ...] = (),
        existing_instance_count: int = 0,
    ) -> tuple[str, ...]:
        """Enforce difficulty, precondition, compatibility, and count limits.

        Composition search is introduced in Phase 5. Keeping this check on the
        motif makes the Phase 3 contracts executable now instead of leaving
        their restrictions as advisory metadata.
        """

        issues: list[str] = []
        if difficulty not in self.allowed_difficulties:
            issues.append(f"motif_difficulty_not_allowed:{self.motif_id}:{difficulty}")
        if not isinstance(objective_phase_index, int) or isinstance(objective_phase_index, bool):
            issues.append(f"motif_objective_phase_invalid:{self.motif_id}")
            return tuple(issues)
        try:
            state = (
                incoming_objective_state
                if isinstance(incoming_objective_state, MotifIncomingObjectiveState)
                else MotifIncomingObjectiveState(incoming_objective_state)
            )
        except ValueError:
            issues.append(f"motif_incoming_objective_state_invalid:{self.motif_id}")
            return tuple(issues)

        if self.preconditions is not None:
            contract = self.preconditions
            if objective_phase_index < contract.minimum_objective_phase_index:
                issues.append(f"motif_objective_phase_too_early:{self.motif_id}")
            if (
                contract.maximum_objective_phase_index is not None
                and objective_phase_index > contract.maximum_objective_phase_index
            ):
                issues.append(f"motif_objective_phase_too_late:{self.motif_id}")
            required_state = contract.required_incoming_objective_state
            if required_state is not MotifIncomingObjectiveState.ANY and state is not required_state:
                issues.append(f"motif_incoming_objective_state_mismatch:{self.motif_id}")
            completed = set(completed_objective_roles)
            for role in contract.required_completed_objective_roles:
                if role not in completed:
                    issues.append(f"motif_required_objective_role_missing:{self.motif_id}:{role}")
            for role in contract.forbidden_completed_objective_roles:
                if role in completed:
                    issues.append(f"motif_forbidden_objective_role_present:{self.motif_id}:{role}")

        for motif_id in self.compatibility.incompatible_motif_ids:
            if motif_id in existing_motif_ids:
                issues.append(f"motif_incompatible_motif:{self.motif_id}:{motif_id}")
        if self.effects is not None:
            for effect in self.effects.incompatible_effects:
                if effect in existing_effects:
                    issues.append(f"motif_incompatible_effect:{self.motif_id}:{effect}")
            limit = self.effects.maximum_instances_per_composition
            if limit is not None and existing_instance_count >= limit:
                issues.append(f"motif_composition_limit_reached:{self.motif_id}:{limit}")
        return tuple(issues)

    def _validate_effect_contract(self, known: set[str]) -> tuple[str, ...]:
        assert self.effects is not None
        issues: list[str] = []
        outgoing_counts: dict[str, int] = {}
        incoming_counts: dict[str, int] = {}
        for edge in self.edges:
            outgoing_counts[edge.from_node_id] = outgoing_counts.get(edge.from_node_id, 0) + 1
            incoming_counts[edge.to_node_id] = incoming_counts.get(edge.to_node_id, 0) + 1
        for node_id in self.effects.completed_objective_node_ids:
            if node_id not in known:
                issues.append(f"motif_effect_objective_node_unknown:{node_id}")
            else:
                role = next(node.role for node in self.nodes if node.id == node_id)
                if role not in {"package", "pickup", "checkpoint", "delivery", "destination", "objective"}:
                    issues.append(f"motif_effect_objective_node_role_invalid:{node_id}")
        for node_id in self.effects.decision_node_ids:
            if node_id not in known:
                issues.append(f"motif_effect_decision_node_unknown:{node_id}")
            elif outgoing_counts.get(node_id, 0) < 2:
                issues.append(f"motif_effect_decision_node_not_branching:{node_id}")
        edge_by_pair = {(edge.from_node_id, edge.to_node_id): edge for edge in self.edges}
        for change in self.effects.edge_state_changes:
            edge = edge_by_pair.get((change.from_node_id, change.to_node_id))
            description = f"{change.from_node_id}:{change.to_node_id}"
            if edge is None:
                issues.append(f"motif_effect_edge_unknown:{description}")
            elif change.kind is MotifEdgeStateChangeKind.OPEN and edge.availability != "afterPackage":
                issues.append(f"motif_effect_open_edge_not_state_gated:{description}")
            elif change.kind is MotifEdgeStateChangeKind.CLOSE and edge.availability != "beforePackage":
                issues.append(f"motif_effect_close_edge_not_state_gated:{description}")
            elif change.kind is MotifEdgeStateChangeKind.CONSUME and edge.usage_limit != 1:
                issues.append(f"motif_effect_consumed_edge_not_one_use:{description}")
            if (
                change.kind is not MotifEdgeStateChangeKind.CONSUME
                and change.trigger_objective_node_id not in self.effects.completed_objective_node_ids
            ):
                issues.append(
                    f"motif_effect_trigger_objective_not_completed:"
                    f"{change.trigger_objective_node_id}"
                )
        declared_flags = (
            ("cycle", self.effects.introduces_cycle, self.may_introduce_cycle),
            ("revisit", self.effects.introduces_revisit, self.may_introduce_revisit),
            ("rejoin", self.effects.introduces_rejoin, self.may_introduce_rejoin),
            ("failure", self.effects.introduces_failure_exit, self.may_introduce_dead_end),
        )
        for name, contracted, legacy in declared_flags:
            if contracted != legacy:
                issues.append(f"motif_effect_{name}_legacy_flag_mismatch")
        if (
            MotifStructuralEffect.SPLIT in self.effects.structural_effects
            and not any(count >= 2 for count in outgoing_counts.values())
        ):
            issues.append("motif_effect_split_not_detected")
        if (
            MotifStructuralEffect.REJOIN in self.effects.structural_effects
            and not any(count >= 2 for count in incoming_counts.values())
        ):
            issues.append("motif_effect_rejoin_not_detected")
        if (
            MotifGameplayEffect.OBJECTIVE_GATE in self.effects.gameplay_effects
            and (
                not self.effects.completed_objective_node_ids
                or not self.effects.edge_state_changes
            )
        ):
            issues.append("motif_effect_objective_gate_evidence_missing")
        return tuple(issues)
