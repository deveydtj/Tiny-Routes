"""Detected graph evidence for one typed puzzle motif."""

from __future__ import annotations

from dataclasses import dataclass

from .motif_contract import MotifDependencyEffect, MotifStructuralEffect


@dataclass(frozen=True)
class MotifContractEvidence:
    motif_id: str
    detected_structural_effects: tuple[MotifStructuralEffect, ...]
    meaningful_decision_node_ids: tuple[str, ...]
    detected_dependencies: tuple[MotifDependencyEffect, ...]
    observed_state_change_count: int
    explicit_exit_port_ids: tuple[str, ...]
    maximum_outcome_count: int
    behavior_signature: str
    issues: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.issues
