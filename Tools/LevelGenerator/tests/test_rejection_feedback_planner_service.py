from __future__ import annotations

import json

from app.models import BlueprintPlanningConstraints, RejectionFeedbackEvent
from app.services import RejectionFeedbackPlannerService


def _events(
    code: str,
    stage: str,
    *,
    count: int = 3,
    archetype: str = "return_to_hub",
    motifs: tuple[str, ...] = (),
) -> tuple[RejectionFeedbackEvent, ...]:
    return tuple(
        RejectionFeedbackEvent(
            code=code,
            stage=stage,
            archetype=archetype,
            motif_combination=motifs,
        )
        for _ in range(count)
    )


def test_repeated_composition_failure_avoids_the_exact_motif_combination() -> None:
    plan = RejectionFeedbackPlannerService().plan(
        _events(
            "composition_port_contract_failed",
            "composition",
            motifs=("revisit_hub", "unlock_gate"),
        )
    )

    assert plan.constraints.avoided_motif_combinations == (
        ("revisit_hub", "unlock_gate"),
    )
    assert [item.action for item in plan.adjustments] == [
        "avoid_motif_combination"
    ]
    assert plan.constraints.preserve_decision_quality
    json.dumps(plan.to_report_dict(), sort_keys=True)


def test_feedback_maps_repeated_causes_to_safe_deterministic_adjustments() -> None:
    events = (
        _events("layout_state_overlap", "layout")
        + _events("strategy_search_limit_exceeded", "strategy")
        + _events("solution_jitter_failure", "runtime")
        + _events("insufficient_planning_decisions", "quality")
    )
    plan = RejectionFeedbackPlannerService().plan(events)

    assert plan.constraints.layout_profile == "large"
    assert plan.constraints.state_space_scale_percent == 85
    assert plan.constraints.outgoing_edge_order_variant == 1
    assert plan.constraints.requested_archetype == "unlock_shortcut"
    assert plan.constraints.preserve_decision_quality is True
    assert {item.action for item in plan.adjustments} == {
        "request_larger_layout",
        "reduce_state_space",
        "adjust_outgoing_edge_order",
        "select_different_archetype",
    }


def test_feedback_waits_for_repetition_and_does_not_reapply_same_milestone() -> None:
    service = RejectionFeedbackPlannerService()
    two_failures = service.plan(_events("layout_state_overlap", "layout", count=2))
    assert two_failures.adjustments == ()
    assert two_failures.constraints == BlueprintPlanningConstraints()

    first = service.plan(_events("layout_state_overlap", "layout"))
    duplicate = service.plan(
        _events("layout_state_overlap", "layout"),
        current=first.constraints,
        previous_adjustments=first.adjustments,
    )
    assert duplicate.adjustments == ()
    assert duplicate.constraints.layout_profile == "large"

    second_milestone = service.plan(
        _events("layout_state_overlap", "layout", count=6),
        current=first.constraints,
        previous_adjustments=first.adjustments,
    )
    assert second_milestone.constraints.layout_profile == "extra_large"
    assert second_milestone.adjustments[0].occurrence_count == 6
