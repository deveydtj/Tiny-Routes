from __future__ import annotations

import json
import threading
from types import SimpleNamespace

from app.models import CandidatePoolRequest, CandidatePoolSlot
from app.random_source import RandomSource
from app.services import CandidatePoolService
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.templates.single_switch_template import SingleSwitchTemplate


class _SignatureService:
    def signature_for_pipeline_result(self, result):
        signature = CandidateSignatureService().signature_for(result.candidate)
        result.candidate.candidate_signature = signature
        return signature


class _Pipeline:
    def __init__(self, rejected_attempts=()):
        self.rejected_attempts = set(rejected_attempts)
        self.requests = []

    def run(self, request):
        self.requests.append(request)
        rejected = (request.level_id, request.attempt_index) in self.rejected_attempts
        candidate = None
        if not rejected:
            number = int(request.level_id.rsplit("_", 1)[1])
            preset = DifficultyService().get_preset(request.difficulty)
            candidate = SingleSwitchTemplate().generate(
                request.level_id,
                number,
                preset,
                RandomSource(request.seed),
            )
        return SimpleNamespace(
            request=request,
            passed=not rejected,
            candidate=candidate,
            terminal_stage="strategy" if rejected else "quality",
            code="static_policy_solution_exists" if rejected else "quality_accepted",
        )


def _request(**overrides) -> CandidatePoolRequest:
    values = {
        "slots": (
            CandidatePoolSlot("level_031", "easy"),
            CandidatePoolSlot("level_032", "easy"),
        ),
        "candidates_per_slot": 2,
        "max_attempts_per_slot": 4,
        "wave_size": 1,
        "base_seed": 9001,
    }
    values.update(overrides)
    return CandidatePoolRequest(**values)


def test_builds_every_campaign_slot_in_deterministic_waves_before_selection() -> None:
    rejected = {("level_031", 0), ("level_032", 1)}
    first_pipeline = _Pipeline(rejected)
    second_pipeline = _Pipeline(rejected)

    first = CandidatePoolService(first_pipeline, _SignatureService()).build(_request())
    second = CandidatePoolService(second_pipeline, _SignatureService()).build(_request())

    assert first.complete
    assert first.constrained_level_ids == ()
    assert tuple(first.candidate_pools) == ("level_031", "level_032")
    assert all(len(pool) == 2 for pool in first.candidate_pools.values())
    assert first.waves_completed == 3
    assert len(first.attempt_diagnostics) == len(first.attempts)
    assert first.attempt_diagnostics[0]["seed"] == first.attempts[0].seed
    assert [attempt.seed for attempt in first.attempts] == [
        attempt.seed for attempt in second.attempts
    ]
    assert [request.level_id for request in first_pipeline.requests[:2]] == [
        "level_031",
        "level_032",
    ]
    retried_requests = tuple(
        request
        for request in first_pipeline.requests
        if request.level_id == "level_031" and request.attempt_index in {0, 1}
    )
    assert len(retried_requests) == 2
    assert all(
        retried_requests[0].retry_variant_seeds[name]
        != retried_requests[1].retry_variant_seeds[name]
        for name in retried_requests[0].retry_variant_seeds
    )
    assert all(
        candidate.candidate_signature is not None
        for pool in first.candidate_pools.values()
        for candidate in pool
    )
    json.dumps(first.to_report_dict(), sort_keys=True)


def test_reports_bounded_shortfall_without_selecting_a_partial_campaign() -> None:
    request = _request(
        slots=(CandidatePoolSlot("level_031", "easy"),),
        max_attempts_per_slot=3,
        wave_size=2,
    )
    pipeline = _Pipeline({("level_031", 0), ("level_031", 1), ("level_031", 2)})

    result = CandidatePoolService(pipeline, _SignatureService()).build(request)

    assert not result.complete
    assert result.constrained_level_ids == ("level_031",)
    assert result.pools[0].shortfall == 2
    assert result.pools[0].attempted_count == 3
    assert result.waves_completed == 2


def test_request_requires_several_candidates_per_slot() -> None:
    try:
        _request(candidates_per_slot=1)
    except ValueError as error:
        assert "at least two" in str(error)
    else:
        raise AssertionError("single-candidate campaign pools must be rejected")


def test_diagnostic_capture_failure_cannot_change_candidate_acceptance() -> None:
    class BrokenDiagnostics:
        def capture_pipeline_result(self, result):
            raise OSError("diagnostic disk unavailable")

        def capture_pipeline_exception(self, request, error):
            raise OSError("diagnostic disk unavailable")

    request = _request(slots=(CandidatePoolSlot("level_031", "easy"),))
    result = CandidatePoolService(
        _Pipeline(),
        _SignatureService(),
        BrokenDiagnostics(),
    ).build(request)

    assert result.complete
    assert all(attempt.passed for attempt in result.attempts)
    assert all(
        item["diagnosticCaptureError"] == "OSError"
        for item in result.attempt_diagnostics
    )


def test_parallel_workers_preserve_serial_candidate_and_report_order() -> None:
    class ConcurrentPipeline(_Pipeline):
        def __init__(self) -> None:
            super().__init__()
            self.barrier = threading.Barrier(4)
            self.lock = threading.Lock()
            self.active = 0
            self.maximum_active = 0

        def run(self, request):
            with self.lock:
                self.active += 1
                self.maximum_active = max(self.maximum_active, self.active)
            try:
                self.barrier.wait(timeout=2)
                return super().run(request)
            finally:
                with self.lock:
                    self.active -= 1

    parallel_pipeline = ConcurrentPipeline()
    parallel_request = _request(wave_size=2, max_workers=4)
    serial_request = _request(wave_size=2, max_workers=1)

    parallel = CandidatePoolService(
        parallel_pipeline, _SignatureService()
    ).build(parallel_request)
    serial = CandidatePoolService(_Pipeline(), _SignatureService()).build(serial_request)

    assert parallel_pipeline.maximum_active == 4
    assert [item.candidate_id for item in parallel.attempts] == sorted(
        item.candidate_id for item in parallel.attempts
    )
    assert [item.to_report_dict() for item in parallel.attempts] == [
        item.to_report_dict() for item in serial.attempts
    ]
    assert [item["candidateID"] for item in parallel.attempt_diagnostics] == [
        item.candidate_id for item in parallel.attempts
    ]
    assert {
        level_id: [candidate.seed for candidate in candidates]
        for level_id, candidates in parallel.candidate_pools.items()
    } == {
        level_id: [candidate.seed for candidate in candidates]
        for level_id, candidates in serial.candidate_pools.items()
    }


def test_global_budget_reallocates_attempts_to_the_constrained_slot_and_reports_it() -> None:
    pipeline = _Pipeline(
        {
            ("level_032", 0),
            ("level_032", 1),
            ("level_032", 2),
            ("level_032", 3),
            ("level_032", 4),
        }
    )
    request = _request(
        max_attempts_per_slot=5,
        global_attempt_budget=5,
        max_workers=2,
    )

    result = CandidatePoolService(pipeline, _SignatureService()).build(request)

    assert not result.complete
    assert result.attempt_budget is not None
    assert result.attempt_budget.maximum_attempts == 5
    assert result.attempt_budget.attempts_used == 5
    assert result.attempt_budget.remaining_attempts == 0
    assert dict(result.attempt_budget.attempts_per_slot) == {
        "level_031": 2,
        "level_032": 3,
    }
    assert any(
        item.level_id == "level_032"
        and item.reason == "constrained_slot_reallocation"
        for item in result.attempt_budget.allocation_changes
    )
    report = result.to_report_dict()["attemptBudget"]
    assert report["remainingAttempts"] == 0
    assert report["attemptsPerSlot"]["level_032"] == 3
