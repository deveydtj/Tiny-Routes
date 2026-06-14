from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .abstract_puzzle_solution import AbstractPuzzleSolutionMetadata
from .recipe_topology_rules import RecipeTopologyRules


@dataclass(frozen=True)
class GraphRecipeNode:
    id: str
    role: str = "route"


@dataclass(frozen=True)
class GraphRecipeEdge:
    from_node_id: str
    to_node_id: str


@dataclass(frozen=True)
class GraphRecipe:
    level_id: str
    difficulty: str
    nodes: tuple[GraphRecipeNode, ...]
    edges: tuple[GraphRecipeEdge, ...]
    required_path: tuple[str, ...]
    tap_node_ids: tuple[str, ...]
    package_node_id: str = "package"
    destination_node_id: str = "destination"
    notes: tuple[str, ...] = field(default_factory=tuple)
    family_name: str = "graph_recipe"
    variant_name: str = "default"
    solved_metadata: AbstractPuzzleSolutionMetadata | None = None
    mechanic_tags: tuple[str, ...] = field(default_factory=tuple)
    primary_mechanic_tag: str = ""
    topology_class: str = ""
    topology_rules: RecipeTopologyRules | None = None
    unlock_requirement: str | None = None
    prior_mechanic_dependency: str | None = None
    mechanic_metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        messages: list[str] = []
        node_ids = {node.id for node in self.nodes}
        if self.topology_rules is None:
            messages.append("topology_rules_missing")
        if not self.required_path:
            messages.append("required_path_empty")
            return messages
        if self.required_path[0] != "start":
            messages.append("required_path_must_start_at_start")
        if self.required_path[-1] != self.destination_node_id:
            messages.append("required_path_must_end_at_destination")
        if self.package_node_id not in self.required_path:
            messages.append("required_path_must_visit_package")
        elif self.required_path.index(self.package_node_id) > self.required_path.index(self.destination_node_id):
            messages.append("required_path_must_visit_package_before_destination")
        for node_id in self.required_path:
            if node_id not in node_ids:
                messages.append(f"required_path_unknown_node:{node_id}")
        for edge in self.edges:
            if edge.from_node_id not in node_ids:
                messages.append(f"edge_unknown_from_node:{edge.from_node_id}")
            if edge.to_node_id not in node_ids:
                messages.append(f"edge_unknown_to_node:{edge.to_node_id}")
        edge_pairs = {(edge.from_node_id, edge.to_node_id) for edge in self.edges}
        for from_node_id, to_node_id in zip(self.required_path, self.required_path[1:]):
            if (from_node_id, to_node_id) not in edge_pairs:
                messages.append(f"required_path_missing_edge:{from_node_id}:{to_node_id}")
        messages.extend(self.validate_no_undeclared_cycles())
        messages.extend(self.validate_declared_loops())
        messages.extend(self.validate_declared_rejoins())
        messages.extend(self.validate_declared_revisits())
        return messages

    def validate_no_undeclared_cycles(self) -> list[str]:
        cycles = self._detected_cycles()
        if not cycles:
            return []
        context = self._cycle_validation_context(cycles)
        if self.topology_rules is None:
            return [f"topology_rules_missing_for_cycle_validation:{context}"]
        if not self.topology_rules.allows_cycles:
            return [
                f"undeclared_cycle:{self._cycle_description(cycle)}:{context}"
                for cycle in cycles
            ]
        return [
            f"undeclared_cycle:{self._cycle_description(cycle)}:{context}"
            for cycle in cycles
            if not self._cycle_matches_declared_topology(cycle)
        ]

    def validateNoUndeclaredCycles(self) -> list[str]:
        return self.validate_no_undeclared_cycles()

    def validate_declared_loops(self) -> list[str]:
        cycles = self._detected_cycles()
        messages: list[str] = []
        if self.topology_rules is None:
            if cycles:
                return [
                    f"topology_rules_missing_for_declared_loop_validation:"
                    f"{self._cycle_validation_context(cycles)}"
                ]
            return []

        rules = self.topology_rules
        context = self._cycle_validation_context(cycles)
        messages.extend(self._validate_loop_metadata_consistency(cycles))
        if not cycles:
            return messages

        if len(cycles) > rules.allowed_cycle_count:
            messages.append(f"declared_loop_count_exceeds_allowed:{context}")
        if rules.allows_cycles and rules.allowed_cycle_count <= 0:
            messages.append(f"declared_loop_allowed_count_must_be_positive:{context}")
        if rules.allows_ring and not self._declares_ring_topology():
            messages.append(f"declared_loop_ring_rule_without_ring_topology:{context}")
        if rules.allows_cycles and not (
            rules.allows_ring
            or rules.allows_return_path
            or rules.allows_revisit
            or self._declares_loop_topology()
        ):
            messages.append(f"declared_loop_topology_missing:{context}")

        required_node_ids = set(self.required_path)
        for cycle in cycles:
            cycle_node_ids = set(cycle)
            if not cycle_node_ids.intersection(required_node_ids):
                messages.append(
                    f"declared_loop_disconnected_from_required_route:"
                    f"{self._cycle_description(cycle)}:{context}"
                )
            if not self._cycle_matches_declared_topology(cycle):
                messages.append(f"declared_loop_topology_mismatch:{self._cycle_description(cycle)}:{context}")

        return messages

    def validateDeclaredLoops(self) -> list[str]:
        return self.validate_declared_loops()

    def validate_declared_rejoins(self) -> list[str]:
        rejoins = self._detected_rejoins()
        if self.topology_rules is None:
            if rejoins:
                return [
                    f"topology_rules_missing_for_declared_rejoin_validation:"
                    f"{self._rejoin_validation_context(rejoins)}"
                ]
            return []

        rules = self.topology_rules
        messages: list[str] = []
        context = self._rejoin_validation_context(rejoins)
        messages.extend(self._validate_rejoin_metadata_consistency(rejoins))
        if not rejoins:
            return messages

        if not rules.allows_rejoin:
            return [
                f"undeclared_rejoin:{node_id}:{context}"
                for node_id in rejoins
            ]

        declared_count, count_is_explicit = self._declared_rejoin_count()
        if count_is_explicit and len(rejoins) > declared_count:
            messages.append(f"declared_rejoin_count_exceeds_metadata:{context}")

        declared_node_ids = self._declared_rejoin_node_ids()
        if declared_node_ids is not None and set(declared_node_ids) != set(rejoins):
            messages.append(
                f"declared_rejoin_node_metadata_mismatch:"
                f"metadataNodes={','.join(declared_node_ids) or 'none'}:"
                f"actualNodes={','.join(rejoins) or 'none'}:"
                f"{context}"
            )

        return messages

    def validateDeclaredRejoins(self) -> list[str]:
        return self.validate_declared_rejoins()

    def validate_declared_revisits(self) -> list[str]:
        repeated_nodes = self._repeated_required_path_nodes()
        if self.topology_rules is None:
            if repeated_nodes:
                return [
                    f"topology_rules_missing_for_declared_revisit_validation:"
                    f"{self._revisit_validation_context(repeated_nodes)}"
                ]
            return []

        rules = self.topology_rules
        messages: list[str] = []
        context = self._revisit_validation_context(repeated_nodes)
        messages.extend(self._validate_revisit_metadata_consistency(repeated_nodes))
        if not repeated_nodes:
            return messages

        if not rules.allows_revisit:
            return [
                f"undeclared_revisit:{node_id}:{context}"
                for node_id in repeated_nodes
            ]

        declared_count, count_is_explicit = self._declared_revisit_count()
        actual_count = self._revisit_count()
        if count_is_explicit and actual_count > declared_count:
            messages.append(f"declared_revisit_count_exceeds_metadata:{context}")

        declared_node_ids = self._declared_revisit_node_ids()
        if declared_node_ids is not None and set(declared_node_ids) != set(repeated_nodes):
            messages.append(
                f"declared_revisit_node_metadata_mismatch:"
                f"metadataNodes={','.join(declared_node_ids) or 'none'}:"
                f"actualNodes={','.join(repeated_nodes) or 'none'}:"
                f"{context}"
            )

        repeated_tap_nodes = self._repeated_tap_node_ids()
        if repeated_tap_nodes and self.mechanic_metadata.get("allowsRepeatedTaps") is False:
            messages.append(
                f"declared_revisit_repeated_taps_not_allowed:"
                f"nodes={','.join(repeated_tap_nodes)}:"
                f"{context}"
            )

        return messages

    def validateDeclaredRevisits(self) -> list[str]:
        return self.validate_declared_revisits()

    def _detected_cycles(self) -> tuple[tuple[str, ...], ...]:
        outgoing: dict[str, list[str]] = {}
        for edge in self.edges:
            outgoing.setdefault(edge.from_node_id, []).append(edge.to_node_id)

        cycles: set[tuple[str, ...]] = set()
        node_ids = sorted({node.id for node in self.nodes})
        max_depth = max(1, len(node_ids))

        def visit(start_id: str, current_id: str, path: tuple[str, ...]) -> None:
            if len(path) > max_depth:
                return
            for next_id in outgoing.get(current_id, ()):
                if next_id == start_id:
                    cycles.add(self._canonical_cycle(path))
                    continue
                if next_id in path:
                    continue
                visit(start_id, next_id, (*path, next_id))

        for node_id in node_ids:
            visit(node_id, node_id, (node_id,))
        return tuple(sorted(cycles))

    def _canonical_cycle(self, cycle: tuple[str, ...]) -> tuple[str, ...]:
        if not cycle:
            return cycle
        rotations = [cycle[index:] + cycle[:index] for index in range(len(cycle))]
        return min(rotations)

    def _detected_rejoins(self) -> tuple[str, ...]:
        incoming: dict[str, list[GraphRecipeEdge]] = {}
        outgoing: dict[str, list[str]] = {}
        for edge in self.edges:
            incoming.setdefault(edge.to_node_id, []).append(edge)
            outgoing.setdefault(edge.from_node_id, []).append(edge.to_node_id)

        route_counts = Counter(self.required_path)
        rejoins: list[str] = []
        for node_id, incoming_edges in incoming.items():
            if node_id == "start" or route_counts.get(node_id, 0) > 1:
                continue
            non_cycle_sources = {
                edge.from_node_id
                for edge in incoming_edges
                if not self._can_reach(node_id, edge.from_node_id, outgoing)
            }
            if len(non_cycle_sources) >= 2:
                rejoins.append(node_id)
        return tuple(sorted(rejoins))

    def _can_reach(self, start_id: str, target_id: str, outgoing: dict[str, list[str]]) -> bool:
        if start_id == target_id:
            return True
        stack = [start_id]
        visited: set[str] = set()
        while stack:
            current_id = stack.pop()
            if current_id in visited:
                continue
            visited.add(current_id)
            for next_id in outgoing.get(current_id, ()):
                if next_id == target_id:
                    return True
                if next_id not in visited:
                    stack.append(next_id)
        return False

    def _cycle_matches_declared_topology(self, cycle: tuple[str, ...]) -> bool:
        if self.topology_rules is None or not self.topology_rules.allows_cycles:
            return False
        if self.topology_rules.allows_ring and self._declares_ring_topology():
            return True
        if cycle and set(self.required_path).intersection(cycle) and self._declares_loop_topology():
            return (
                self.topology_rules.allows_revisit
                or self.topology_rules.allows_return_path
            )
        return self._declares_loop_topology() and (
            self.topology_rules.allows_revisit or self.topology_rules.allows_return_path
        )

    def _declares_loop_topology(self) -> bool:
        terms = self._topology_terms()
        return bool(terms.intersection({"loop", "return_loop", "revisit", "repeated_tap"}))

    def _declares_ring_topology(self) -> bool:
        terms = self._topology_terms()
        return bool(terms.intersection({"ring", "ring_route", "four_way_ring"}))

    def _topology_terms(self) -> set[str]:
        terms = {self.topology_class, self.primary_mechanic_tag, self.family_name, self.variant_name}
        terms.update(self.mechanic_tags)
        metadata_topology_class = self.mechanic_metadata.get("topologyClass")
        metadata_primary_mechanic_tag = self.mechanic_metadata.get("primaryMechanicTag")
        if isinstance(metadata_topology_class, str):
            terms.add(metadata_topology_class)
        if isinstance(metadata_primary_mechanic_tag, str):
            terms.add(metadata_primary_mechanic_tag)
        normalized: set[str] = set()
        for term in terms:
            normalized_term = term.strip().lower()
            if not normalized_term:
                continue
            normalized.add(normalized_term)
            normalized.update(part for part in normalized_term.split("_") if part)
        return normalized

    def _validate_loop_metadata_consistency(self, cycles: tuple[tuple[str, ...], ...]) -> list[str]:
        messages: list[str] = []
        topology_rules_metadata = self.mechanic_metadata.get("topologyRules")
        context = self._cycle_validation_context(cycles)
        if self.topology_rules is not None and self.topology_rules.allows_cycles and not isinstance(
            topology_rules_metadata,
            dict,
        ):
            messages.append(f"declared_loop_metadata_missing:{context}")
        if isinstance(topology_rules_metadata, dict) and self.topology_rules is not None:
            if topology_rules_metadata.get("allowsCycles") != self.topology_rules.allows_cycles:
                messages.append(
                    f"declared_loop_metadata_allows_cycles_mismatch:"
                    f"metadataAllowsCycles={self._format_context_value(topology_rules_metadata.get('allowsCycles'))}:"
                    f"ruleAllowsCycles={self._format_context_value(self.topology_rules.allows_cycles)}:"
                    f"{context}"
                )
            if topology_rules_metadata.get("allowedCycleCount") != self.topology_rules.allowed_cycle_count:
                messages.append(
                    f"declared_loop_metadata_allowed_cycle_count_mismatch:"
                    f"metadataAllowedCycleCount="
                    f"{self._format_context_value(topology_rules_metadata.get('allowedCycleCount'))}:"
                    f"ruleAllowedCycleCount={self.topology_rules.allowed_cycle_count}:"
                    f"{context}"
                )
        metadata_topology_class = self.mechanic_metadata.get("topologyClass")
        if (
            isinstance(metadata_topology_class, str)
            and self.topology_class
            and metadata_topology_class.strip().lower() != self.topology_class
        ):
            messages.append(
                f"declared_loop_metadata_topology_class_mismatch:"
                f"metadataTopologyClass={metadata_topology_class}:"
                f"recipeTopologyClass={self.topology_class}:"
                f"{context}"
            )
        return messages

    def _validate_rejoin_metadata_consistency(self, rejoins: tuple[str, ...]) -> list[str]:
        messages: list[str] = []
        topology_rules_metadata = self.mechanic_metadata.get("topologyRules")
        context = self._rejoin_validation_context(rejoins)
        if self.topology_rules is not None and rejoins and not isinstance(topology_rules_metadata, dict):
            messages.append(f"declared_rejoin_metadata_missing:{context}")
        if isinstance(topology_rules_metadata, dict) and self.topology_rules is not None:
            if topology_rules_metadata.get("allowsRejoin") != self.topology_rules.allows_rejoin:
                messages.append(
                    f"declared_rejoin_metadata_allows_rejoin_mismatch:"
                    f"metadataAllowsRejoin={self._format_context_value(topology_rules_metadata.get('allowsRejoin'))}:"
                    f"ruleAllowsRejoin={self._format_context_value(self.topology_rules.allows_rejoin)}:"
                    f"{context}"
                )
        return messages

    def _validate_revisit_metadata_consistency(self, repeated_nodes: tuple[str, ...]) -> list[str]:
        messages: list[str] = []
        topology_rules_metadata = self.mechanic_metadata.get("topologyRules")
        context = self._revisit_validation_context(repeated_nodes)
        if self.topology_rules is not None and repeated_nodes and not isinstance(topology_rules_metadata, dict):
            messages.append(f"declared_revisit_metadata_missing:{context}")
        if isinstance(topology_rules_metadata, dict) and self.topology_rules is not None:
            if topology_rules_metadata.get("allowsRevisit") != self.topology_rules.allows_revisit:
                messages.append(
                    f"declared_revisit_metadata_allows_revisit_mismatch:"
                    f"metadataAllowsRevisit={self._format_context_value(topology_rules_metadata.get('allowsRevisit'))}:"
                    f"ruleAllowsRevisit={self._format_context_value(self.topology_rules.allows_revisit)}:"
                    f"{context}"
                )
        return messages

    def _cycle_description(self, cycle: tuple[str, ...]) -> str:
        if not cycle:
            return ""
        return "->".join((*cycle, cycle[0]))

    def _cycle_validation_context(self, cycles: tuple[tuple[str, ...], ...]) -> str:
        rules = self.topology_rules
        allows_cycles = rules.allows_cycles if rules is not None else "missing"
        allowed_cycle_count = rules.allowed_cycle_count if rules is not None else "missing"
        return (
            f"recipe={self.family_name}/{self.variant_name}:"
            f"allowsCycles={self._format_context_value(allows_cycles)}:"
            f"allowedCycleCount={self._format_context_value(allowed_cycle_count)}:"
            f"actualCycleCount={len(cycles)}:"
            f"declaredCycleCount={self._declared_cycle_count_context_value()}"
        )

    def _rejoin_validation_context(self, rejoins: tuple[str, ...]) -> str:
        rules = self.topology_rules
        allows_rejoin = rules.allows_rejoin if rules is not None else "missing"
        declared_count, _ = self._declared_rejoin_count()
        return (
            f"recipe={self.family_name}/{self.variant_name}:"
            f"allowsRejoin={self._format_context_value(allows_rejoin)}:"
            f"actualRejoinCount={len(rejoins)}:"
            f"declaredRejoinCount={self._format_context_value(declared_count)}:"
            f"rejoinNodes={','.join(rejoins) or 'none'}"
        )

    def _revisit_validation_context(self, repeated_nodes: tuple[str, ...]) -> str:
        rules = self.topology_rules
        allows_revisit = rules.allows_revisit if rules is not None else "missing"
        declared_count, _ = self._declared_revisit_count()
        return (
            f"recipe={self.family_name}/{self.variant_name}:"
            f"allowsRevisit={self._format_context_value(allows_revisit)}:"
            f"actualRevisitCount={self._revisit_count()}:"
            f"declaredRevisitCount={self._format_context_value(declared_count)}:"
            f"repeatedNodes={','.join(repeated_nodes) or 'none'}"
        )

    def _declared_cycle_count_context_value(self) -> str:
        topology_rules_metadata = self.mechanic_metadata.get("topologyRules")
        if not isinstance(topology_rules_metadata, dict):
            return "missing"
        return self._format_context_value(topology_rules_metadata.get("allowedCycleCount"))

    def _declared_rejoin_count(self) -> tuple[int | None, bool]:
        for key in ("declaredRejoinCount", "allowedRejoinCount", "rejoinCount"):
            value = self.mechanic_metadata.get(key)
            if isinstance(value, int) and value >= 0:
                return value, True
        declared_nodes = self._declared_rejoin_node_ids()
        if declared_nodes is not None:
            return len(declared_nodes), True
        if self.topology_rules is not None and self.topology_rules.allows_rejoin:
            return len(self._detected_rejoins()), False
        return 0, False

    def _declared_revisit_count(self) -> tuple[int | None, bool]:
        for key in ("declaredRevisitCount", "allowedRevisitCount", "revisitCount"):
            value = self.mechanic_metadata.get(key)
            if isinstance(value, int) and value >= 0:
                return value, True
        declared_nodes = self._declared_revisit_node_ids()
        if declared_nodes is not None:
            return len(declared_nodes), True
        if self.topology_rules is not None and self.topology_rules.allows_revisit:
            return self._revisit_count(), False
        return 0, False

    def _declared_rejoin_node_ids(self) -> tuple[str, ...] | None:
        return self._declared_node_ids(("declaredRejoinNodeIDs", "rejoinNodeIDs"))

    def _declared_revisit_node_ids(self) -> tuple[str, ...] | None:
        return self._declared_node_ids(("declaredRevisitNodeIDs", "revisitNodeIDs", "repeatedNodeIDs"))

    def _declared_node_ids(self, keys: tuple[str, ...]) -> tuple[str, ...] | None:
        for key in keys:
            value = self.mechanic_metadata.get(key)
            if isinstance(value, (list, tuple)):
                return tuple(sorted(str(node_id) for node_id in value))
        return None

    def _repeated_required_path_nodes(self) -> tuple[str, ...]:
        counts = Counter(self.required_path)
        return tuple(sorted(node_id for node_id, count in counts.items() if count > 1))

    def _repeated_tap_node_ids(self) -> tuple[str, ...]:
        counts = Counter(self.tap_node_ids)
        return tuple(sorted(node_id for node_id, count in counts.items() if count > 1))

    def _revisit_count(self) -> int:
        counts = Counter(self.required_path)
        return sum(count - 1 for count in counts.values() if count > 1)

    def _format_context_value(self, value: Any) -> str:
        if isinstance(value, bool):
            return str(value).lower()
        if value is None:
            return "missing"
        return str(value)

    @property
    def abstract_signature(self) -> str:
        payload = {
            "difficulty": self.difficulty,
            "family": self.family_name,
            "variant": self.variant_name,
            "nodes": [(node.id, node.role) for node in self.nodes],
            "edges": [(edge.from_node_id, edge.to_node_id) for edge in self.edges],
            "requiredPath": list(self.required_path),
            "tapNodeIDs": list(self.tap_node_ids),
            "mechanicTags": list(self.mechanic_tags),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
