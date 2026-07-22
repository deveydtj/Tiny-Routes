"""Fail-closed orchestration for one production V3 candidate attempt."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from ..models.blueprint_stage_result import BlueprintStageResult
from ..models.generated_level import GeneratedLevel
from ..models.quality_stage_result import QualityStageResult
from ..models.stage_result import CandidateStageResult
from ..models.strategy_stage_result import StrategyStageResult


@dataclass(frozen=True)
class V3CandidatePipelineRequest:
    """Stable identity shared by every stage of one candidate attempt."""

    candidate_id: str
    level_id: str
    seed: int
    difficulty: str
    attempt_index: int = 0

    _RETRY_VARIANT_NAMES: ClassVar[tuple[str, ...]] = (
        "blueprint",
        "composition",
        "layout",
        "road_geometry",
    )

    def __post_init__(self) -> None:
        for field_name in ("candidate_id", "level_id", "difficulty"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
            object.__setattr__(self, field_name, value.strip())
        object.__setattr__(self, "difficulty", self.difficulty.lower())
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ValueError("seed must be an integer")
        if (
            not isinstance(self.attempt_index, int)
            or isinstance(self.attempt_index, bool)
            or self.attempt_index < 0
        ):
            raise ValueError("attempt_index must be a non-negative integer")

    def retry_variant_seed(self, variant_name: str) -> int:
        """Return a deterministic, independently named retry-variant seed.

        Candidate attempts already receive distinct root seeds. Naming the four
        production retry axes here prevents a stage from accidentally reusing a
        different stage's random stream and gives reports executable evidence
        that a retry explored more than the rejected candidate verbatim.
        """

        if variant_name not in self._RETRY_VARIANT_NAMES:
            raise ValueError(
                "variant_name must be one of "
                + ", ".join(self._RETRY_VARIANT_NAMES)
            )
        payload = (
            f"production_v3:{self.level_id}:{self.seed}:{self.attempt_index}:"
            f"{variant_name}"
        ).encode("utf-8")
        return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & (
            (1 << 63) - 1
        )

    @property
    def retry_variant_seeds(self) -> dict[str, int]:
        return {
            name: self.retry_variant_seed(name)
            for name in self._RETRY_VARIANT_NAMES
        }


BlueprintStageRunner = Callable[[V3CandidatePipelineRequest], BlueprintStageResult]
CompositionStageRunner = Callable[
    [V3CandidatePipelineRequest, BlueprintStageResult], CandidateStageResult
]
StrategyStageRunner = Callable[
    [V3CandidatePipelineRequest, CandidateStageResult], StrategyStageResult
]
LayoutStageRunner = Callable[
    [V3CandidatePipelineRequest, CandidateStageResult, StrategyStageResult],
    CandidateStageResult,
]
RuntimeStageRunner = Callable[
    [V3CandidatePipelineRequest, CandidateStageResult, StrategyStageResult],
    CandidateStageResult,
]
QualityStageRunner = Callable[
    [
        V3CandidatePipelineRequest,
        BlueprintStageResult,
        CandidateStageResult,
        StrategyStageResult,
        CandidateStageResult,
        CandidateStageResult,
    ],
    QualityStageResult,
]


@dataclass(frozen=True)
class V3CandidatePipelineHandlers:
    """Focused stage implementations consumed by the coordinator."""

    blueprint: BlueprintStageRunner
    composition: CompositionStageRunner
    strategy: StrategyStageRunner
    layout: LayoutStageRunner
    runtime: RuntimeStageRunner
    quality: QualityStageRunner

    def __post_init__(self) -> None:
        for field_name in (
            "blueprint",
            "composition",
            "strategy",
            "layout",
            "runtime",
            "quality",
        ):
            if not callable(getattr(self, field_name)):
                raise TypeError(f"{field_name} stage handler must be callable")


@dataclass(frozen=True)
class V3CandidatePipelineResult:
    """Ordered evidence from every stage reached by one attempt."""

    request: V3CandidatePipelineRequest
    stage_results: tuple[CandidateStageResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.request, V3CandidatePipelineRequest):
            raise TypeError("request must be a V3CandidatePipelineRequest")
        stages = tuple(self.stage_results)
        if not stages:
            raise ValueError("stage_results must not be empty")
        expected_order = (
            "blueprint",
            "composition",
            "strategy",
            "layout",
            "runtime",
            "quality",
        )
        actual_order = tuple(result.stage for result in stages)
        if actual_order != expected_order[: len(actual_order)]:
            raise ValueError("stage_results must follow the V3 candidate stage order")
        if len(stages) > 6:
            raise ValueError("stage_results contains more stages than the V3 pipeline")
        for index, result in enumerate(stages):
            if not isinstance(result, CandidateStageResult):
                raise TypeError("stage_results must contain CandidateStageResult values")
            self._validate_identity(result)
            if index < len(stages) - 1 and not result.passed:
                raise ValueError("no stage may run after a rejected stage")
        if all(result.passed for result in stages) and len(stages) != 6:
            raise ValueError("a passing pipeline result must include all six stages")
        object.__setattr__(self, "stage_results", stages)

    def _validate_identity(self, result: CandidateStageResult) -> None:
        request = self.request
        if result.candidate_id != request.candidate_id:
            raise ValueError("stage candidate ID must match the pipeline request")
        if result.level_id != request.level_id:
            raise ValueError("stage level ID must match the pipeline request")
        if result.seed != request.seed:
            raise ValueError("stage seed must match the pipeline request")
        if result.difficulty.lower() != request.difficulty:
            raise ValueError("stage difficulty must match the pipeline request")

    @property
    def passed(self) -> bool:
        return len(self.stage_results) == 6 and all(
            result.passed for result in self.stage_results
        )

    @property
    def terminal_stage(self) -> str:
        return self.stage_results[-1].stage

    @property
    def code(self) -> str:
        return self.stage_results[-1].code

    @property
    def quality_result(self) -> QualityStageResult | None:
        final = self.stage_results[-1]
        return final if isinstance(final, QualityStageResult) else None

    @property
    def candidate(self) -> GeneratedLevel | None:
        result = self.quality_result
        return result.generated_level if result is not None and result.passed else None

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "candidateID": self.request.candidate_id,
            "levelID": self.request.level_id,
            "seed": self.request.seed,
            "difficulty": self.request.difficulty,
            "attemptIndex": self.request.attempt_index,
            "retryVariantSeeds": self.request.retry_variant_seeds,
            "passed": self.passed,
            "terminalStage": self.terminal_stage,
            "code": self.code,
            "stages": [result.to_report_dict() for result in self.stage_results],
        }


class V3CandidatePipelineCoordinator:
    """Execute the locked V3 stage order and stop at the first rejection.

    Each handler owns one focused architecture boundary. The coordinator owns
    ordering, identity validation, stable exception conversion, and the key
    cost-control invariant that strategy failures never reach layout/runtime.
    """

    _EXPECTED_TYPES = {
        "blueprint": BlueprintStageResult,
        "composition": CandidateStageResult,
        "strategy": StrategyStageResult,
        "layout": CandidateStageResult,
        "runtime": CandidateStageResult,
        "quality": QualityStageResult,
    }

    def __init__(self, handlers: V3CandidatePipelineHandlers) -> None:
        if not isinstance(handlers, V3CandidatePipelineHandlers):
            raise TypeError("handlers must be V3CandidatePipelineHandlers")
        self.handlers = handlers

    def run(self, request: V3CandidatePipelineRequest) -> V3CandidatePipelineResult:
        if not isinstance(request, V3CandidatePipelineRequest):
            raise TypeError("request must be a V3CandidatePipelineRequest")
        results: list[CandidateStageResult] = []

        blueprint = self._invoke("blueprint", request, self.handlers.blueprint, request)
        results.append(blueprint)
        if not blueprint.passed:
            return V3CandidatePipelineResult(request, tuple(results))
        assert isinstance(blueprint, BlueprintStageResult)

        composition = self._invoke(
            "composition",
            request,
            self.handlers.composition,
            request,
            blueprint,
        )
        results.append(composition)
        if not composition.passed:
            return V3CandidatePipelineResult(request, tuple(results))

        strategy = self._invoke(
            "strategy",
            request,
            self.handlers.strategy,
            request,
            composition,
        )
        results.append(strategy)
        if not strategy.passed:
            return V3CandidatePipelineResult(request, tuple(results))
        assert isinstance(strategy, StrategyStageResult)

        layout = self._invoke(
            "layout",
            request,
            self.handlers.layout,
            request,
            composition,
            strategy,
        )
        results.append(layout)
        if not layout.passed:
            return V3CandidatePipelineResult(request, tuple(results))

        runtime = self._invoke(
            "runtime",
            request,
            self.handlers.runtime,
            request,
            layout,
            strategy,
        )
        results.append(runtime)
        if not runtime.passed:
            return V3CandidatePipelineResult(request, tuple(results))

        quality = self._invoke(
            "quality",
            request,
            self.handlers.quality,
            request,
            blueprint,
            composition,
            strategy,
            layout,
            runtime,
        )
        results.append(quality)
        return V3CandidatePipelineResult(request, tuple(results))

    coordinate = run

    def _invoke(
        self,
        stage: str,
        request: V3CandidatePipelineRequest,
        handler: Callable[..., CandidateStageResult],
        *args: object,
    ) -> CandidateStageResult:
        try:
            result = handler(*args)
            self._validate_stage_result(stage, request, result)
            return result
        except Exception as error:
            return self._error_result(stage, request, error)

    def _validate_stage_result(
        self,
        stage: str,
        request: V3CandidatePipelineRequest,
        result: object,
    ) -> None:
        expected_type = self._EXPECTED_TYPES[stage]
        if not isinstance(result, expected_type):
            raise TypeError(
                f"{stage} handler must return {expected_type.__name__}"
            )
        if result.stage != stage:
            raise ValueError(f"{stage} handler returned stage {result.stage!r}")
        if result.candidate_id != request.candidate_id:
            raise ValueError(f"{stage} handler returned a different candidate ID")
        if result.level_id != request.level_id:
            raise ValueError(f"{stage} handler returned a different level ID")
        if result.seed != request.seed:
            raise ValueError(f"{stage} handler returned a different seed")
        if result.difficulty.lower() != request.difficulty:
            raise ValueError(f"{stage} handler returned a different difficulty")
        if stage == "blueprint" and result.attempt_index != request.attempt_index:
            raise ValueError("blueprint handler returned a different attempt index")

    @staticmethod
    def _error_result(
        stage: str,
        request: V3CandidatePipelineRequest,
        error: Exception,
    ) -> CandidateStageResult:
        code = f"{stage}_stage_error"
        return CandidateStageResult(
            passed=False,
            stage=stage,
            code=code,
            details=str(error) or error.__class__.__name__,
            report_fields={"exceptionType": error.__class__.__name__},
            candidate_id=request.candidate_id,
            level_id=request.level_id,
            seed=request.seed,
            difficulty=request.difficulty,
            status="rejected",
        )
