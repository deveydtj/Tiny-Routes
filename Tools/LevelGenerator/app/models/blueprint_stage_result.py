"""Typed boundary result for V3 blueprint generation and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .puzzle_blueprint import PuzzleBlueprint
from .puzzle_experience_target import PuzzleExperienceTarget
from .stage_result import CandidateStageResult


_STAGE = "blueprint"
_ACCEPTED_CODE = "blueprint_accepted"
_MISSING_BLUEPRINT_CODE = "blueprint_generation_failed"


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def _stable_codes(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        code = _identifier(value, "validation issue")
        if code not in result:
            result.append(code)
    return tuple(result)


@dataclass(frozen=True)
class BlueprintStageResult(CandidateStageResult):
    """Complete, immutable evidence from the first V3 pipeline boundary.

    The stage retains a rejected blueprint when generation succeeded but
    validation failed. This lets later retry planning inspect the exact intent
    without allowing malformed intent to reach composition.
    """

    passed: bool = False
    stage: str = _STAGE
    code: str = _MISSING_BLUEPRINT_CODE
    details: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    report_fields: dict[str, Any] = field(default_factory=dict)
    candidate_id: str = ""
    level_id: str = ""
    seed: int = 0
    difficulty: str = ""
    status: str = "rejected"
    attempt_index: int = 0
    experience_target: PuzzleExperienceTarget | None = None
    blueprint: PuzzleBlueprint | None = None
    validation_issues: tuple[str, ...] = ()

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
        if (
            not isinstance(self.attempt_index, int)
            or isinstance(self.attempt_index, bool)
            or self.attempt_index < 0
        ):
            raise ValueError("attempt_index must be a non-negative integer")
        if not isinstance(self.experience_target, PuzzleExperienceTarget):
            raise TypeError("experience_target must be a PuzzleExperienceTarget")
        if self.experience_target.difficulty != self.difficulty:
            raise ValueError("experience target difficulty must match the stage difficulty")
        if self.blueprint is not None:
            if not isinstance(self.blueprint, PuzzleBlueprint):
                raise TypeError("blueprint must be a PuzzleBlueprint or None")
            if self.blueprint.experience_target != self.experience_target:
                raise ValueError("blueprint must use the stage experience target")

        issues = _stable_codes(tuple(self.validation_issues))
        if self.blueprint is not None:
            actual_issues = self.blueprint.validate()
            if issues != actual_issues:
                raise ValueError(
                    "validation_issues must exactly match blueprint.validate()"
                )
        elif not issues:
            issues = (_MISSING_BLUEPRINT_CODE,)
        object.__setattr__(self, "validation_issues", issues)

        accepted = self.blueprint is not None and not issues
        if self.passed != accepted:
            raise ValueError("passed must match blueprint validation")
        expected_status = "accepted" if accepted else "rejected"
        if self.status != expected_status:
            raise ValueError(f"status must be {expected_status!r}")
        expected_code = _ACCEPTED_CODE if accepted else issues[0]
        if self.code != expected_code:
            raise ValueError(f"code must be {expected_code!r}")

    @classmethod
    def accepted(
        cls,
        *,
        candidate_id: str,
        level_id: str,
        seed: int,
        difficulty: str,
        attempt_index: int,
        experience_target: PuzzleExperienceTarget,
        blueprint: PuzzleBlueprint,
        details: str | None = None,
        metrics: dict[str, Any] | None = None,
        report_fields: dict[str, Any] | None = None,
    ) -> "BlueprintStageResult":
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
            attempt_index=attempt_index,
            experience_target=experience_target,
            blueprint=blueprint,
            validation_issues=(),
        )

    @classmethod
    def rejected(
        cls,
        *,
        candidate_id: str,
        level_id: str,
        seed: int,
        difficulty: str,
        attempt_index: int,
        experience_target: PuzzleExperienceTarget,
        blueprint: PuzzleBlueprint | None = None,
        validation_issues: tuple[str, ...] = (),
        details: str | None = None,
        metrics: dict[str, Any] | None = None,
        report_fields: dict[str, Any] | None = None,
    ) -> "BlueprintStageResult":
        issues = tuple(validation_issues)
        if blueprint is not None and not issues:
            issues = blueprint.validate()
        if blueprint is None and not issues:
            issues = (_MISSING_BLUEPRINT_CODE,)
        return cls(
            passed=False,
            code=issues[0],
            details=details,
            metrics=dict(metrics or {}),
            report_fields=dict(report_fields or {}),
            candidate_id=candidate_id,
            level_id=level_id,
            seed=seed,
            difficulty=difficulty,
            status="rejected",
            attempt_index=attempt_index,
            experience_target=experience_target,
            blueprint=blueprint,
            validation_issues=issues,
        )

    def to_report_dict(self) -> dict[str, Any]:
        payload = super().to_report_dict()
        blueprint = self.blueprint
        payload.update(
            {
                "attemptIndex": self.attempt_index,
                "validationIssues": list(self.validation_issues),
                "experienceTargetDifficulty": self.experience_target.difficulty,
                "blueprintID": blueprint.id if blueprint is not None else None,
                "blueprintArchetype": (
                    blueprint.archetype if blueprint is not None else None
                ),
                "objectiveCount": len(blueprint.objectives) if blueprint else 0,
                "meaningfulDecisionCount": (
                    len(blueprint.decision_ids) if blueprint else 0
                ),
                "dependencyDepth": (
                    blueprint.decision_graph.dependency_depth if blueprint else 0
                ),
                "stateTransitionCount": (
                    len(blueprint.state_transitions) if blueprint else 0
                ),
            }
        )
        return payload
