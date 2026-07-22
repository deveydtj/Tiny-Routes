"""Deterministic campaign-wide V3 candidate-pool construction."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib

from ..models.candidate_pool import (
    AttemptBudgetAllocation,
    CampaignCandidatePoolResult,
    CandidatePoolAttempt,
    CandidatePoolRequest,
    CandidateSlotPool,
    GlobalAttemptBudgetReport,
)
from .candidate_signature_service import CandidateSignatureService
from .reproducibility_bundle_service import ReproducibilityBundleService
from .v3_candidate_pipeline_coordinator import V3CandidatePipelineRequest


class CandidatePoolService:
    """Run complete V3 attempts in bounded waves before portfolio selection.

    Rejected pipeline results retain deterministic JSON diagnostics rather than
    live proof graphs. This keeps memory bounded while preserving the evidence
    required for reproduction bundles and health aggregation. Accepted
    candidates keep their complete production signatures and are never selected
    here; campaign optimization is a later boundary.
    """

    def __init__(
        self,
        pipeline,
        signature_service: CandidateSignatureService | None = None,
        reproducibility_bundle_service: ReproducibilityBundleService | None = None,
    ) -> None:
        runner = getattr(pipeline, "run", None)
        if not callable(runner):
            raise TypeError("pipeline must expose a callable run(request) method")
        self.pipeline = pipeline
        self.signature_service = signature_service or CandidateSignatureService()
        self.reproducibility_bundle_service = (
            reproducibility_bundle_service or ReproducibilityBundleService()
        )

    def build(self, request: CandidatePoolRequest) -> CampaignCandidatePoolResult:
        if not isinstance(request, CandidatePoolRequest):
            raise TypeError("request must be a CandidatePoolRequest")

        accepted = {slot.level_id: [] for slot in request.slots}
        attempted = {slot.level_id: 0 for slot in request.slots}
        attempts: list[CandidatePoolAttempt] = []
        attempt_diagnostics: list[dict] = []
        accepted_pipeline_results: list[object] = []
        allocations: list[AttemptBudgetAllocation] = []
        wave_index = 0
        global_budget = request.resolved_global_attempt_budget

        while (
            len(attempts) < global_budget
            and self._has_runnable_slot(request, accepted, attempted)
        ):
            active_before = tuple(
                slot.level_id
                for slot in request.slots
                if len(accepted[slot.level_id]) < request.candidates_per_slot
                and attempted[slot.level_id] < request.max_attempts_per_slot
            )
            planned: list[V3CandidatePipelineRequest] = []
            allocation_counts = {level_id: 0 for level_id in active_before}

            # Allocate in fixed round-robin order before any worker starts. This
            # prevents a fast worker from consuming budget intended for another
            # campaign slot and makes every derived seed independent of timing.
            for _ in range(request.wave_size):
                for slot in request.slots:
                    level_id = slot.level_id
                    if level_id not in allocation_counts:
                        continue
                    if len(attempts) + len(planned) >= global_budget:
                        break
                    allocated = allocation_counts[level_id]
                    if len(accepted[level_id]) + allocated >= request.candidates_per_slot:
                        continue
                    if attempted[level_id] >= request.max_attempts_per_slot:
                        continue
                    attempt_index = attempted[level_id]
                    planned.append(
                        self._pipeline_request(
                            request,
                            level_id,
                            slot.difficulty,
                            attempt_index,
                        )
                    )
                    attempted[level_id] += 1
                    allocation_counts[level_id] += 1
                if len(attempts) + len(planned) >= global_budget:
                    break
            if not planned:
                break

            reason = (
                "initial_equal_allocation"
                if wave_index == 0
                else (
                    "constrained_slot_reallocation"
                    if len(active_before) < len(request.slots)
                    else "candidate_shortfall_retry"
                )
            )
            allocated_so_far = len(attempts)
            for slot in request.slots:
                count = allocation_counts.get(slot.level_id, 0)
                if count:
                    allocated_so_far += count
                    allocations.append(
                        AttemptBudgetAllocation(
                            wave_index=wave_index,
                            level_id=slot.level_id,
                            attempts_allocated=count,
                            reason=reason,
                            remaining_budget_after=global_budget - allocated_so_far,
                        )
                    )

            for pipeline_request, result, pipeline_error in self._execute_requests(
                planned,
                max_workers=request.max_workers,
            ):
                level_id = pipeline_request.level_id
                difficulty = pipeline_request.difficulty
                try:
                    if pipeline_error is not None:
                        raise pipeline_error
                    diagnostic = self._capture_pipeline_result(
                        result, pipeline_request
                    )
                    self._validate_result_identity(result, pipeline_request)
                    passed = bool(getattr(result, "passed", False))
                    terminal_stage = str(
                        getattr(result, "terminal_stage", "pipeline")
                    )
                    code = str(
                        getattr(result, "code", "pipeline_result_invalid")
                    )
                    if passed:
                        signature = self.signature_service.signature_for_pipeline_result(
                            result
                        )
                        candidate = getattr(result, "candidate", None)
                        if candidate is None or candidate.candidate_signature != signature:
                            raise ValueError(
                                "accepted pipeline result did not retain its signature"
                            )
                        accepted[level_id].append(candidate)
                        accepted_pipeline_results.append(result)
                except Exception as error:
                    passed = False
                    terminal_stage = "pipeline"
                    code = "candidate_pipeline_error"
                    diagnostic = self._capture_pipeline_exception(
                        pipeline_request,
                        error,
                    )

                attempts.append(
                    CandidatePoolAttempt(
                        candidate_id=pipeline_request.candidate_id,
                        level_id=level_id,
                        difficulty=difficulty,
                        seed=pipeline_request.seed,
                        attempt_index=pipeline_request.attempt_index,
                        wave_index=wave_index,
                        passed=passed,
                        terminal_stage=terminal_stage,
                        code=code,
                    )
                )
                attempt_diagnostics.append(diagnostic)
            wave_index += 1

        pools = tuple(
            CandidateSlotPool(
                slot=slot,
                target_count=request.candidates_per_slot,
                candidates=tuple(accepted[slot.level_id]),
                attempted_count=attempted[slot.level_id],
            )
            for slot in request.slots
        )
        attempts, attempt_diagnostics = self._sort_attempt_evidence(
            attempts, attempt_diagnostics
        )
        accepted_pipeline_results.sort(
            key=lambda item: getattr(getattr(item, "request", None), "candidate_id", "")
        )
        return CampaignCandidatePoolResult(
            pools=pools,
            attempts=tuple(attempts),
            waves_completed=wave_index,
            accepted_pipeline_results=tuple(accepted_pipeline_results),
            attempt_diagnostics=tuple(attempt_diagnostics),
            attempt_budget=self._budget_report(
                request,
                attempts,
                allocations,
            ),
        )

    def expand(
        self,
        result: CampaignCandidatePoolResult,
        request: CandidatePoolRequest,
        constrained_level_ids,
        *,
        additional_candidates_per_slot: int = 1,
        max_additional_attempts_per_slot: int = 4,
        max_total_attempts: int | None = None,
    ) -> CampaignCandidatePoolResult:
        """Generate only the candidates needed by constrained portfolio slots.

        Attempt indices continue from the original pool, which preserves seed
        determinism while guaranteeing that replenishment does not regenerate a
        candidate already considered by the optimizer.
        """

        if not isinstance(result, CampaignCandidatePoolResult):
            raise TypeError("result must be a CampaignCandidatePoolResult")
        if not isinstance(request, CandidatePoolRequest):
            raise TypeError("request must be a CandidatePoolRequest")
        for field_name, value in (
            ("additional_candidates_per_slot", additional_candidates_per_slot),
            ("max_additional_attempts_per_slot", max_additional_attempts_per_slot),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        if max_total_attempts is not None and (
            not isinstance(max_total_attempts, int)
            or isinstance(max_total_attempts, bool)
            or max_total_attempts <= 0
        ):
            raise ValueError("max_total_attempts must be a positive integer")

        targets = tuple(dict.fromkeys(str(item) for item in constrained_level_ids))
        known_slots = {pool.slot.level_id for pool in result.pools}
        unknown = tuple(level_id for level_id in targets if level_id not in known_slots)
        if unknown:
            raise ValueError(
                "constrained level IDs are not present in the pool: " + ", ".join(unknown)
            )
        if not targets:
            raise ValueError("at least one constrained level ID is required")

        request_slots = {slot.level_id: slot for slot in request.slots}
        if known_slots != set(request_slots):
            raise ValueError("pool result slots do not match the candidate pool request")

        candidates = {
            pool.slot.level_id: list(pool.candidates) for pool in result.pools
        }
        attempted = {
            pool.slot.level_id: pool.attempted_count for pool in result.pools
        }
        original_pools = {pool.slot.level_id: pool for pool in result.pools}
        additions = {level_id: 0 for level_id in targets}
        desired_additions = {
            level_id: (
                original_pools[level_id].shortfall
                if not original_pools[level_id].complete
                else additional_candidates_per_slot
            )
            for level_id in targets
        }
        slot_attempts = {level_id: 0 for level_id in targets}
        attempts = list(result.attempts)
        attempt_diagnostics = list(result.attempt_diagnostics)
        accepted_pipeline_results = list(result.accepted_pipeline_results)
        wave_index = result.waves_completed
        total_new_attempts = 0
        global_budget = request.resolved_global_attempt_budget
        remaining_global_budget = max(0, global_budget - len(attempts))
        expansion_budget = remaining_global_budget
        if max_total_attempts is not None:
            expansion_budget = min(expansion_budget, max_total_attempts)
        allocations = list(
            result.attempt_budget.allocation_changes
            if result.attempt_budget is not None
            else ()
        )

        while total_new_attempts < expansion_budget and any(
            additions[level_id] < desired_additions[level_id]
            and slot_attempts[level_id] < max_additional_attempts_per_slot
            for level_id in targets
        ):
            active = tuple(
                level_id
                for level_id in targets
                if additions[level_id] < desired_additions[level_id]
                and slot_attempts[level_id] < max_additional_attempts_per_slot
            )
            planned: list[V3CandidatePipelineRequest] = []
            allocation_counts = {level_id: 0 for level_id in active}
            for _ in range(request.wave_size):
                for slot in request.slots:
                    level_id = slot.level_id
                    if level_id not in allocation_counts:
                        continue
                    if total_new_attempts + len(planned) >= expansion_budget:
                        break
                    allocated = allocation_counts[level_id]
                    if additions[level_id] + allocated >= desired_additions[level_id]:
                        continue
                    if slot_attempts[level_id] >= max_additional_attempts_per_slot:
                        continue
                    planned.append(
                        self._pipeline_request(
                            request,
                            level_id,
                            slot.difficulty,
                            attempted[level_id],
                        )
                    )
                    attempted[level_id] += 1
                    slot_attempts[level_id] += 1
                    allocation_counts[level_id] += 1
                if total_new_attempts + len(planned) >= expansion_budget:
                    break
            if not planned:
                break

            allocation_reason = (
                "candidate_pool_shortfall_reallocation"
                if any(not original_pools[level_id].complete for level_id in active)
                else "portfolio_constraint_reallocation"
            )
            allocated_so_far = len(attempts)
            for slot in request.slots:
                count = allocation_counts.get(slot.level_id, 0)
                if count:
                    allocated_so_far += count
                    allocations.append(
                        AttemptBudgetAllocation(
                            wave_index=wave_index,
                            level_id=slot.level_id,
                            attempts_allocated=count,
                            reason=allocation_reason,
                            remaining_budget_after=global_budget - allocated_so_far,
                        )
                    )

            for pipeline_request, pipeline_result, pipeline_error in self._execute_requests(
                planned,
                max_workers=request.max_workers,
            ):
                level_id = pipeline_request.level_id
                try:
                    if pipeline_error is not None:
                        raise pipeline_error
                    diagnostic = self._capture_pipeline_result(
                        pipeline_result,
                        pipeline_request,
                    )
                    self._validate_result_identity(pipeline_result, pipeline_request)
                    passed = bool(getattr(pipeline_result, "passed", False))
                    terminal_stage = str(
                        getattr(pipeline_result, "terminal_stage", "pipeline")
                    )
                    code = str(
                        getattr(pipeline_result, "code", "pipeline_result_invalid")
                    )
                    if passed:
                        signature = self.signature_service.signature_for_pipeline_result(
                            pipeline_result
                        )
                        candidate = getattr(pipeline_result, "candidate", None)
                        if candidate is None or candidate.candidate_signature != signature:
                            raise ValueError(
                                "accepted pipeline result did not retain its signature"
                            )
                        candidates[level_id].append(candidate)
                        accepted_pipeline_results.append(pipeline_result)
                        additions[level_id] += 1
                except Exception as error:
                    passed = False
                    terminal_stage = "pipeline"
                    code = "candidate_pipeline_error"
                    diagnostic = self._capture_pipeline_exception(
                        pipeline_request,
                        error,
                    )
                attempts.append(
                    CandidatePoolAttempt(
                        candidate_id=pipeline_request.candidate_id,
                        level_id=level_id,
                        difficulty=pipeline_request.difficulty,
                        seed=pipeline_request.seed,
                        attempt_index=pipeline_request.attempt_index,
                        wave_index=wave_index,
                        passed=passed,
                        terminal_stage=terminal_stage,
                        code=code,
                    )
                )
                attempt_diagnostics.append(diagnostic)
            total_new_attempts += len(planned)
            wave_index += 1

        pools = []
        for pool in result.pools:
            level_id = pool.slot.level_id
            target_count = pool.target_count
            if pool.complete and level_id in additions:
                # A complete pool stays complete even if every replenishment
                # attempt is rejected; only accepted additions enlarge its target.
                target_count += additions[level_id]
            pools.append(
                CandidateSlotPool(
                    slot=pool.slot,
                    target_count=target_count,
                    candidates=tuple(candidates[level_id]),
                    attempted_count=attempted[level_id],
                )
            )
        attempts, attempt_diagnostics = self._sort_attempt_evidence(
            attempts, attempt_diagnostics
        )
        accepted_pipeline_results.sort(
            key=lambda item: getattr(getattr(item, "request", None), "candidate_id", "")
        )
        return CampaignCandidatePoolResult(
            pools=tuple(pools),
            attempts=tuple(attempts),
            waves_completed=wave_index,
            accepted_pipeline_results=tuple(accepted_pipeline_results),
            attempt_diagnostics=tuple(attempt_diagnostics),
            attempt_budget=self._budget_report(
                request,
                attempts,
                allocations,
            ),
        )

    def _execute_requests(
        self,
        requests: list[V3CandidatePipelineRequest],
        *,
        max_workers: int,
    ) -> list[tuple[V3CandidatePipelineRequest, object | None, Exception | None]]:
        """Run a preallocated wave and preserve its deterministic input order."""

        worker_count = min(max_workers, len(requests))
        if worker_count == 1:
            return [self._run_pipeline_request(request) for request in requests]
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="tiny-routes-candidate",
        ) as executor:
            # executor.map yields in input order even when workers finish out of
            # order, which makes candidate selection and reports reproducible.
            return list(executor.map(self._run_pipeline_request, requests))

    def _run_pipeline_request(
        self,
        request: V3CandidatePipelineRequest,
    ) -> tuple[V3CandidatePipelineRequest, object | None, Exception | None]:
        try:
            return request, self.pipeline.run(request), None
        except Exception as error:
            return request, None, error

    @staticmethod
    def _sort_attempt_evidence(
        attempts: list[CandidatePoolAttempt],
        diagnostics: list[dict],
    ) -> tuple[list[CandidatePoolAttempt], list[dict]]:
        paired = sorted(
            zip(attempts, diagnostics, strict=True),
            key=lambda item: item[0].candidate_id,
        )
        return (
            [attempt for attempt, _ in paired],
            [diagnostic for _, diagnostic in paired],
        )

    @staticmethod
    def _budget_report(
        request: CandidatePoolRequest,
        attempts: list[CandidatePoolAttempt],
        allocations: list[AttemptBudgetAllocation],
    ) -> GlobalAttemptBudgetReport:
        counts = {slot.level_id: 0 for slot in request.slots}
        for attempt in attempts:
            counts[attempt.level_id] += 1
        return GlobalAttemptBudgetReport(
            maximum_attempts=request.resolved_global_attempt_budget,
            attempts_used=len(attempts),
            attempts_per_slot=tuple(counts.items()),
            allocation_changes=tuple(allocations),
        )

    @staticmethod
    def _has_runnable_slot(request, accepted, attempted) -> bool:
        return any(
            len(accepted[slot.level_id]) < request.candidates_per_slot
            and attempted[slot.level_id] < request.max_attempts_per_slot
            for slot in request.slots
        )

    def _pipeline_request(
        self,
        request: CandidatePoolRequest,
        level_id: str,
        difficulty: str,
        attempt_index: int,
    ) -> V3CandidatePipelineRequest:
        seed_payload = (
            f"{request.base_seed}:{level_id}:{difficulty}:{attempt_index}"
        ).encode("utf-8")
        seed = int.from_bytes(hashlib.sha256(seed_payload).digest()[:8], "big")
        return V3CandidatePipelineRequest(
            candidate_id=f"{level_id}:candidate:{attempt_index:04d}:{seed:016x}",
            level_id=level_id,
            seed=seed,
            difficulty=difficulty,
            attempt_index=attempt_index,
        )

    @staticmethod
    def _validate_result_identity(result, request: V3CandidatePipelineRequest) -> None:
        result_request = getattr(result, "request", None)
        if result_request != request:
            raise ValueError("pipeline result request identity does not match its attempt")

    def _capture_pipeline_result(
        self,
        result: object,
        request: V3CandidatePipelineRequest,
    ) -> dict:
        try:
            return self.reproducibility_bundle_service.capture_pipeline_result(result)
        except Exception as error:
            return self._minimal_diagnostic(
                request,
                passed=bool(getattr(result, "passed", False)),
                terminal_stage=str(getattr(result, "terminal_stage", "pipeline")),
                code=str(getattr(result, "code", "pipeline_result_invalid")),
                diagnostic_error=error,
            )

    def _capture_pipeline_exception(
        self,
        request: V3CandidatePipelineRequest,
        error: Exception,
    ) -> dict:
        try:
            return self.reproducibility_bundle_service.capture_pipeline_exception(
                request,
                error,
            )
        except Exception as diagnostic_error:
            return self._minimal_diagnostic(
                request,
                passed=False,
                terminal_stage="pipeline",
                code="candidate_pipeline_error",
                diagnostic_error=diagnostic_error,
            )

    @staticmethod
    def _minimal_diagnostic(
        request: V3CandidatePipelineRequest,
        *,
        passed: bool,
        terminal_stage: str,
        code: str,
        diagnostic_error: Exception,
    ) -> dict:
        return {
            "candidateID": request.candidate_id,
            "levelID": request.level_id,
            "difficulty": request.difficulty,
            "seed": request.seed,
            "attemptIndex": request.attempt_index,
            "passed": passed,
            "terminalStage": terminal_stage,
            "code": code,
            "diagnosticCaptureError": diagnostic_error.__class__.__name__,
            "stages": [],
        }
