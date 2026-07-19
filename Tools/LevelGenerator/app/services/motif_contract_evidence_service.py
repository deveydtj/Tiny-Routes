"""Exact, name-independent evidence checks for typed puzzle motifs."""

from __future__ import annotations

import hashlib
import json
from collections import deque

from ..models.motif_contract import (
    MotifDependencyEffect,
    MotifEdgeStateChangeKind,
    MotifIncomingObjectiveState,
    MotifStructuralEffect,
)
from ..models.motif_evidence import MotifContractEvidence
from ..models.motif_port import MotifPortType
from ..models.puzzle_motif import PuzzleMotif


class MotifContractEvidenceService:
    """Detect topology, outcomes, state changes, and dependencies from the graph."""

    _difficulty_names = {"tutorial", "easy", "medium", "hard", "expert"}

    def analyze(self, motif: PuzzleMotif) -> MotifContractEvidence:
        issues = list(motif.validate())
        adjacency = self._adjacency(motif)
        reverse = self._reverse_adjacency(motif)
        cyclic_nodes = self._cyclic_nodes(adjacency)
        detected_structural = self._detected_structural_effects(motif, adjacency, reverse, cyclic_nodes)
        meaningful = tuple(
            node_id
            for node_id in sorted(adjacency)
            if len(adjacency[node_id]) >= 2 and self._decision_is_meaningful(motif, node_id, adjacency)
        )
        observed_changes = self._observed_state_changes(motif)
        detected_dependencies = self._detected_dependencies(
            motif, meaningful, cyclic_nodes, observed_changes, adjacency
        )

        if not motif.ports:
            issues.append("motif_evidence_typed_ports_missing")
        if motif.preconditions is None:
            issues.append("motif_evidence_preconditions_missing")
        elif not self._preconditions_are_satisfiable(motif):
            issues.append("motif_evidence_preconditions_unsatisfiable")
        if motif.effects is None:
            issues.append("motif_evidence_effect_contract_missing")
        else:
            for effect in motif.effects.structural_effects:
                if effect not in detected_structural:
                    issues.append(f"motif_evidence_structural_effect_not_detected:{effect.value}")
            for node_id in motif.effects.decision_node_ids:
                if node_id not in meaningful:
                    issues.append(f"motif_evidence_decision_not_meaningful:{node_id}")
            if len(observed_changes) != len(motif.effects.edge_state_changes):
                issues.append("motif_evidence_state_change_not_observed")
            dependency = motif.effects.expected_downstream_dependency
            if dependency is not MotifDependencyEffect.NONE and dependency not in detected_dependencies:
                issues.append(f"motif_evidence_dependency_not_detected:{dependency.value}")
            port_types = {port.port_type for port in motif.ports}
            if motif.effects.introduces_failure_exit and MotifPortType.FAILURE_EXIT not in port_types:
                issues.append("motif_evidence_failure_exit_not_explicit")
            if motif.effects.introduces_recovery_exit and MotifPortType.RECOVERY_EXIT not in port_types:
                issues.append("motif_evidence_recovery_exit_not_explicit")
            detected_cycle = bool(cyclic_nodes)
            detected_revisit = any(node_id in cyclic_nodes for node_id in meaningful)
            detected_rejoin = MotifStructuralEffect.REJOIN in detected_structural
            for label, declared, detected in (
                ("cycle", motif.effects.introduces_cycle, detected_cycle),
                ("revisit", motif.effects.introduces_revisit, detected_revisit),
                ("rejoin", motif.effects.introduces_rejoin, detected_rejoin),
            ):
                if declared != detected:
                    issues.append(f"motif_evidence_{label}_declaration_mismatch")
            if detected_rejoin:
                rejoin_ports = tuple(
                    port for port in motif.ports if port.port_type is MotifPortType.REJOIN_INPUT
                )
                if len(rejoin_ports) < 2:
                    issues.append("motif_evidence_alternate_rejoin_ports_not_explicit")

        if (
            not motif.allowed_difficulties
            or len(motif.allowed_difficulties) != len(set(motif.allowed_difficulties))
            or any(value not in self._difficulty_names for value in motif.allowed_difficulties)
        ):
            issues.append("motif_evidence_difficulty_restrictions_invalid")

        exit_types = {
            MotifPortType.MAIN_ROUTE_EXIT,
            MotifPortType.FAILURE_EXIT,
            MotifPortType.RECOVERY_EXIT,
        }
        explicit_exits = tuple(sorted(port.id for port in motif.ports if port.port_type in exit_types))
        maximum_outcomes = max(
            (len({self._branch_signature(motif, edge.to_node_id, adjacency) for edge in edges})
             for edges in adjacency.values()),
            default=0,
        )
        return MotifContractEvidence(
            motif_id=motif.motif_id,
            detected_structural_effects=detected_structural,
            meaningful_decision_node_ids=meaningful,
            detected_dependencies=detected_dependencies,
            observed_state_change_count=len(observed_changes),
            explicit_exit_port_ids=explicit_exits,
            maximum_outcome_count=maximum_outcomes,
            behavior_signature=self._behavior_signature(motif),
            issues=tuple(dict.fromkeys(issues)),
        )

    def _detected_structural_effects(self, motif, adjacency, reverse, cyclic_nodes):
        effects: list[MotifStructuralEffect] = []
        if motif.edges:
            effects.append(MotifStructuralEffect.SEGMENT)
        if any(len(edges) >= 2 for edges in adjacency.values()):
            effects.append(MotifStructuralEffect.SPLIT)
        if any(len(edges) >= 2 for edges in reverse.values()):
            effects.append(MotifStructuralEffect.REJOIN)
        if any(len(edges) >= 3 for edges in adjacency.values()):
            effects.append(MotifStructuralEffect.HUB)
        if len(cyclic_nodes) >= 3:
            effects.append(MotifStructuralEffect.RING)
        if cyclic_nodes:
            effects.append(MotifStructuralEffect.RETURN_CORRIDOR)
        if any(edge.availability != "always" or edge.usage_limit is not None for edge in motif.edges):
            effects.append(MotifStructuralEffect.CROSS_PHASE_CONNECTOR)
        if (
            MotifStructuralEffect.SPLIT in effects
            and MotifStructuralEffect.REJOIN in effects
        ):
            effects.append(MotifStructuralEffect.LANE_EXPANSION)
        return tuple(effects)

    def _detected_dependencies(self, motif, meaningful, cyclic_nodes, changes, adjacency):
        result: list[MotifDependencyEffect] = []
        if changes:
            result.append(MotifDependencyEffect.OBJECTIVE_STATE)
        if meaningful:
            result.append(MotifDependencyEffect.EARLIER_CHOICE)
        if any(node_id in cyclic_nodes for node_id in meaningful):
            result.append(MotifDependencyEffect.REVISIT)
        return tuple(result)

    @staticmethod
    def _preconditions_are_satisfiable(motif: PuzzleMotif) -> bool:
        assert motif.preconditions is not None
        contract = motif.preconditions
        maximum = contract.maximum_objective_phase_index
        phase = contract.minimum_objective_phase_index
        if maximum is not None and phase > maximum:
            return False
        state = contract.required_incoming_objective_state
        if state is MotifIncomingObjectiveState.ANY:
            state = MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
        return not motif.validate_composition_context(
            difficulty=motif.allowed_difficulties[0],
            objective_phase_index=phase,
            incoming_objective_state=state,
            completed_objective_roles=contract.required_completed_objective_roles,
        )

    @staticmethod
    def _adjacency(motif):
        result = {node.id: [] for node in motif.nodes}
        for edge in motif.edges:
            result[edge.from_node_id].append(edge)
        return result

    @staticmethod
    def _reverse_adjacency(motif):
        result = {node.id: [] for node in motif.nodes}
        for edge in motif.edges:
            result[edge.to_node_id].append(edge)
        return result

    def _decision_is_meaningful(self, motif, node_id, adjacency):
        signatures = {
            self._branch_signature(motif, edge.to_node_id, adjacency)
            for edge in adjacency[node_id]
        }
        return len(signatures) >= 2

    def _branch_signature(self, motif, start, adjacency):
        queue = deque([(start, 0)])
        best = {start: 0}
        outcomes: list[tuple[str, int]] = []
        conditional: list[tuple[str, int]] = []
        while queue:
            node_id, distance = queue.popleft()
            node = next(node for node in motif.nodes if node.id == node_id)
            outgoing = adjacency[node_id]
            if not outgoing or node.role in {
                "package", "pickup", "checkpoint", "delivery", "destination",
                "dead_end", "failure", "recovery",
            }:
                outcomes.append((node.role, distance))
            for edge in outgoing:
                if edge.availability != "always" or edge.usage_limit is not None:
                    conditional.append((
                        f"{edge.availability}:usage={edge.usage_limit}", distance
                    ))
                next_distance = distance + 1
                if next_distance < best.get(edge.to_node_id, 10**9):
                    best[edge.to_node_id] = next_distance
                    queue.append((edge.to_node_id, next_distance))
        return tuple(sorted(outcomes)), tuple(sorted(conditional)), len(best)

    @staticmethod
    def _observed_state_changes(motif):
        if motif.effects is None:
            return ()
        edge_by_pair = {(edge.from_node_id, edge.to_node_id): edge for edge in motif.edges}
        observed = []
        for change in motif.effects.edge_state_changes:
            edge = edge_by_pair.get((change.from_node_id, change.to_node_id))
            if edge is None:
                continue
            before = edge.availability in {"always", "beforePackage"}
            after = edge.availability in {"always", "afterPackage"}
            if change.kind is MotifEdgeStateChangeKind.OPEN and not before and after:
                observed.append(change)
            elif change.kind is MotifEdgeStateChangeKind.CLOSE and before and not after:
                observed.append(change)
            elif change.kind is MotifEdgeStateChangeKind.CONSUME and edge.usage_limit == 1:
                observed.append(change)
        return tuple(observed)

    @staticmethod
    def _cyclic_nodes(adjacency):
        cyclic: set[str] = set()
        for origin in adjacency:
            stack = [edge.to_node_id for edge in adjacency[origin]]
            visited: set[str] = set()
            while stack:
                node_id = stack.pop()
                if node_id == origin:
                    cyclic.add(origin)
                    break
                if node_id in visited:
                    continue
                visited.add(node_id)
                stack.extend(edge.to_node_id for edge in adjacency[node_id])
        return cyclic

    def _behavior_signature(self, motif: PuzzleMotif) -> str:
        """WL-style canonical fingerprint excluding IDs, names, tags, and prose."""

        outgoing = self._adjacency(motif)
        incoming = self._reverse_adjacency(motif)
        ports_by_node: dict[str, list[str]] = {node.id: [] for node in motif.nodes}
        for port in motif.ports:
            ports_by_node[port.node_id].append(port.port_type.value)
        colors = {
            node.id: json.dumps((node.role, sorted(ports_by_node[node.id])))
            for node in motif.nodes
        }
        for _ in range(len(motif.nodes)):
            payloads = {
                node.id: (
                    colors[node.id],
                    tuple(sorted(
                        (f"{edge.availability}:{edge.usage_limit}", colors[edge.to_node_id])
                        for edge in outgoing[node.id]
                    )),
                    tuple(sorted(
                        (f"{edge.availability}:{edge.usage_limit}", colors[edge.from_node_id])
                        for edge in incoming[node.id]
                    )),
                )
                for node in motif.nodes
            }
            palette = {value: index for index, value in enumerate(sorted(set(payloads.values()), key=repr))}
            next_colors = {node_id: str(palette[value]) for node_id, value in payloads.items()}
            if next_colors == colors:
                break
            colors = next_colors
        payload = {
            "nodes": sorted(colors.values()),
            "edges": sorted(
                (
                    colors[edge.from_node_id], colors[edge.to_node_id],
                    edge.availability, edge.usage_limit,
                )
                for edge in motif.edges
            ),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
