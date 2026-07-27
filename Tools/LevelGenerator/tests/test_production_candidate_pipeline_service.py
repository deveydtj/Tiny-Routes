from __future__ import annotations

import pytest

from app.models.candidate_pool import CandidatePoolRequest, CandidatePoolSlot
from app.services.candidate_pool_service import CandidatePoolService
from app.services.production_campaign_service import ProductionCampaignService
from app.services.production_candidate_pipeline_service import (
    ProductionCandidatePipelineService,
)
from app.services.production_pipeline_policy_service import (
    ProductionPipelinePolicyService,
)
from app.services.v3_candidate_pipeline_coordinator import (
    V3CandidatePipelineRequest,
)


@pytest.mark.parametrize("difficulty", ("easy", "medium", "hard", "expert"))
def test_default_pipeline_completes_all_six_v3_stages(difficulty: str) -> None:
    request = V3CandidatePipelineRequest(
        candidate_id=f"level_001:{difficulty}:candidate",
        level_id="level_001",
        seed=1,
        difficulty=difficulty,
    )

    result = ProductionCandidatePipelineService().run(request)

    assert result.passed
    assert tuple(stage.stage for stage in result.stage_results) == (
        "blueprint",
        "composition",
        "strategy",
        "layout",
        "runtime",
        "quality",
    )
    assert result.candidate is not None
    assert result.candidate.solution.actions
    assert result.candidate.solution.expectedOutcome == "completed"
    assert result.candidate.requires_swift_validation is True
    assert ProductionPipelinePolicyService().validate((result,)) == ()


def test_default_pipeline_is_deterministic() -> None:
    request = V3CandidatePipelineRequest(
        candidate_id="level_001:deterministic",
        level_id="level_001",
        seed=17,
        difficulty="easy",
        attempt_index=2,
    )

    first = ProductionCandidatePipelineService().run(request)
    second = ProductionCandidatePipelineService().run(request)

    assert first.passed and second.passed
    assert first.candidate is not None and second.candidate is not None
    assert (
        first.candidate.level_document.to_dict()
        == second.candidate.level_document.to_dict()
    )
    assert first.candidate.solution.to_dict() == second.candidate.solution.to_dict()


def test_campaign_service_constructs_the_default_v3_pool() -> None:
    service = ProductionCampaignService()

    assert isinstance(service.candidate_pool_service, CandidatePoolService)
    assert isinstance(
        service.candidate_pool_service.pipeline,
        ProductionCandidatePipelineService,
    )


def test_default_campaign_pool_builds_real_diverse_candidates() -> None:
    service = ProductionCampaignService()
    request = CandidatePoolRequest(
        slots=(CandidatePoolSlot("level_001", "easy"),),
        candidates_per_slot=2,
        max_attempts_per_slot=8,
        wave_size=2,
        base_seed=731_005,
        max_workers=2,
        global_attempt_budget=8,
    )

    result = service.candidate_pool_service.build(request)

    assert result.complete
    assert len(result.pools[0].candidates) == 2
    archetypes = {
        candidate.candidate_signature.blueprint_archetype
        for candidate in result.pools[0].candidates
    }
    assert len(archetypes) == 2
