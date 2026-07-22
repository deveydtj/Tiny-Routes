from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.models import CandidatePoolRequest, CandidatePoolSlot
from app.random_source import RandomSource
from app.services import (
    CampaignPortfolioService,
    CandidatePoolService,
    PortfolioBacktrackingConfig,
    PortfolioBacktrackingFailure,
)
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.templates.single_switch_template import SingleSwitchTemplate


class _Pipeline:
    def __init__(self, *, always_same: bool = False) -> None:
        self.always_same = always_same
        self.requests = []

    def run(self, request):
        self.requests.append(request)
        number = int(request.level_id.rsplit("_", 1)[1])
        preset = DifficultyService().get_preset(request.difficulty)
        candidate = SingleSwitchTemplate().generate(
            request.level_id,
            number,
            preset,
            RandomSource(request.seed),
        )
        candidate._portfolio_archetype = (
            "hub"
            if self.always_same or request.level_id == "level_031" or request.attempt_index < 2
            else "loop"
        )
        return SimpleNamespace(
            request=request,
            passed=True,
            candidate=candidate,
            terminal_stage="quality",
            code="quality_accepted",
        )


class _SignatureService:
    def signature_for_pipeline_result(self, result):
        signature = CandidateSignatureService().signature_for(result.candidate)
        signature = replace(
            signature,
            blueprint_archetype=result.candidate._portfolio_archetype,
        )
        result.candidate.candidate_signature = signature
        return signature


def _request() -> CandidatePoolRequest:
    return CandidatePoolRequest(
        slots=(
            CandidatePoolSlot("level_031", "easy"),
            CandidatePoolSlot("level_032", "easy"),
        ),
        candidates_per_slot=2,
        max_attempts_per_slot=2,
        wave_size=1,
        base_seed=103104,
    )


def test_targeted_backtracking_expands_only_the_constrained_slot() -> None:
    pipeline = _Pipeline()
    pool_service = CandidatePoolService(pipeline, _SignatureService())
    request = _request()
    initial = pool_service.build(request)

    result = CampaignPortfolioService(pool_service).select_with_backtracking(
        initial,
        request,
        config=PortfolioBacktrackingConfig(
            max_rounds=2,
            additional_candidates_per_slot=1,
            max_attempts_per_slot_per_round=2,
            global_attempt_budget=4,
        ),
    )

    assert [candidate.candidate_signature.blueprint_archetype for candidate in result.candidates] == [
        "hub",
        "loop",
    ]
    assert len(result.expansions) == 1
    assert result.expansions[0].constrained_level_ids == ("level_032",)
    assert result.expansions[0].attempts_added == 1
    assert [request.level_id for request in pipeline.requests[4:]] == ["level_032"]
    assert result.candidate_pools.complete
    budget = result.candidate_pools.attempt_budget
    assert budget is not None
    assert dict(budget.attempts_per_slot) == {"level_031": 2, "level_032": 3}
    assert budget.remaining_attempts == budget.maximum_attempts - 5
    assert budget.allocation_changes[-1].reason == "portfolio_constraint_reallocation"


def test_backtracking_fails_without_relaxing_constraints_after_global_budget() -> None:
    pipeline = _Pipeline(always_same=True)
    pool_service = CandidatePoolService(pipeline, _SignatureService())
    request = _request()
    initial = pool_service.build(request)

    with pytest.raises(PortfolioBacktrackingFailure) as captured:
        CampaignPortfolioService(pool_service).select_with_backtracking(
            initial,
            request,
            config=PortfolioBacktrackingConfig(
                max_rounds=3,
                additional_candidates_per_slot=1,
                max_attempts_per_slot_per_round=2,
                global_attempt_budget=2,
            ),
        )

    assert captured.value.constrained_level_ids == ("level_032",)
    assert sum(item.attempts_added for item in captured.value.expansions) == 2
    assert all(
        dict(item.trigger_reasons).keys()
        == {"portfolio_adjacent_blueprint_archetype"}
        for item in captured.value.expansions
    )
