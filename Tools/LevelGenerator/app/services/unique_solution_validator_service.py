from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UniqueSolutionValidationIssue:
    severity: str
    code: str
    message: str
    related_node_id: str | None = None
    related_edge_id: str | None = None


@dataclass(frozen=True)
class UniqueSolutionSearchState:
    """State required for future exhaustive unique-solution traversal."""

    current_node_id: str
    active_edge_by_node_id: tuple[tuple[str, str | None], ...]
    has_collected_package: bool
    visited_node_ids: tuple[str, ...]
    tap_history: tuple[str, ...]
    revisit_counts: tuple[tuple[str, int], ...]
    traversal_depth: int
    current_edge_id: str | None = None
    elapsed_time_seconds: float = 0.0


@dataclass(frozen=True)
class UniqueSolutionValidationConfig:
    max_taps: int
    max_traversal_depth: int
    allow_loops: bool
    allow_rejoins: bool
    allow_revisits: bool
    require_package_gate: bool


@dataclass(frozen=True)
class UniqueSolutionValidationResult:
    requires_unique_solution: bool
    is_exhaustive: bool
    solution_count: int | None = None
    issues: tuple[UniqueSolutionValidationIssue, ...] = field(default_factory=tuple)
    initial_state: UniqueSolutionSearchState | None = None
    config: UniqueSolutionValidationConfig | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


class UniqueSolutionValidatorService:
    """Integration point for strict generated-level unique-solution validation.

    Phase 3 intentionally does not enumerate paths or reject candidates for
    alternate solutions. This service centralizes the state model and call site
    so later phases can replace the placeholder with exhaustive traversal
    without rewiring candidate validation.
    """

    def validate_unique_solution(self, generated_level) -> UniqueSolutionValidationResult:
        topology_rules = self._topology_rules(generated_level)
        requires_unique_solution = bool(topology_rules.get("requiresUniqueSolution", False))
        config = self._config(generated_level, topology_rules)
        initial_state = self._initial_state(generated_level)

        if not requires_unique_solution:
            return UniqueSolutionValidationResult(
                requires_unique_solution=False,
                is_exhaustive=False,
                initial_state=initial_state,
                config=config,
                notes=("unique_solution_not_required_by_topology_rules",),
            )

        return UniqueSolutionValidationResult(
            requires_unique_solution=True,
            is_exhaustive=False,
            solution_count=None,
            initial_state=initial_state,
            config=config,
            notes=(
                "unique_solution_framework_registered",
                "exhaustive_path_enumeration_pending",
            ),
        )

    def validateUniqueSolution(self, generated_level) -> UniqueSolutionValidationResult:
        return self.validate_unique_solution(generated_level)

    def _topology_rules(self, generated_level) -> dict[str, Any]:
        metadata = getattr(generated_level, "mechanic_metadata", {}) or {}
        topology_rules = metadata.get("topologyRules")
        return dict(topology_rules) if isinstance(topology_rules, dict) else {}

    def _config(
        self,
        generated_level,
        topology_rules: dict[str, Any],
    ) -> UniqueSolutionValidationConfig:
        level = generated_level.level_document
        max_taps = max(
            int(getattr(level, "parTaps", 0) or 0),
            len(getattr(generated_level.solution, "actions", ()) or ()),
        )
        max_depth = max(8, len(level.graph.nodes) * 4)
        if topology_rules.get("allowsCycles") or topology_rules.get("allowsRevisit"):
            max_depth = max(max_depth, len(level.graph.nodes) * 8)

        return UniqueSolutionValidationConfig(
            max_taps=max_taps,
            max_traversal_depth=max_depth,
            allow_loops=bool(topology_rules.get("allowsCycles", False)),
            allow_rejoins=bool(topology_rules.get("allowsRejoin", False)),
            allow_revisits=bool(topology_rules.get("allowsRevisit", False)),
            require_package_gate=bool(topology_rules.get("requiresPackageGate", False)),
        )

    def _initial_state(self, generated_level) -> UniqueSolutionSearchState:
        level = generated_level.level_document
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        active_edges: list[tuple[str, str | None]] = []
        for node in level.graph.nodes:
            valid_edges = [
                edge_id
                for edge_id in node.outgoingEdgeIDs
                if edge_id in edge_by_id and edge_by_id[edge_id].fromNodeID == node.id
            ]
            active_edges.append((node.id, valid_edges[0] if valid_edges else None))

        visited = (level.startNodeID,)
        revisit_counts = tuple(sorted(Counter(visited).items()))
        return UniqueSolutionSearchState(
            current_node_id=level.startNodeID,
            active_edge_by_node_id=tuple(sorted(active_edges)),
            has_collected_package=level.startNodeID == level.packageNodeID,
            visited_node_ids=visited,
            tap_history=(),
            revisit_counts=revisit_counts,
            traversal_depth=0,
        )
