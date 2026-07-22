"""Fail-closed policy for candidates entering a production V3 transaction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .v3_candidate_pipeline_coordinator import V3CandidatePipelineResult


_STAGE_ORDER = (
    "blueprint",
    "composition",
    "strategy",
    "layout",
    "runtime",
    "quality",
)


@dataclass(frozen=True, order=True)
class ProductionPipelinePolicyIssue:
    code: str
    level_id: str
    detail: str


class ProductionPipelinePolicyError(ValueError):
    """Raised before staging when selected evidence uses a weak path."""


class ProductionPipelinePolicyService:
    """Prove that selected candidates never used a legacy or relaxed fallback.

    Typed V3 stage results prove stage ordering.  These explicit provenance
    fields prove what each handler actually executed, so a handler cannot wrap
    a recipe, direct motif fixture, template, or relaxed playtest path and call
    the result production V3.
    """

    def validate(
        self, pipeline_results: Iterable[V3CandidatePipelineResult]
    ) -> tuple[ProductionPipelinePolicyIssue, ...]:
        results = tuple(pipeline_results)
        issues: list[ProductionPipelinePolicyIssue] = []
        if not results:
            return (
                ProductionPipelinePolicyIssue(
                    "production_pipeline_evidence_missing",
                    "<campaign>",
                    "A production campaign requires selected V3 pipeline evidence.",
                ),
            )

        for index, result in enumerate(results):
            if not isinstance(result, V3CandidatePipelineResult):
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_pipeline_evidence_invalid",
                        f"<selection:{index}>",
                        "Selected evidence is not a V3CandidatePipelineResult.",
                    )
                )
                continue
            level_id = result.request.level_id
            stages = result.stage_results
            if not result.passed or tuple(stage.stage for stage in stages) != _STAGE_ORDER:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_pipeline_incomplete",
                        level_id,
                        "All six locked V3 stages must pass before staging.",
                    )
                )
                continue

            for stage in stages:
                fields = stage.report_fields
                if fields.get("generatorArchitecture") != "production_v3":
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "non_v3_stage_architecture",
                            level_id,
                            f"{stage.stage} did not declare production_v3.",
                        )
                    )
                if fields.get("generatorArchitectureVersion") != 3:
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "non_v3_stage_version",
                            level_id,
                            f"{stage.stage} did not declare architecture version 3.",
                        )
                    )
                if fields.get("fallbackUsed") is not False:
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "production_fallback_used",
                            level_id,
                            f"{stage.stage} did not prove fallbackUsed=false.",
                        )
                    )

            composition = stages[1].report_fields
            if composition.get("execution") != "production_v3_composition":
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "weak_composition_path",
                        level_id,
                        "Composition must execute the blueprint-driven production V3 path.",
                    )
                )
            if composition.get("sourceKind") != "blueprint_composition":
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "weak_composition_source",
                        level_id,
                        "Templates, fixed recipes, and direct motif fixtures are forbidden.",
                    )
                )

            layout = stages[3].report_fields
            if layout.get("manualRepairRequired") is not False:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "manual_repair_path",
                        level_id,
                        "Production layout and road geometry cannot require manual repair.",
                    )
                )

            quality = stages[5].report_fields
            if quality.get("generationProfile") != "production":
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "non_production_quality_profile",
                        level_id,
                        "The relaxed playtest portfolio is not production eligible.",
                    )
                )
            if quality.get("qualityThresholdsRelaxed") is not False:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "relaxed_quality_thresholds",
                        level_id,
                        "Production quality thresholds must be locked and unrelaxed.",
                    )
                )
            if quality.get("manualApprovalRequired") is not False:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "manual_approval_path",
                        level_id,
                        "Production selection cannot depend on manual approval.",
                    )
                )

        return tuple(sorted(set(issues)))

    def require(
        self, pipeline_results: Iterable[V3CandidatePipelineResult]
    ) -> None:
        issues = self.validate(pipeline_results)
        if not issues:
            return
        summary = "; ".join(
            f"{issue.level_id}:{issue.code}" for issue in issues
        )
        raise ProductionPipelinePolicyError(
            f"production_pipeline_policy_failed: {summary}"
        )
