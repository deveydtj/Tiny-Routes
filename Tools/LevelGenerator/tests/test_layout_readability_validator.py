from __future__ import annotations

from app.level_editor_imports import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel
from app.services.layout_readability_validator import LayoutReadabilityValidator


def test_layout_readability_reports_implicit_intersection_metadata() -> None:
    level = _level(
        nodes={
            "start": (0.0, 0.0, ["e_start_package"]),
            "package": (2.0, 0.0, []),
            "side_a": (1.0, -1.0, ["e_side_destination"]),
            "destination": (1.0, 1.0, []),
        },
        edges=[
            ("e_start_package", "start", "package", "horizontalFirst"),
            ("e_side_destination", "side_a", "destination", "verticalFirst"),
        ],
    )

    report = LayoutReadabilityValidator().report_for_level(level)

    assert "implicit_intersection_without_node" in _issue_codes(report)
    assert report.metadata["implicitIntersectionDetected"] is True
    assert report.metadata["offendingRoads"] == ["e_side_destination", "e_start_package"]


def test_layout_readability_rejects_overlapping_switch_exits() -> None:
    level = _level(
        nodes={
            "start": (-0.5, 0.0, ["e_start_switch"]),
            "switch": (0.0, 0.0, ["e_switch_package", "e_switch_destination"]),
            "package": (1.0, 0.45, []),
            "destination": (1.0, -0.45, []),
        },
        edges=[
            ("e_start_switch", "start", "switch", "horizontalFirst"),
            ("e_switch_package", "switch", "package", "horizontalFirst"),
            ("e_switch_destination", "switch", "destination", "horizontalFirst"),
        ],
    )

    report = LayoutReadabilityValidator().report_for_level(level)

    assert "switch_exit_overlap" in _issue_codes(report)
    assert report.metadata["switchExitOverlapDetected"] is True
    angle_measurements = [
        measurement
        for measurement in report.metadata["measuredAngles"]
        if measurement["code"] == "switch_exit_overlap"
    ]
    assert angle_measurements


def test_layout_readability_rejects_start_goal_too_close() -> None:
    level = _level(
        nodes={
            "start": (0.0, 0.0, ["e_start_package"]),
            "package": (0.5, 0.0, ["e_package_destination"]),
            "destination": (0.2, 0.0, []),
        },
        edges=[
            ("e_start_package", "start", "package", "horizontalFirst"),
            ("e_package_destination", "package", "destination", "horizontalFirst"),
        ],
    )

    report = LayoutReadabilityValidator().report_for_level(level)

    assert "start_goal_separation_failure" in _issue_codes(report)
    assert report.metadata["startGoalTooClose"] is True


def _level(
    *,
    nodes: dict[str, tuple[float, float, list[str]]],
    edges: list[tuple[str, str, str, str]],
) -> LevelDocument:
    return LevelDocument(
        id="level_layout_readability",
        name="Layout Readability",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id=node_id, x=x, y=y, outgoingEdgeIDs=outgoing_edge_ids)
                for node_id, (x, y, outgoing_edge_ids) in nodes.items()
            ],
            edges=[
                RouteEdgeModel(
                    id=edge_id,
                    fromNodeID=from_node_id,
                    toNodeID=to_node_id,
                    roadShape=road_shape,
                )
                for edge_id, from_node_id, to_node_id, road_shape in edges
            ],
        ),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=30,
        parTaps=0,
    )


def _issue_codes(report) -> set[str]:
    return {issue.code for issue in report.issues}
