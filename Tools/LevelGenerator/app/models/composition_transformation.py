"""Typed requests and proof results for controlled composition variants."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from .composition_state import CompositionState


class CompositionTransformationKind(str, Enum):
    EXCHANGE_PHASE_HUB_EXITS = "exchangePhaseHubExits"
    MOVE_OBJECTIVE_TO_BRANCH = "moveObjectiveToBranch"
    REVERSE_RING_PHASE_ORDER = "reverseRingPhaseOrder"
    CONVERT_FATAL_BRANCH_TO_RECOVERY = "convertFatalBranchToRecovery"
    CHANGE_SHORTCUT_UNLOCK_OBJECTIVE = "changeShortcutUnlockObjective"
    SWAP_BRANCH_COSTS = "swapBranchCosts"
    INSERT_READABILITY_SEGMENT = "insertReadabilitySegment"
    REMOVE_READABILITY_SEGMENT = "removeReadabilitySegment"


@dataclass(frozen=True)
class CompositionTransformation:
    """One deterministic transformation with kind-specific selectors."""

    kind: CompositionTransformationKind
    edge_indices: tuple[int, ...] = ()
    node_ids: tuple[str, ...] = ()
    objective_id: str | None = None
    transition_id: str | None = None
    replacement_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CompositionTransformationKind):
            object.__setattr__(self, "kind", CompositionTransformationKind(self.kind))
        edge_indices = tuple(self.edge_indices)
        if any(
            not isinstance(index, int) or isinstance(index, bool) or index < 0
            for index in edge_indices
        ):
            raise ValueError("edge_indices must contain non-negative integers")
        if len(edge_indices) != len(set(edge_indices)):
            raise ValueError("edge_indices must be unique")
        object.__setattr__(self, "edge_indices", edge_indices)
        node_ids = tuple(node_id.strip() for node_id in self.node_ids)
        if any(not node_id for node_id in node_ids):
            raise ValueError("node_ids cannot contain empty values")
        object.__setattr__(self, "node_ids", node_ids)
        for field_name in ("objective_id", "transition_id", "replacement_id"):
            value = getattr(self, field_name)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{field_name} must not be empty")
                object.__setattr__(self, field_name, value.strip())

    @property
    def id(self) -> str:
        payload = {
            "kind": self.kind.value,
            "edges": self.edge_indices,
            "nodes": self.node_ids,
            "objective": self.objective_id,
            "transition": self.transition_id,
            "replacement": self.replacement_id,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return f"{self.kind.value}:{hashlib.sha256(encoded).hexdigest()[:12]}"


@dataclass(frozen=True)
class CompositionTransformationProof:
    """Adapter result from the exact strategy solver after a transformation."""

    accepted: bool
    proof_signature: str
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise TypeError("accepted must be a bool")
        if not isinstance(self.proof_signature, str) or not self.proof_signature.strip():
            raise ValueError("proof_signature must not be empty")
        object.__setattr__(self, "proof_signature", self.proof_signature.strip())
        reasons = tuple(reason.strip() for reason in self.rejection_reasons)
        if any(not reason for reason in reasons):
            raise ValueError("rejection_reasons cannot contain empty values")
        if self.accepted and reasons:
            raise ValueError("accepted proof cannot contain rejection reasons")
        if not self.accepted and not reasons:
            raise ValueError("rejected proof must contain a rejection reason")
        object.__setattr__(self, "rejection_reasons", tuple(sorted(set(reasons))))


@dataclass(frozen=True)
class CompositionTransformationResult:
    transformation: CompositionTransformation
    status: str
    original_state_signature: str
    candidate_state_signature: str
    solver_proof: CompositionTransformationProof
    transformed_state: CompositionState | None = None

    def __post_init__(self) -> None:
        if self.status not in {"accepted", "solver_rejected"}:
            raise ValueError(f"unknown transformation status: {self.status}")
        if (self.status == "accepted") != (self.transformed_state is not None):
            raise ValueError("only accepted transformations contain transformed_state")
        if (self.status == "accepted") != self.solver_proof.accepted:
            raise ValueError("status must match solver proof")

    @property
    def is_accepted(self) -> bool:
        return self.status == "accepted"
