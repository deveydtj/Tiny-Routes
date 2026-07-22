"""One-path orchestration for complete transactional V3 campaign runs."""

from __future__ import annotations

import json
import secrets
from dataclasses import replace
from pathlib import Path
from typing import Callable

from ..models.candidate_pool import CandidatePoolRequest, CandidatePoolSlot
from ..models.production_campaign import (
    ProductionCampaignConfig,
    ProductionCampaignResult,
)
from ..repositories.existing_level_repository import ExistingLevelRepository
from .campaign_portfolio_service import CampaignPortfolioService
from .candidate_pool_service import CandidatePoolService
from .difficulty_curve_service import DifficultyCurveService
from .generator_health_metrics_service import GeneratorHealthMetricsService
from .production_staged_corpus_validation_service import (
    ProductionStagedCorpusValidationService,
)
from .production_staged_output_service import ProductionStagedOutputService
from .production_staging_service import ProductionStagingService
from .production_pipeline_policy_service import ProductionPipelinePolicyService
from .reproducibility_bundle_service import ReproducibilityBundleService
from .quality_profile_service import QualityProfileService
from .transactional_promotion_service import TransactionalPromotionService


ProgressCallback = Callable[[str, str], None]


class ProductionCampaignService:
    """Fill, verify, and atomically promote an entire V3 campaign.

    The candidate pipeline is injected because its six stage handlers are the
    production architecture boundary.  No legacy level/recipe generator is a
    permitted fallback when that dependency is unavailable or rejects a run.
    """

    def __init__(
        self,
        candidate_pipeline=None,
        *,
        candidate_pool_service=None,
        portfolio_service=None,
        staged_output_service: ProductionStagedOutputService | None = None,
        validation_service: ProductionStagedCorpusValidationService | None = None,
        promotion_service: TransactionalPromotionService | None = None,
        existing_level_repository: ExistingLevelRepository | None = None,
        difficulty_curve_service: DifficultyCurveService | None = None,
        run_id_factory: Callable[[int], str] | None = None,
        seed_factory: Callable[[], int] | None = None,
        reproducibility_bundle_service: ReproducibilityBundleService | None = None,
        health_metrics_service: GeneratorHealthMetricsService | None = None,
        quality_profile_service: QualityProfileService | None = None,
        pipeline_policy_service: ProductionPipelinePolicyService | None = None,
    ) -> None:
        if candidate_pool_service is None and candidate_pipeline is not None:
            candidate_pool_service = CandidatePoolService(candidate_pipeline)
        self.candidate_pool_service = candidate_pool_service
        self.portfolio_service = portfolio_service
        self.staged_output_service = (
            staged_output_service or ProductionStagedOutputService()
        )
        self.validation_service = (
            validation_service or ProductionStagedCorpusValidationService()
        )
        self.promotion_service = promotion_service or TransactionalPromotionService()
        self.existing_level_repository = (
            existing_level_repository or ExistingLevelRepository()
        )
        self.difficulty_curve_service = (
            difficulty_curve_service or DifficultyCurveService()
        )
        self.run_id_factory = run_id_factory or self._default_run_id
        self.seed_factory = seed_factory or (lambda: secrets.randbits(63))
        self.reproducibility_bundle_service = (
            reproducibility_bundle_service or ReproducibilityBundleService()
        )
        self.health_metrics_service = (
            health_metrics_service or GeneratorHealthMetricsService()
        )
        self.quality_profile_service = quality_profile_service or QualityProfileService()
        self.pipeline_policy_service = (
            pipeline_policy_service or ProductionPipelinePolicyService()
        )

    def run(
        self,
        config: ProductionCampaignConfig,
        *,
        progress: ProgressCallback | None = None,
    ) -> ProductionCampaignResult:
        if not isinstance(config, ProductionCampaignConfig):
            raise TypeError("config must be a ProductionCampaignConfig")
        quality_profile = self.quality_profile_service.load(
            config.quality_profile_version
        )
        seed = config.seed if config.seed is not None else self.seed_factory()
        run_id = self.run_id_factory(seed)
        staging = ProductionStagingService(config.staging_root)
        workspace = staging.create_workspace(
            run_id,
            seed=seed,
            config_snapshot=config.snapshot(resolved_seed=seed),
        )
        selected_count = 0
        pool_result = None
        candidates: tuple[object, ...] = ()
        selected_pipeline_results: tuple[object, ...] = ()

        try:
            self._progress(progress, "planning", "Resolving the campaign plan")
            if self.candidate_pool_service is None:
                raise RuntimeError(
                    "production_v3_pipeline_unavailable: no V3 candidate pipeline "
                    "was configured; legacy fallback is forbidden"
                )
            batch_plan = self.difficulty_curve_service.build_plan(
                config.start_level_number,
                config.count,
                config.difficulty,
            )
            slots = tuple(
                CandidatePoolSlot(entry.level_id, entry.difficulty)
                for entry in batch_plan.entries
            )
            pool_request = CandidatePoolRequest(
                slots=slots,
                candidates_per_slot=config.candidates_per_slot,
                max_attempts_per_slot=config.max_attempts_per_slot,
                wave_size=config.wave_size,
                base_seed=seed,
                max_workers=config.candidate_workers,
                global_attempt_budget=config.global_attempt_budget,
            )

            self._progress(progress, "candidate_pool", "Building candidate pools")
            pool_result = self.candidate_pool_service.build(pool_request)
            if not pool_result.complete:
                constrained = ", ".join(pool_result.constrained_level_ids)
                raise RuntimeError(
                    "candidate_pool_incomplete: no partial campaign can be "
                    f"promoted; constrained slots: {constrained}"
                )

            self._progress(progress, "portfolio", "Selecting the complete portfolio")
            portfolio_service = self.portfolio_service or CampaignPortfolioService(
                self.candidate_pool_service
            )
            existing = self.existing_level_repository.load_existing_levels(
                config.levels_output_dir,
                config.solutions_output_dir,
                config.production_manifest_path,
            )
            portfolio = portfolio_service.select_with_backtracking(
                pool_result,
                pool_request,
                existing_signatures=existing.signatures,
            )
            candidates = tuple(portfolio.candidates)
            pool_result = portfolio.candidate_pools
            selected_count = len(candidates)
            if selected_count != config.count:
                raise RuntimeError(
                    "portfolio_incomplete: selected candidate count does not match "
                    "the requested campaign"
                )
            selected_pipeline_results = tuple(
                portfolio.candidate_pools.pipeline_result_for(candidate)
                for candidate in candidates
            )
            self.pipeline_policy_service.require(selected_pipeline_results)

            self._progress(progress, "staging", "Writing the complete corpus to staging")
            self.staged_output_service.write_selected_candidates(
                workspace,
                candidates,
                production_levels_dir=config.levels_output_dir,
                production_solutions_dir=config.solutions_output_dir,
                production_manifest_path=config.production_manifest_path,
            )

            self._progress(progress, "validation", "Validating staged Python and Swift evidence")
            validation = self.validation_service.validate(
                workspace,
                selected_pipeline_results,
                run_swift_tests=True,
                swift_timeout_seconds=config.swift_timeout_seconds,
            )
            if not validation.passed:
                failed_manifest = replace(validation.manifest, status="failed_no_changes")
                failed_manifest.write(workspace.run_manifest_path)
                reasons = "; ".join(
                    f"{issue.code}: {issue.detail}" for issue in validation.issues
                )
                raise RuntimeError(f"staged_validation_failed: {reasons}")

            self._progress(progress, "promotion", "Promoting the validated corpus atomically")
            promotion = self.promotion_service.promote(workspace)
            if not promotion.completed:
                result = ProductionCampaignResult(
                    status=promotion.status,
                    run_id=run_id,
                    seed=seed,
                    requested_count=config.count,
                    selected_count=selected_count,
                    workspace_path=workspace.root,
                    quality_profile_version=quality_profile.version,
                    quality_profile_fingerprint=quality_profile.fingerprint,
                    promoted_paths=promotion.promoted_paths,
                    failure_reason=promotion.failure_reason,
                )
                result = self._with_report(
                    workspace,
                    result,
                    config=config,
                    pool_result=pool_result,
                    candidates=candidates,
                    selected_pipeline_results=selected_pipeline_results,
                )
                self._progress(progress, result.status, result.failure_reason or result.status)
                return result

            result = ProductionCampaignResult(
                status="completed",
                run_id=run_id,
                seed=seed,
                requested_count=config.count,
                selected_count=selected_count,
                workspace_path=workspace.root,
                quality_profile_version=quality_profile.version,
                quality_profile_fingerprint=quality_profile.fingerprint,
                promoted_paths=promotion.promoted_paths,
            )
            result = self._with_report(
                workspace,
                result,
                config=config,
                pool_result=pool_result,
                candidates=candidates,
                selected_pipeline_results=selected_pipeline_results,
            )
            self._progress(progress, "completed", "Production campaign completed")
            return result
        except Exception as error:
            result = ProductionCampaignResult(
                status="failed_no_changes",
                run_id=run_id,
                seed=seed,
                requested_count=config.count,
                selected_count=selected_count,
                workspace_path=workspace.root,
                quality_profile_version=quality_profile.version,
                quality_profile_fingerprint=quality_profile.fingerprint,
                failure_reason=str(error) or error.__class__.__name__,
            )
            result = self._with_report(
                workspace,
                result,
                config=config,
                pool_result=pool_result,
                candidates=candidates,
                selected_pipeline_results=selected_pipeline_results,
            )
            self._progress(progress, "failed_no_changes", result.failure_reason or "failed")
            return result

    @staticmethod
    def _default_run_id(seed: int) -> str:
        return f"production-{seed}-{secrets.token_hex(6)}"

    @staticmethod
    def _progress(
        callback: ProgressCallback | None,
        stage: str,
        message: str,
    ) -> None:
        if callback is not None:
            try:
                callback(stage, message)
            except Exception:
                # Observability must never alter the transactional outcome.
                pass

    def _with_report(
        self,
        workspace,
        result: ProductionCampaignResult,
        *,
        config: ProductionCampaignConfig,
        pool_result: object | None,
        candidates: tuple[object, ...],
        selected_pipeline_results: tuple[object, ...],
    ) -> ProductionCampaignResult:
        result = self._with_observability(
            workspace,
            result,
            config=config,
            pool_result=pool_result,
            candidates=candidates,
            selected_pipeline_results=selected_pipeline_results,
        )
        try:
            return replace(result, report_path=self._write_report(workspace, result))
        except Exception:
            # A report-write failure after successful promotion cannot truthfully
            # turn a completed production transaction into failed_no_changes.
            return result

    def _with_observability(
        self,
        workspace,
        result: ProductionCampaignResult,
        *,
        config: ProductionCampaignConfig,
        pool_result: object | None,
        candidates: tuple[object, ...],
        selected_pipeline_results: tuple[object, ...],
    ) -> ProductionCampaignResult:
        bundle_path = result.reproducibility_bundle_path
        health_path = result.health_report_path
        try:
            bundle_path = self.reproducibility_bundle_service.write_run_bundle(
                workspace,
                root_seed=result.seed,
                request_configuration=config.snapshot(resolved_seed=result.seed),
                pool_result=pool_result,
                selected_pipeline_results=selected_pipeline_results,
                run_status=result.status,
                failure_reason=result.failure_reason,
            )
        except Exception:
            pass
        if pool_result is not None:
            try:
                health = self.health_metrics_service.build(
                    pool_result,
                    root_seed=result.seed,
                    selected_candidates=candidates,
                    run_completed=result.passed,
                )
                health_path = self.health_metrics_service.write(
                    health,
                    workspace.require_path(
                        workspace.reports_dir / "generator_health_report.json"
                    ),
                )
            except Exception:
                pass
        return replace(
            result,
            reproducibility_bundle_path=bundle_path,
            health_report_path=health_path,
        )

    def _write_report(
        self,
        workspace,
        result: ProductionCampaignResult,
    ) -> Path:
        path = workspace.reports_dir / "production_campaign_result.json"
        reported_result = replace(result, report_path=path)
        payload = json.dumps(reported_result.to_dict(), indent=2, sort_keys=True) + "\n"
        path = self.staged_output_service.write_report(
            workspace,
            "production_campaign_result.json",
            payload,
        )
        summary = (
            f"# Tiny Routes Production Campaign\n\n"
            f"- Status: `{result.status}`\n"
            f"- Run ID: `{result.run_id}`\n"
            f"- Seed: `{result.seed}`\n"
            f"- Requested: {result.requested_count}\n"
            f"- Selected: {result.selected_count}\n"
            f"- Quality profile: `{result.quality_profile_version}`\n"
            f"- Quality profile fingerprint: `{result.quality_profile_fingerprint}`\n"
        )
        if result.failure_reason:
            summary += f"- Failure: {result.failure_reason}\n"
        if result.reproducibility_bundle_path:
            summary += (
                f"- Reproduction bundle: `{result.reproducibility_bundle_path}`\n"
            )
        if result.health_report_path:
            summary += f"- Health report: `{result.health_report_path}`\n"
        self.staged_output_service.write_report(
            workspace,
            "production_campaign_result.md",
            summary,
        )
        return path


ProductionCampaignOrchestrationService = ProductionCampaignService
