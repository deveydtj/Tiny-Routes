from __future__ import annotations

import pytest

from app.models.candidate_pool import CandidatePoolRequest, CandidatePoolSlot
from app.services.candidate_pool_service import CandidatePoolService
from app.services.production_campaign_service import ProductionCampaignService
from app.services.production_candidate_pipeline_service import (
    ProductionCandidatePipelineService,
)
from app.services.production_level_realization_service import (
    ProductionLevelRealizationService,
)
from app.services.production_pipeline_policy_service import (
    ProductionPipelinePolicyService,
)
from app.services.puzzle_blueprint_service import PuzzleBlueprintService
from app.services.road_geometry_validation_service import (
    RoadGeometryValidationService,
)
from app.services.visual_clarity_validation_service import (
    VisualClarityValidationService,
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


@pytest.mark.parametrize("difficulty", ("easy", "medium", "hard", "expert"))
def test_default_pipeline_rejects_overlapping_roads_and_ambiguous_turns(
    difficulty: str,
) -> None:
    request = V3CandidatePipelineRequest(
        candidate_id=f"level_001:{difficulty}:readability",
        level_id="level_001",
        seed=1,
        difficulty=difficulty,
    )

    result = ProductionCandidatePipelineService().run(request)

    assert result.passed
    assert result.candidate is not None
    visual = VisualClarityValidationService().report_for_level(
        result.candidate.level_document
    )
    geometry = RoadGeometryValidationService().report_for_level(
        result.candidate.level_document
    )
    assert not visual.has_errors, [issue.code for issue in visual.errors]
    assert not geometry.has_errors, [issue.code for issue in geometry.errors]


@pytest.mark.parametrize(
    ("difficulty", "seed"),
    (
        ("medium", 2),
        ("easy", 8),
        ("medium", 8),
        ("hard", 8),
        ("expert", 8),
    ),
)
def test_realization_keeps_recovery_lanes_clear(
    difficulty: str,
    seed: int,
) -> None:
    request = V3CandidatePipelineRequest(
        candidate_id=f"level_{seed:03d}:{difficulty}:recovery-layout",
        level_id=f"level_{seed:03d}",
        seed=seed,
        difficulty=difficulty,
        attempt_index=seed % 3,
    )
    blueprint = PuzzleBlueprintService().generate(
        difficulty,
        request.retry_variant_seed("blueprint"),
    )
    level = ProductionLevelRealizationService().realize(
        level_id=request.level_id,
        difficulty=difficulty,
        blueprint=blueprint,
        seed=request.retry_variant_seed("composition"),
        attempt_index=request.attempt_index,
    )

    visual = VisualClarityValidationService().report_for_level(level)
    geometry = RoadGeometryValidationService().report_for_level(level)
    assert not visual.has_errors, [issue.code for issue in visual.errors]
    assert not geometry.has_errors, [issue.code for issue in geometry.errors]


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
