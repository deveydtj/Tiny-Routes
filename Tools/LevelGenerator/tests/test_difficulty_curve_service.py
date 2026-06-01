from __future__ import annotations

from app.services.difficulty_curve_service import DifficultyCurveService


def test_difficulty_curve_default_campaign_curve() -> None:
    service = DifficultyCurveService()

    assert [service.difficulty_for_level(level) for level in [1, 3, 4, 10, 11, 25, 26, 40, 41]] == [
        "tutorial",
        "tutorial",
        "easy",
        "easy",
        "medium",
        "medium",
        "hard",
        "hard",
        "expert",
    ]


def test_difficulty_curve_builds_batch_plan_with_weights() -> None:
    plan = DifficultyCurveService().build_plan(9, 4, "auto")

    assert [entry.difficulty for entry in plan.entries] == ["easy", "easy", "medium", "medium"]
    assert plan.entries[0].template_weights["two_switch_order_intro"] > 0
    assert plan.entries[2].template_weights["multi_switch_order"] > 0


def test_difficulty_curve_expert_template_weights() -> None:
    service = DifficultyCurveService()

    assert service.template_weights_for_level(41, "expert")["four_way_intro"] == 5
    assert service.template_weights_for_level(46, "expert")["four_way_ring"] == 4
    assert service.template_weights_for_level(28, "hard")["two_phase_route"] == 5


def test_difficulty_curve_feature_unlock_gates() -> None:
    service = DifficultyCurveService()

    assert service.template_weights_for_level(1, "tutorial")["straight_delivery_intro"] == 7
    assert "return_loop_intro" not in service.template_weights_for_level(15, "medium")
    assert (
        service.template_weights_for_level(31, "hard")["ring_route_gate"]
        > service.template_weights_for_level(28, "hard").get("ring_route_gate", 0)
    )
