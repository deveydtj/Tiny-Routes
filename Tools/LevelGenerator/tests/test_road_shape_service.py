from __future__ import annotations

import pytest

from app.services.road_shape_service import RoadShapeService


def test_road_shape_service_prefers_dominant_axis() -> None:
    service = RoadShapeService()

    assert service.pick_for_positions(0, 0, 2, 1) == "horizontalFirst"
    assert service.pick_for_positions(0, 0, 1, 2) == "verticalFirst"


def test_road_shape_service_allows_valid_override() -> None:
    assert RoadShapeService().pick_for_positions(0, 0, 2, 1, override="verticalFirst") == "verticalFirst"


def test_road_shape_service_rejects_invalid_override() -> None:
    with pytest.raises(ValueError):
        RoadShapeService().pick_for_positions(0, 0, 2, 1, override="diagonal")


def test_road_shape_planner_can_separate_two_switch_exits() -> None:
    service = RoadShapeService()

    plan = service.plan_for_graph(
        {
            "switch": (0, 0),
            "upper": (1, 1),
            "lower": (1, -1),
        },
        [("switch", "upper"), ("switch", "lower")],
        strategy="switch_clarity_optimized",
    )

    buckets = plan.metadata["switchDirectionBuckets"]["switch"]
    assert len(set(buckets.values())) == 2
    assert not any(issue.startswith("switch_choices_same_visual_direction") for issue in plan.issues)


def test_horizontal_first_and_vertical_first_create_different_l_road_tangents() -> None:
    service = RoadShapeService()

    horizontal_plan = service.plan_for_graph(
        {"a": (0, 0), "b": (1, 1)},
        [("a", "b")],
        strategy="horizontal_first",
    )
    vertical_plan = service.plan_for_graph(
        {"a": (0, 0), "b": (1, 1)},
        [("a", "b")],
        strategy="vertical_first",
    )

    assert horizontal_plan.edge_plans[0].start_direction == "east"
    assert vertical_plan.edge_plans[0].start_direction == "north"


def test_crossing_heavy_candidate_scores_lower() -> None:
    service = RoadShapeService()

    crossing_plan = service.plan_for_graph(
        {
            "a": (0, 1),
            "b": (2, 1),
            "c": (1, 0),
            "d": (1, 2),
        },
        [("a", "b"), ("c", "d")],
        strategy="all_straight",
    )
    clear_plan = service.plan_for_graph(
        {
            "a": (0, 1),
            "b": (2, 1),
            "c": (3, 0),
            "d": (3, 2),
        },
        [("a", "b"), ("c", "d")],
        strategy="all_straight",
    )

    assert crossing_plan.metadata["crossingCount"] == 1
    assert crossing_plan.score < clear_plan.score


def test_overlapping_first_segments_fail_road_shape_validation() -> None:
    service = RoadShapeService()

    plan = service.plan_for_graph(
        {
            "switch": (0, 0),
            "package": (2, 1),
            "dead_end": (2, 2),
        },
        [("switch", "package"), ("switch", "dead_end")],
        required_path=("switch", "package"),
        strategy="horizontal_first",
    )

    assert any(issue.startswith("same_switch_first_segments_overlap:switch") for issue in plan.issues)
    assert any(issue.startswith("required_and_wrong_route_first_segments_overlap:switch") for issue in plan.issues)
