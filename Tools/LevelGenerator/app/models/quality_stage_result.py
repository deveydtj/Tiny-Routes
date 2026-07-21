"""Typed boundary result for final V3 hard gates and candidate ranking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .generated_level import GeneratedLevel
from .generation_quality import GenerationQualityScore
from .production_puzzle_gate import ProductionPuzzleGateResult
from .puzzle_analysis import PuzzleAnalysis
from .stage_result import CandidateStageResult


_STAGE = "quality"
_ACCEPTED_CODE = "quality_accepted"
_INCOMPLETE_CODE = "final_quality_evidence_incomplete"


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def _stable_codes(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        code = _identifier(value, "rejection reason")
        if code not in result:
            result.append(code)
    return tuple(result)


@dataclass(frozen=True)
class QualityStageResult(CandidateStageResult):
    """Final proof-bearing boundary before a candidate enters a pool.

    Strategic, layout, and runtime hard-gate failures are deliberately
    non-compensating: a preference score cannot exist unless the complete hard
    gate accepts the candidate. Rejected candidates may retain a score only
    when they passed every hard gate and then failed a ranking threshold.
    """

    passed: bool = False
    stage: str = _STAGE
    code: str = _INCOMPLETE_CODE
    details: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    report_fields: dict[str, Any] = field(default_factory=dict)
    candidate_id: str = ""
    level_id: str = ""
    seed: int = 0
    difficulty: str = ""
    status: str = "rejected"
    generated_level: GeneratedLevel | None = None
    puzzle_analysis: PuzzleAnalysis | None = None
    hard_gate: ProductionPuzzleGateResult | None = None
    quality_score: GenerationQualityScore | None = None
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.stage != _STAGE:
            raise ValueError(f"stage must be {_STAGE!r}")
        if not isinstance(self.passed, bool):
            raise ValueError("passed must be a Boolean")
        object.__setattr__(
            self,
            "candidate_id",
            _identifier(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(self, "level_id", _identifier(self.level_id, "level_id"))
        object.__setattr__(
            self,
            "difficulty",
            _identifier(self.difficulty, "difficulty").lower(),
        )
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ValueError("seed must be an integer")

        self._validate_artifact_types()
        reasons = _stable_codes(tuple(self.rejection_reasons))
        object.__setattr__(self, "rejection_reasons", reasons)

        gate = self.hard_gate
        gate_reasons = gate.rejection_reasons if gate is not None else ()
        missing_gate_reasons = tuple(
            reason for reason in gate_reasons if reason not in reasons
        )
        if missing_gate_reasons:
            raise ValueError(
                "rejection_reasons must include every failed hard-gate code"
            )
        if gate is not None and not gate.ranking_eligible and self.quality_score is not None:
            raise ValueError("a hard-gate failure cannot have a quality score")

        complete = bool(
            self.generated_level is not None
            and self.puzzle_analysis is not None
            and gate is not None
            and gate.ranking_eligible
            and self.quality_score is not None
        )
        if self.passed:
            if reasons:
                raise ValueError("an accepted quality stage cannot have rejection reasons")
            if not complete:
                raise ValueError("accepted quality stage requires complete accepted evidence")
            if self.status != "accepted":
                raise ValueError("accepted quality stage status must be 'accepted'")
            if self.code != _ACCEPTED_CODE:
                raise ValueError(f"accepted quality stage code must be {_ACCEPTED_CODE!r}")
        else:
            if not reasons:
                raise ValueError("a rejected quality stage requires rejection reasons")
            if self.status != "rejected":
                raise ValueError("rejected quality stage status must be 'rejected'")
            if self.code != reasons[0]:
                raise ValueError("rejected quality stage code must be its first reason")

    def _validate_artifact_types(self) -> None:
        expected_types = (
            ("generated_level", self.generated_level, GeneratedLevel),
            ("puzzle_analysis", self.puzzle_analysis, PuzzleAnalysis),
            ("hard_gate", self.hard_gate, ProductionPuzzleGateResult),
            ("quality_score", self.quality_score, GenerationQualityScore),
        )
        for field_name, value, expected_type in expected_types:
            if value is not None and not isinstance(value, expected_type):
                raise TypeError(
                    f"{field_name} must be a {expected_type.__name__} or None"
                )
        candidate = self.generated_level
        if candidate is not None:
            if candidate.level_id != self.level_id:
                raise ValueError("generated level ID must match the stage level")
            if candidate.seed != self.seed:
                raise ValueError("generated level seed must match the stage seed")
            if candidate.difficulty.lower() != self.difficulty:
                raise ValueError("generated level difficulty must match the stage difficulty")

    @property
    def ranking_eligible(self) -> bool:
        return bool(self.hard_gate is not None and self.hard_gate.ranking_eligible)

    @classmethod
    def accepted(
        cls,
        *,
        candidate_id: str,
        level_id: str,
        seed: int,
        difficulty: str,
        generated_level: GeneratedLevel,
        puzzle_analysis: PuzzleAnalysis,
        hard_gate: ProductionPuzzleGateResult,
        quality_score: GenerationQualityScore,
        details: str | None = None,
        metrics: dict[str, Any] | None = None,
        report_fields: dict[str, Any] | None = None,
    ) -> "QualityStageResult":
        return cls(
            passed=True,
            code=_ACCEPTED_CODE,
            details=details,
            metrics=dict(metrics or {}),
            report_fields=dict(report_fields or {}),
            candidate_id=candidate_id,
            level_id=level_id,
            seed=seed,
            difficulty=difficulty,
            status="accepted",
            generated_level=generated_level,
            puzzle_analysis=puzzle_analysis,
            hard_gate=hard_gate,
            quality_score=quality_score,
        )

    @classmethod
    def rejected(
        cls,
        *,
        candidate_id: str,
        level_id: str,
        seed: int,
        difficulty: str,
        rejection_reasons: tuple[str, ...],
        generated_level: GeneratedLevel | None = None,
        puzzle_analysis: PuzzleAnalysis | None = None,
        hard_gate: ProductionPuzzleGateResult | None = None,
        quality_score: GenerationQualityScore | None = None,
        details: str | None = None,
        metrics: dict[str, Any] | None = None,
        report_fields: dict[str, Any] | None = None,
    ) -> "QualityStageResult":
        reasons = _stable_codes(tuple(rejection_reasons))
        if not reasons:
            reasons = (_INCOMPLETE_CODE,)
        return cls(
            passed=False,
            code=reasons[0],
            details=details,
            metrics=dict(metrics or {}),
            report_fields=dict(report_fields or {}),
            candidate_id=candidate_id,
            level_id=level_id,
            seed=seed,
            difficulty=difficulty,
            status="rejected",
            generated_level=generated_level,
            puzzle_analysis=puzzle_analysis,
            hard_gate=hard_gate,
            quality_score=quality_score,
            rejection_reasons=reasons,
        )

    def to_report_dict(self) -> dict[str, Any]:
        payload = super().to_report_dict()
        candidate = self.generated_level
        analysis = self.puzzle_analysis
        gate = self.hard_gate
        score = self.quality_score
        payload.update(
            {
                "rejectionReasons": list(self.rejection_reasons),
                "rankingEligible": self.ranking_eligible,
                "candidatePresent": candidate is not None,
                "analysis": None
                if analysis is None
                else {
                    "meaningfulDecisionCount": analysis.meaningful_decisions,
                    "planningDecisionCount": analysis.planning_decisions,
                    "adaptiveDecisionCount": analysis.adaptive_decisions,
                    "dependencyDepth": analysis.dependency_depth,
                    "objectivePhaseCount": analysis.objective_phases,
                    "stateChangeCount": analysis.state_changes,
                    "successfulStrategyClassCount": (
                        analysis.successful_strategy_classes
                    ),
                    "optimalAcceptedTaps": analysis.optimal_accepted_taps,
                    "optimalRouteDistance": analysis.optimal_route_distance,
                    "optimalTravelTimeSeconds": (
                        analysis.optimal_travel_time_seconds
                    ),
                    "visualComplexity": analysis.visual_complexity,
                },
                "hardGate": None
                if gate is None
                else {
                    "accepted": gate.accepted,
                    "rankingEligible": gate.ranking_eligible,
                    "rejectionReasons": list(gate.rejection_reasons),
                    "checks": [
                        {
                            "code": check.code,
                            "passed": check.passed,
                            "actual": check.actual,
                            "required": check.required,
                        }
                        for check in gate.checks
                    ],
                },
                "qualityScore": None
                if score is None
                else {
                    "totalScore": score.total_score,
                    "total": score.total,
                    "categoryScores": dict(score.category_scores),
                    "estimatedDifficultyBand": score.estimated_difficulty_band,
                    "penalties": list(score.penalties),
                    "topPositiveFactors": list(score.top_positive_factors),
                    "topNegativeFactors": list(score.top_negative_factors),
                },
            }
        )
        return payload
