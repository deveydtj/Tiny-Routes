from __future__ import annotations

from app.services.candidate_seed_planning_service import CandidateSeedPlanningService


def test_candidate_seed_plan_is_deterministic_and_stage_specific() -> None:
    first = CandidateSeedPlanningService(42)
    second = CandidateSeedPlanningService(42)

    assert first.candidate_seed("easy", None, "level_004", 2) == second.candidate_seed(
        "easy", None, "level_004", 2
    )
    assert first.map_seed("level_004", 2, 0) != first.map_seed("level_004", 2, 1)
