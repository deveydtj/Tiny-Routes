"""Typed hard-gate evidence for production puzzle eligibility."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class ProductionPuzzleGateCheck:
    """One deterministic production requirement and its measured evidence."""

    code: str
    passed: bool
    actual: str
    required: str

    def __post_init__(self) -> None:
        for field_name in ("code", "actual", "required"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
            object.__setattr__(self, field_name, value.strip())
        if not isinstance(self.passed, bool):
            raise ValueError("passed must be a Boolean")


@dataclass(frozen=True)
class UniqueOptimalGateResult:
    """Production-boundary validation of an exact unique-optimal proof."""

    accepted: bool
    proof_rejection_reasons: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted must be a Boolean")
        proof_reasons = tuple(sorted(set(self.proof_rejection_reasons)))
        reasons = tuple(sorted(set(self.rejection_reasons)))
        if self.accepted and (proof_reasons or reasons):
            raise ValueError("an accepted unique-optimal gate cannot have rejection reasons")
        if not self.accepted and reasons != ("unique_optimal_not_proven",):
            raise ValueError(
                "a rejected unique-optimal gate requires unique_optimal_not_proven"
            )
        object.__setattr__(self, "proof_rejection_reasons", proof_reasons)
        object.__setattr__(self, "rejection_reasons", reasons)


@dataclass(frozen=True)
class ProductionPuzzleGateResult:
    """Complete hard-gate result; only accepted candidates may be ranked."""

    checks: tuple[ProductionPuzzleGateCheck, ...]
    rejection_reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        checks = tuple(self.checks)
        codes = tuple(check.code for check in checks)
        if not checks:
            raise ValueError("a production puzzle gate result requires checks")
        if len(codes) != len(set(codes)):
            raise ValueError("production puzzle gate check codes must be unique")
        expected = tuple(sorted(check.code for check in checks if not check.passed))
        reasons = tuple(sorted(set(self.rejection_reasons)))
        if reasons != expected:
            raise ValueError("rejection_reasons must exactly match failed checks")
        object.__setattr__(self, "checks", checks)
        object.__setattr__(self, "rejection_reasons", reasons)

    @property
    def accepted(self) -> bool:
        return not self.rejection_reasons

    @property
    def ranking_eligible(self) -> bool:
        """A preference score may be calculated only after every hard gate passes."""

        return self.accepted

    def check_for(self, code: str) -> ProductionPuzzleGateCheck:
        for check in self.checks:
            if check.code == code:
                return check
        raise KeyError(code)
