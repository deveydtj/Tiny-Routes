from __future__ import annotations

from dataclasses import replace

from ..generation_config import GenerationConfig
from ..level_numbering import format_level_id
from ..models.generation_result import GenerationResult
from ..paths import find_repo_root
from .candidate_rejection_service import CandidateRejectionService
from .candidate_seed_planning_service import CandidateSeedPlanningService
from .swift_test_service import SwiftTestService


class BatchOrchestrationService:
    """Runs candidate pooling, portfolio selection, persistence, and verification.

    The generation façade owns the stage services; this coordinator deliberately
    delegates stage operations so the public API and dependency injection surface
    remain compatible while the batch workflow has one focused home.
    """

    def __init__(self, generator) -> None:
        self.generator = generator

    def __getattr__(self, name):
        return getattr(self.generator, name)

    def generate(self, config: GenerationConfig) -> GenerationResult:
        result = GenerationResult()
        try:
            batch_plan = self.difficulty_curve_service.build_plan(
                config.start_level_number,
                config.count,
                config.difficulty,
            )
            self._validate_template(config.template_name, config)
            self._validate_swift_validation_policy(config, [entry.difficulty for entry in batch_plan.entries])
            self._preflight_output_collisions(config)
        except Exception as exc:
            result.passed = False
            result.messages.append(str(exc))
            self._write_reports(config, result)
            return result
        if not config.dry_run and config.candidate_pool_size == 1:
            result.messages.append(
                "Warning: production generation is using `candidate_pool_size=1`; "
                "use a larger pool for quality-based selection."
            )
        if config.playtest_portfolio:
            result.messages.append(
                "Using playtest portfolio mode: strict structural validation stays enabled; "
                "batch/existing similarity and route-interest selection filters are relaxed for large batches."
            )

        rejection_service = CandidateRejectionService()
        seed_plan = CandidateSeedPlanningService(config.base_seed)
        batch_candidate_pools = {}
        batch_near_misses = {}
        target_level_ids = {
            format_level_id(config.start_level_number + offset)
            for offset in range(config.count)
        }
        existing_signatures = self._load_existing_signatures(config, result, target_level_ids)
        map_seed_graph = self._load_map_seed_graph(config, result)
        if config.map_seed_path is not None and map_seed_graph is None:
            result.passed = False
            self._write_reports(config, result)
            return result

        for offset in range(config.count):
            plan_entry = batch_plan.entries[offset]
            level_number = plan_entry.level_number
            level_id = plan_entry.level_id
            preset = self.difficulty_service.get_preset(plan_entry.difficulty)
            candidate_pool = []
            near_miss_candidates = []

            effective_max_attempts = self._effective_max_attempts(config, preset)
            for attempt in range(effective_max_attempts):
                candidate_seed = seed_plan.candidate_seed(
                    plan_entry.difficulty, config.template_name, level_id, attempt
                )
                from ..random_source import RandomSource
                rng = RandomSource(candidate_seed)
                try:
                    candidates = self._generate_raw_candidates(
                        config=config,
                        level_id=level_id,
                        level_number=level_number,
                        preset=preset,
                        rng=rng,
                        plan_template_weights=plan_entry.template_weights,
                        accepted_candidates=result.accepted,
                        diversity_decisions=result.diversity_adjustment_decisions,
                    )
                except Exception as exc:
                    rejection_code = getattr(exc, "code", "candidate_generation_error")
                    rejection_service.reason_counts[rejection_code] += 1
                    self._record_rejection_by_difficulty(result, preset.name, rejection_code)
                    self._record_generation_error(result)
                    self._record_generation_error_summary(
                        result,
                        level_id=level_id,
                        seed=candidate_seed,
                        difficulty=preset.name,
                        reason=rejection_code,
                        detail=str(exc),
                    )
                    result.messages.append(f"Rejected candidate {level_id} attempt={attempt}: {exc}")
                    continue

                self._record_candidate_generation(result, preset.name, len(candidates))
                for candidate_index, candidate in enumerate(candidates):
                    candidate_rng = RandomSource(seed_plan.map_seed(level_id, attempt, candidate_index))
                    if map_seed_graph is not None:
                        candidate = self.map_seed_adapter.apply_to_generated_level(map_seed_graph, candidate, candidate_rng)

                    self._record_layout_entry(result, candidate)

                    level_path = self.generated_level_repository.level_path(level_id, config.levels_output_dir)
                    solution_path = self.generated_level_repository.solution_path(level_id, config.solutions_output_dir)
                    validation_preset = self._preset_for_candidate_layout(candidate, preset)
                    validation_result = self.validation_service.validate(
                        candidate,
                        preset=validation_preset,
                        level_output_path=level_path,
                        solution_output_path=solution_path,
                        overwrite=config.overwrite or config.dry_run,
                    )
                    self._record_candidate_validation(result, validation_preset.name)
                    candidate.warning_messages = [
                        f"{message.code}: {message.message}"
                        for message in validation_result.messages
                        if message.severity != "error"
                    ]
                    self._annotate_runtime_parity(candidate, config)
                    if rejection_service.can_save(validation_result):
                        runtime_rejection = self._runtime_validation_rejection(candidate)
                        if runtime_rejection is not None:
                            reason, detail = runtime_rejection
                            message = rejection_service.record_custom_rejection(
                                candidate,
                                reason,
                                detail,
                                config.debug_failures_dir,
                            )
                            self._record_rejected_candidate_summary(result, candidate, reason, detail)
                            self._record_rejection_by_difficulty(result, candidate.difficulty, reason)
                            self._record_validation_rejection(result)
                            self._append_rejection_message(result, message)
                            continue

                        candidate_signature = self.signature_service.signature_for(candidate)
                        if config.compare_against_existing:
                            existing_duplicate_result = self.uniqueness_service.check_duplicate(
                                candidate_signature,
                                existing_signatures,
                                threshold=self._existing_duplicate_threshold(config),
                            )
                            if existing_duplicate_result.is_duplicate:
                                message = rejection_service.record_custom_rejection(
                                    candidate,
                                    "candidate_too_similar_to_existing",
                                    existing_duplicate_result.message,
                                    config.debug_failures_dir,
                                )
                                self._record_rejected_candidate_summary(
                                    result,
                                    candidate,
                                    "candidate_too_similar_to_existing",
                                    existing_duplicate_result.message,
                                )
                                self._record_rejection_by_difficulty(
                                    result,
                                    candidate.difficulty,
                                    "candidate_too_similar_to_existing",
                                )
                                self._record_filter_rejection(result)
                                self._append_rejection_message(result, message)
                                continue

                        candidate.candidate_signature = candidate_signature
                        candidate.quality_score = self._score_candidate_quality(
                            candidate,
                            validation_preset,
                            [
                                *(existing_signatures if config.compare_against_existing else []),
                            ],
                            [],
                        )
                        quality_rejection = self._quality_rejection(
                            candidate,
                            config=config,
                            attempt=attempt,
                            accepted_count=len(result.accepted),
                            effective_max_attempts=effective_max_attempts,
                        )
                        if quality_rejection is not None:
                            reason, detail = quality_rejection
                            near_miss_candidates.append(self._candidate_summary(candidate, "rejected", reason, detail))
                            message = rejection_service.record_custom_rejection(
                                candidate,
                                reason,
                                detail,
                                config.debug_failures_dir,
                            )
                            self._record_rejected_candidate_summary(result, candidate, reason, detail)
                            self._record_rejection_by_difficulty(result, candidate.difficulty, reason)
                            self._record_filter_rejection(result)
                            self._append_rejection_message(result, message)
                            continue
                        candidate_pool.append(candidate)
                        result.valid_candidates_after_layout += 1
                        result.repairs_for_valid_candidates += self._successful_layout_repairs(candidate)
                        if self._candidate_pool_ready(candidate_pool, config, preset):
                            break
                        continue

                    first_error = rejection_service.preferred_rejection_message(validation_result)
                    self._record_rejection_by_difficulty(
                        result,
                        candidate.difficulty,
                        first_error.code if first_error is not None else "unknown",
                    )
                    self._record_validation_rejection(result)
                    rejection_service.record_rejection(candidate, validation_result, config.debug_failures_dir)
                    self._record_rejected_candidate_summary(
                        result,
                        candidate,
                        first_error.code if first_error is not None else "unknown",
                        first_error.message if first_error is not None else "No validation detail available.",
                    )

                if self._candidate_pool_ready(candidate_pool, config, preset):
                    break

            if not candidate_pool:
                result.passed = False
                result.messages.append(
                    f"Could not generate valid {level_id} after {effective_max_attempts} attempts."
                )
                break
            batch_candidate_pools[level_id] = tuple(candidate_pool)
            batch_near_misses[level_id] = tuple(near_miss_candidates)

        if result.passed:
            requested_levels = [(entry.level_id, entry.difficulty) for entry in batch_plan.entries]
            try:
                portfolio = self.portfolio_selection_service.select(
                    batch_candidate_pools,
                    requested_levels,
                    existing_signatures=existing_signatures if config.compare_against_existing else (),
                )
            except ValueError as exc:
                result.passed = False
                result.messages.append(str(exc))
            else:
                result.accepted = portfolio.candidates
                for selection in portfolio.selections:
                    level_id = selection.candidate.level_id
                    summary = self._candidate_selection_summary(
                        level_id,
                        selection.candidate,
                        batch_candidate_pools[level_id],
                        batch_near_misses[level_id],
                    )
                    report_fields = dict(summary.report_fields)
                    report_fields["portfolioObjectiveScore"] = selection.objective_score
                    report_fields["portfolioObjectiveComponents"] = {
                        key: round(value, 4) for key, value in selection.components.items()
                    }
                    report_fields["selectionRationale"] = (
                        selection.rationale
                        + f" It ranked above {len(batch_candidate_pools[level_id]) - 1} alternatives."
                    )
                    result.candidate_selection_summaries.append(
                        replace(
                            summary,
                            details=report_fields["selectionRationale"],
                            report_fields=report_fields,
                        )
                    )

        result.add_rejections(dict(rejection_service.reason_counts))

        if result.passed and not config.dry_run:
            self._write_generated_files(config, result)
            result.messages.extend(self._sync_xcode_project(config))

        if result.passed and config.run_swift_tests and not config.dry_run:
            result.messages.extend(self._resource_reference_warnings(config, result))
            swift_summary = SwiftTestService(
                find_repo_root(),
                timeout_seconds=config.swift_timeout_seconds,
                level_ids=tuple(level.level_id for level in result.accepted),
                levels_output_dir=config.levels_output_dir,
                solutions_output_dir=config.solutions_output_dir,
            ).run()
            result.swift_test_summary = swift_summary
            self._apply_swift_validation_summary(config, result, swift_summary)
            if swift_summary.passed is not True:
                result.passed = False
                result.messages.append(swift_summary.summary)
                if swift_summary.failure_reasons:
                    result.messages.append(
                        "Swift runtime parity failure reason(s): "
                        + ", ".join(swift_summary.failure_reasons)
                    )

        self._write_reports(config, result)
        return result
