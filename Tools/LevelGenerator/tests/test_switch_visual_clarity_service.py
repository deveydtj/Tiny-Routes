from __future__ import annotations

from app.level_editor_imports import (
    LevelDocument,
    RouteEdge,
    RouteGraph,
    RouteNode,
    SolutionAction,
    Solution,
)
from app.services.switch_visual_clarity_service import SwitchVisualClarityService


def test_switch_visual_clarity_rejects_two_choices_that_both_start_right() -> None:
    level = _level(
        targets={
            "upper": (1.0, 1.0, "horizontalFirst"),
            "lower": (1.0, -1.0, "horizontalFirst"),
        },
        outgoing_edge_ids=["e_upper", "e_lower"],
    )

    issues = SwitchVisualClarityService().issues_for_level(level, _solution(["switch"]))

    assert "switch_choices_same_visual_direction" in [issue.code for issue in issues]
    assert "solution_tap_cycles_to_visually_confusing_edge" in [issue.code for issue in issues]


def test_switch_visual_clarity_accepts_distinct_cardinal_exits() -> None:
    level = _level(
        targets={
            "right": (1.0, 0.0, "horizontalFirst"),
            "up": (0.0, 1.0, "verticalFirst"),
            "left": (-1.0, 0.0, "horizontalFirst"),
            "down": (0.0, -1.0, "verticalFirst"),
        },
        outgoing_edge_ids=["e_right", "e_up", "e_left", "e_down"],
    )

    issues = SwitchVisualClarityService().issues_for_level(level, _solution(["switch", "switch"]))

    assert issues == []


def test_switch_visual_clarity_uses_l_road_first_segment_not_target_vector() -> None:
    level = _level(
        targets={
            "horizontal": (1.0, 1.0, "horizontalFirst"),
            "vertical": (1.0, 1.0, "verticalFirst"),
        },
        outgoing_edge_ids=["e_horizontal", "e_vertical"],
    )

    report = SwitchVisualClarityService().report_for_level(level)[0]
    buckets_by_edge_id = {direction.edge_id: direction.bucket for direction in report.directions}
    issues = SwitchVisualClarityService().issues_for_level(level, _solution(["switch"]))

    assert buckets_by_edge_id == {
        "e_horizontal": "east",
        "e_vertical": "north",
    }
    assert issues == []


def _level(
    targets: dict[str, tuple[float, float, str]],
    outgoing_edge_ids: list[str],
) -> LevelDocument:
    nodes = [RouteNode(id="switch", x=0.0, y=0.0, outgoingEdgeIDs=outgoing_edge_ids)]
    edges = []
    for target_id, (x, y, road_shape) in targets.items():
        edge_id = f"e_{target_id}"
        nodes.append(RouteNode(id=target_id, x=x, y=y, outgoingEdgeIDs=[]))
        edges.append(RouteEdge(id=edge_id, fromNodeID="switch", toNodeID=target_id, roadShape=road_shape))

    return LevelDocument(
        id="level_switch_visual_clarity",
        name="Switch Visual Clarity",
        graph=RouteGraph(nodes=nodes, edges=edges),
        startNodeID="switch",
        packageNodeID=next(iter(targets)),
        destinationNodeID=next(reversed(targets)),
        timeLimitSeconds=30,
        parTaps=0,
    )


def _solution(tap_node_ids: list[str]) -> Solution:
    return Solution(
        levelID="level_switch_visual_clarity",
        description="Tap switches.",
        expectedOutcome="completed",
        maxTaps=len(tap_node_ids),
        requiresWithinTimeLimit=True,
        actions=[
            SolutionAction(timeSeconds=float(index + 1), tapNodeID=node_id)
            for index, node_id in enumerate(tap_node_ids)
        ],
    )
