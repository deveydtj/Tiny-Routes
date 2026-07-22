from __future__ import annotations

import json
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
