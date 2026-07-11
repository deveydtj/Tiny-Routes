from __future__ import annotations

from dataclasses import dataclass, field

from .graph_recipe import GraphRecipeEdge, GraphRecipeNode


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
    may_introduce_cycle: bool = False
    may_introduce_rejoin: bool = False
    may_introduce_revisit: bool = False
    may_introduce_dead_end: bool = False
    compatibility: MotifCompatibilityConstraints = field(default_factory=MotifCompatibilityConstraints)
    mechanic_metadata: tuple[tuple[str, str], ...] = ()

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
        for edge in self.edges:
            if edge.from_node_id not in known:
                issues.append(f"motif_edge_unknown_from_node:{edge.from_node_id}")
            if edge.to_node_id not in known:
                issues.append(f"motif_edge_unknown_to_node:{edge.to_node_id}")
        if not self.intended_decision_effect.strip():
            issues.append("motif_intended_decision_effect_empty")
        if not self.allowed_difficulties:
            issues.append("motif_allowed_difficulties_empty")
        return tuple(issues)
