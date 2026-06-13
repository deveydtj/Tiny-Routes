from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecipeTopologyRules:
    allows_cycles: bool
    allows_rejoin: bool
    allows_revisit: bool
    allows_return_path: bool
    allows_ring: bool
    allowed_cycle_count: int
    requires_package_gate: bool
    requires_unique_solution: bool
    requires_swift_runtime_validation: bool

    def __post_init__(self) -> None:
        if self.allowed_cycle_count < 0:
            raise ValueError("allowed_cycle_count must be non-negative")
        if not self.allows_cycles and self.allowed_cycle_count != 0:
            raise ValueError("allowed_cycle_count must be 0 when cycles are not allowed")
        if self.allows_cycles and self.allowed_cycle_count < 1:
            raise ValueError("allowed_cycle_count must be at least 1 when cycles are allowed")

    @property
    def allowsCycles(self) -> bool:
        return self.allows_cycles

    @property
    def allowsRejoin(self) -> bool:
        return self.allows_rejoin

    @property
    def allowsRevisit(self) -> bool:
        return self.allows_revisit

    @property
    def allowsReturnPath(self) -> bool:
        return self.allows_return_path

    @property
    def allowsRing(self) -> bool:
        return self.allows_ring

    @property
    def allowedCycleCount(self) -> int:
        return self.allowed_cycle_count

    @property
    def requiresPackageGate(self) -> bool:
        return self.requires_package_gate

    @property
    def requiresUniqueSolution(self) -> bool:
        return self.requires_unique_solution

    @property
    def requiresSwiftRuntimeValidation(self) -> bool:
        return self.requires_swift_runtime_validation

    def to_metadata(self) -> dict[str, object]:
        return {
            "allowsCycles": self.allows_cycles,
            "allowsRejoin": self.allows_rejoin,
            "allowsRevisit": self.allows_revisit,
            "allowsReturnPath": self.allows_return_path,
            "allowsRing": self.allows_ring,
            "allowedCycleCount": self.allowed_cycle_count,
            "requiresPackageGate": self.requires_package_gate,
            "requiresUniqueSolution": self.requires_unique_solution,
            "requiresSwiftRuntimeValidation": self.requires_swift_runtime_validation,
        }
