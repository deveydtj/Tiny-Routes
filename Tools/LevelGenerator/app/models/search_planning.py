"""Typed evidence for adaptive V3 search and rejection-driven replanning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _positive_integer(field_name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _identifier(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


@dataclass(frozen=True)
class SearchBreadth:
    """The six bounded search dimensions that may grow when yield is low."""

    blueprint_count: int
    composition_alternatives_per_blueprint: int
    layout_variants: int
    road_shape_variants: int
    candidate_pool_size: int
    attempt_budget: int

    def __post_init__(self) -> None:
        for field_name in (
            "blueprint_count",
            "composition_alternatives_per_blueprint",
            "layout_variants",
            "road_shape_variants",
            "candidate_pool_size",
            "attempt_budget",
        ):
            _positive_integer(field_name, getattr(self, field_name))

    def to_report_dict(self) -> dict[str, int]:
        return {
            "blueprintCount": self.blueprint_count,
            "compositionAlternativesPerBlueprint": (
                self.composition_alternatives_per_blueprint
            ),
            "layoutVariants": self.layout_variants,
            "roadShapeVariants": self.road_shape_variants,
            "candidatePoolSize": self.candidate_pool_size,
            "attemptBudget": self.attempt_budget,
        }


@dataclass(frozen=True)
class SearchYieldEvidence:
    difficulty: str
    archetype: str
    attempted_candidates: int
    accepted_candidates: int
    required_candidates: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "difficulty", _identifier("difficulty", self.difficulty).lower())
        object.__setattr__(self, "archetype", _identifier("archetype", self.archetype).lower())
        for field_name in (
            "attempted_candidates",
            "accepted_candidates",
            "required_candidates",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.required_candidates == 0:
            raise ValueError("required_candidates must be positive")
        if self.accepted_candidates > self.attempted_candidates:
            raise ValueError("accepted_candidates cannot exceed attempted_candidates")

    @property
    def yield_ratio(self) -> float:
        if self.attempted_candidates == 0:
            return 0.0
        return self.accepted_candidates / self.attempted_candidates

    @property
    def pool_shortfall(self) -> int:
        return max(0, self.required_candidates - self.accepted_candidates)

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "difficulty": self.difficulty,
            "archetype": self.archetype,
            "attemptedCandidates": self.attempted_candidates,
            "acceptedCandidates": self.accepted_candidates,
            "requiredCandidates": self.required_candidates,
            "yieldRatio": round(self.yield_ratio, 6),
            "poolShortfall": self.pool_shortfall,
        }


@dataclass(frozen=True)
class SearchBreadthAdjustment:
    sequence: int
    reason: str
    evidence: SearchYieldEvidence
    before: SearchBreadth
    after: SearchBreadth
    changed_dimensions: tuple[str, ...]
    hard_quality_gates_unchanged: bool = True

    def __post_init__(self) -> None:
        _positive_integer("sequence", self.sequence)
        object.__setattr__(self, "reason", _identifier("reason", self.reason))
        if not isinstance(self.evidence, SearchYieldEvidence):
            raise TypeError("evidence must be SearchYieldEvidence")
        if not isinstance(self.before, SearchBreadth) or not isinstance(
            self.after, SearchBreadth
        ):
            raise TypeError("before and after must be SearchBreadth values")
        dimensions = tuple(_identifier("changed dimension", value) for value in self.changed_dimensions)
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("changed_dimensions must be unique")
        if not dimensions:
            raise ValueError("an adjustment must change at least one dimension")
        if not self.hard_quality_gates_unchanged:
            raise ValueError("adaptive breadth may never weaken hard quality gates")
        object.__setattr__(self, "changed_dimensions", dimensions)

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "reason": self.reason,
            "evidence": self.evidence.to_report_dict(),
            "before": self.before.to_report_dict(),
            "after": self.after.to_report_dict(),
            "changedDimensions": list(self.changed_dimensions),
            "hardQualityGatesUnchanged": self.hard_quality_gates_unchanged,
        }


@dataclass(frozen=True)
class AdaptiveSearchBreadthResult:
    breadth: SearchBreadth
    evidence: SearchYieldEvidence
    adjustments: tuple[SearchBreadthAdjustment, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.breadth, SearchBreadth):
            raise TypeError("breadth must be SearchBreadth")
        if not isinstance(self.evidence, SearchYieldEvidence):
            raise TypeError("evidence must be SearchYieldEvidence")
        adjustments = tuple(self.adjustments)
        if any(not isinstance(item, SearchBreadthAdjustment) for item in adjustments):
            raise TypeError("adjustments must contain SearchBreadthAdjustment values")
        object.__setattr__(self, "adjustments", adjustments)

    @property
    def adjusted(self) -> bool:
        return bool(self.adjustments)

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "breadth": self.breadth.to_report_dict(),
            "yieldEvidence": self.evidence.to_report_dict(),
            "adjusted": self.adjusted,
            "automaticSearchAdjustments": [
                item.to_report_dict() for item in self.adjustments
            ],
        }


@dataclass(frozen=True)
class RejectionFeedbackEvent:
    code: str
    stage: str
    archetype: str | None = None
    motif_combination: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _identifier("code", self.code))
        object.__setattr__(self, "stage", _identifier("stage", self.stage))
        if self.archetype is not None:
            object.__setattr__(
                self,
                "archetype",
                _identifier("archetype", self.archetype).lower(),
            )
        combination = tuple(
            sorted({_identifier("motif ID", value) for value in self.motif_combination})
        )
        object.__setattr__(self, "motif_combination", combination)


@dataclass(frozen=True)
class BlueprintPlanningConstraints:
    """Retry constraints changed by feedback without changing puzzle targets."""

    avoided_motif_combinations: tuple[tuple[str, ...], ...] = ()
    layout_profile: str = "standard"
    requested_archetype: str | None = None
    state_space_scale_percent: int = 100
    outgoing_edge_order_variant: int = 0
    preserve_decision_quality: bool = True

    def __post_init__(self) -> None:
        combinations = tuple(
            sorted(
                {
                    tuple(sorted({_identifier("motif ID", value) for value in combination}))
                    for combination in self.avoided_motif_combinations
                    if combination
                }
            )
        )
        object.__setattr__(self, "avoided_motif_combinations", combinations)
        if self.layout_profile not in {"standard", "large", "extra_large"}:
            raise ValueError("layout_profile must be standard, large, or extra_large")
        if self.requested_archetype is not None:
            object.__setattr__(
                self,
                "requested_archetype",
                _identifier("requested_archetype", self.requested_archetype).lower(),
            )
        if (
            not isinstance(self.state_space_scale_percent, int)
            or isinstance(self.state_space_scale_percent, bool)
            or not 50 <= self.state_space_scale_percent <= 100
        ):
            raise ValueError("state_space_scale_percent must be between 50 and 100")
        if (
            not isinstance(self.outgoing_edge_order_variant, int)
            or isinstance(self.outgoing_edge_order_variant, bool)
            or self.outgoing_edge_order_variant < 0
        ):
            raise ValueError("outgoing_edge_order_variant must be non-negative")
        if not self.preserve_decision_quality:
            raise ValueError("feedback planning may not reduce decision quality")

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "avoidedMotifCombinations": [
                list(combination) for combination in self.avoided_motif_combinations
            ],
            "layoutProfile": self.layout_profile,
            "requestedArchetype": self.requested_archetype,
            "stateSpaceScalePercent": self.state_space_scale_percent,
            "outgoingEdgeOrderVariant": self.outgoing_edge_order_variant,
            "preserveDecisionQuality": self.preserve_decision_quality,
        }


@dataclass(frozen=True)
class RejectionFeedbackAdjustment:
    action: str
    trigger_code: str
    occurrence_count: int
    before_value: Any
    after_value: Any
    details: str

    def __post_init__(self) -> None:
        allowed = {
            "avoid_motif_combination",
            "request_larger_layout",
            "select_different_archetype",
            "reduce_state_space",
            "adjust_outgoing_edge_order",
        }
        if self.action not in allowed:
            raise ValueError(f"unknown feedback action: {self.action}")
        object.__setattr__(self, "trigger_code", _identifier("trigger_code", self.trigger_code))
        _positive_integer("occurrence_count", self.occurrence_count)
        object.__setattr__(self, "details", _identifier("details", self.details))

    @property
    def record_key(self) -> tuple[str, str, int]:
        return (self.action, self.trigger_code, self.occurrence_count)

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "triggerCode": self.trigger_code,
            "occurrenceCount": self.occurrence_count,
            "before": self.before_value,
            "after": self.after_value,
            "details": self.details,
            "decisionQualityUnchanged": True,
        }


@dataclass(frozen=True)
class RejectionFeedbackPlan:
    constraints: BlueprintPlanningConstraints
    rejection_counts: tuple[tuple[str, int], ...]
    adjustments: tuple[RejectionFeedbackAdjustment, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.constraints, BlueprintPlanningConstraints):
            raise TypeError("constraints must be BlueprintPlanningConstraints")
        counts = tuple(self.rejection_counts)
        for code, count in counts:
            _identifier("rejection code", code)
            _positive_integer("rejection count", count)
        if tuple(sorted(counts)) != counts or len(dict(counts)) != len(counts):
            raise ValueError("rejection_counts must be sorted and unique by code")
        adjustments = tuple(self.adjustments)
        if any(not isinstance(item, RejectionFeedbackAdjustment) for item in adjustments):
            raise TypeError("adjustments must contain RejectionFeedbackAdjustment values")
        object.__setattr__(self, "rejection_counts", counts)
        object.__setattr__(self, "adjustments", adjustments)

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "planningConstraints": self.constraints.to_report_dict(),
            "rejectionCounts": [
                {"code": code, "count": count} for code, count in self.rejection_counts
            ],
            "automaticPlanningAdjustments": [
                item.to_report_dict() for item in self.adjustments
            ],
        }
