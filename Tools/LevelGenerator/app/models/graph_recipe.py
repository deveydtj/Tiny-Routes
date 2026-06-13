from __future__ import annotations

import hashlib
import json
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

    def _declared_cycle_count_context_value(self) -> str:
        topology_rules_metadata = self.mechanic_metadata.get("topologyRules")
        if not isinstance(topology_rules_metadata, dict):
            return "missing"
        return self._format_context_value(topology_rules_metadata.get("allowedCycleCount"))

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
