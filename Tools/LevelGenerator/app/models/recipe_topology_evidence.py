"""Stable evidence emitted by the legacy recipe topology audit."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecipeTopologyEvidence:
    family_name: str
    variant_name: str
    claimed_behaviors: tuple[str, ...]
    detected_behaviors: tuple[str, ...]
    status: str
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in {"passed", "failed"}:
            raise ValueError(f"Unknown recipe topology audit status: {self.status}")
        if self.status == "passed" and self.reasons:
            raise ValueError("A passed recipe topology audit cannot contain failure reasons")
        if self.status == "failed" and not self.reasons:
            raise ValueError("A failed recipe topology audit must contain a stable reason")

    @property
    def is_valid(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family_name,
            "variant": self.variant_name,
            "claimedBehaviors": list(self.claimed_behaviors),
            "detectedBehaviors": list(self.detected_behaviors),
            "status": self.status,
            "reasons": list(self.reasons),
        }
