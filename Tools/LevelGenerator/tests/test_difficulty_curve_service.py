from __future__ import annotations

from app.services.difficulty_curve_service import DifficultyCurveService


def test_difficulty_curve_default_campaign_curve() -> None:
    service = DifficultyCurveService()

    assert [service.difficulty_for_level(level) for level in [1, 3, 4, 10, 11, 25, 26]] == [
        "tutorial",
        "tutorial",
        "easy",
        "easy",
        "medium",
        "medium",
        "hard",
    ]


def test_difficulty_curve_builds_batch_plan_with_weights() -> None:
    plan = DifficultyCurveService().build_plan(9, 4, "auto")

    assert [entry.difficulty for entry in plan.entries] == ["easy", "easy", "medium", "medium"]
    assert plan.entries[0].template_weights["single_switch"] > 0
    assert plan.entries[2].template_weights["multi_switch_chain"] > 0
