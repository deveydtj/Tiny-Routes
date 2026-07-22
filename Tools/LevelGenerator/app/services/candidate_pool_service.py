"""Deterministic campaign-wide V3 candidate-pool construction."""

from __future__ import annotations

import hashlib

from ..models.candidate_pool import (
    CampaignCandidatePoolResult,
    CandidatePoolAttempt,
    CandidatePoolRequest,
    CandidateSlotPool,
)
from .candidate_signature_service import CandidateSignatureService
from .v3_candidate_pipeline_coordinator import V3CandidatePipelineRequest


class CandidatePoolService:
    """Run complete V3 attempts in bounded waves before portfolio selection.

    Rejected pipeline results are reduced to compact audit records, so callers
    can increase ``max_attempts_per_slot`` without retaining every large proof
    artifact in memory. Accepted candidates keep their complete production
    signatures and are never selected here; campaign optimization is a later
    boundary.
    """

    def __init__(self, pipeline, signature_service: CandidateSignatureService | None = None) -> None:
        runner = getattr(pipeline, "run", None)
        if not callable(runner):
            raise TypeError("pipeline must expose a callable run(request) method")
        self.pipeline = pipeline
        self.signature_service = signature_service or CandidateSignatureService()

    def build(self, request: CandidatePoolRequest) -> CampaignCandidatePoolResult:
        if not isinstance(request, CandidatePoolRequest):
            raise TypeError("request must be a CandidatePoolRequest")

        accepted = {slot.level_id: [] for slot in request.slots}
        attempted = {slot.level_id: 0 for slot in request.slots}
        attempts: list[CandidatePoolAttempt] = []
        wave_index = 0

        while self._has_runnable_slot(request, accepted, attempted):
            for slot in request.slots:
                if len(accepted[slot.level_id]) >= request.candidates_per_slot:
                    continue
                remaining_attempts = (
                    request.max_attempts_per_slot - attempted[slot.level_id]
                )
                for _ in range(min(request.wave_size, remaining_attempts)):
                    if len(accepted[slot.level_id]) >= request.candidates_per_slot:
                        break
                    attempt_index = attempted[slot.level_id]
                    pipeline_request = self._pipeline_request(
                        request, slot.level_id, slot.difficulty, attempt_index
                    )
                    attempted[slot.level_id] += 1
                    try:
                        result = self.pipeline.run(pipeline_request)
                        self._validate_result_identity(result, pipeline_request)
                        passed = bool(getattr(result, "passed", False))
                        terminal_stage = str(
                            getattr(result, "terminal_stage", "pipeline")
                        )
                        code = str(getattr(result, "code", "pipeline_result_invalid"))
                        if passed:
                            signature = self.signature_service.signature_for_pipeline_result(
                                result
                            )
                            candidate = getattr(result, "candidate", None)
                            if candidate is None or candidate.candidate_signature != signature:
                                raise ValueError(
                                    "accepted pipeline result did not retain its signature"
                                )
                            accepted[slot.level_id].append(candidate)
                    except Exception:
                        passed = False
                        terminal_stage = "pipeline"
                        code = "candidate_pipeline_error"

                    attempts.append(
                        CandidatePoolAttempt(
                            candidate_id=pipeline_request.candidate_id,
                            level_id=slot.level_id,
                            difficulty=slot.difficulty,
                            seed=pipeline_request.seed,
                            attempt_index=attempt_index,
                            wave_index=wave_index,
                            passed=passed,
                            terminal_stage=terminal_stage,
                            code=code,
                        )
                    )
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
        return CampaignCandidatePoolResult(
            pools=pools,
            attempts=tuple(attempts),
            waves_completed=wave_index,
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
        wave_index = result.waves_completed
        total_new_attempts = 0

        while any(
            additions[level_id] < desired_additions[level_id]
            and slot_attempts[level_id] < max_additional_attempts_per_slot
            for level_id in targets
        ):
            for slot in request.slots:
                level_id = slot.level_id
                if level_id not in additions:
                    continue
                if additions[level_id] >= desired_additions[level_id]:
                    continue
                remaining = max_additional_attempts_per_slot - slot_attempts[level_id]
                for _ in range(min(request.wave_size, remaining)):
                    if additions[level_id] >= desired_additions[level_id]:
                        break
                    if (
                        max_total_attempts is not None
                        and total_new_attempts >= max_total_attempts
                    ):
                        break
                    attempt_index = attempted[level_id]
                    pipeline_request = self._pipeline_request(
                        request,
                        level_id,
                        slot.difficulty,
                        attempt_index,
                    )
                    attempted[level_id] += 1
                    slot_attempts[level_id] += 1
                    total_new_attempts += 1
                    try:
                        pipeline_result = self.pipeline.run(pipeline_request)
                        self._validate_result_identity(pipeline_result, pipeline_request)
                        passed = bool(getattr(pipeline_result, "passed", False))
                        terminal_stage = str(
                            getattr(pipeline_result, "terminal_stage", "pipeline")
                        )
                        code = str(
                            getattr(
                                pipeline_result, "code", "pipeline_result_invalid"
                            )
                        )
                        if passed:
                            signature = (
                                self.signature_service.signature_for_pipeline_result(
                                    pipeline_result
                                )
                            )
                            candidate = getattr(pipeline_result, "candidate", None)
                            if (
                                candidate is None
                                or candidate.candidate_signature != signature
                            ):
                                raise ValueError(
                                    "accepted pipeline result did not retain its signature"
                                )
                            candidates[level_id].append(candidate)
                            additions[level_id] += 1
                    except Exception:
                        passed = False
                        terminal_stage = "pipeline"
                        code = "candidate_pipeline_error"
                    attempts.append(
                        CandidatePoolAttempt(
                            candidate_id=pipeline_request.candidate_id,
                            level_id=level_id,
                            difficulty=slot.difficulty,
                            seed=pipeline_request.seed,
                            attempt_index=attempt_index,
                            wave_index=wave_index,
                            passed=passed,
                            terminal_stage=terminal_stage,
                            code=code,
                        )
                    )
                if (
                    max_total_attempts is not None
                    and total_new_attempts >= max_total_attempts
                ):
                    break
            wave_index += 1
            if (
                max_total_attempts is not None
                and total_new_attempts >= max_total_attempts
            ):
                break

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
        return CampaignCandidatePoolResult(
            pools=tuple(pools),
            attempts=tuple(attempts),
            waves_completed=wave_index,
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
