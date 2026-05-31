from __future__ import annotations

from app.level_editor_imports import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel, SolutionModel
from app.models.generated_level import GeneratedLevel
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.services.visual_clarity_validation_service import VisualClarityValidationService


def test_visual_clarity_rejects_implicit_intersection_without_graph_node() -> None:
    level = _level(
        nodes={
            "start": (0.0, 0.0, ["e_start_package"]),
            "package": (2.0, 0.0, []),
            "side_a": (1.0, -1.0, ["e_side"]),
            "destination": (1.0, 1.0, []),
        },
        edges=[
            ("e_start_package", "start", "package"),
            ("e_side", "side_a", "destination"),
        ],
    )

    issue = _single_issue(level, "implicit_intersection_without_graph_node")

    assert issue.severity == "error"
    assert issue.related_edge_ids == ("e_start_package", "e_side")


def test_visual_clarity_rejects_road_crosses_through_unconnected_node() -> None:
    level = _level(
        nodes={
            "start": (0.0, 0.0, ["e_start_package"]),
            "marker": (1.0, 0.0, []),
            "package": (2.0, 0.0, ["e_package_destination"]),
            "destination": (3.0, 0.0, []),
        },
        edges=[
            ("e_start_package", "start", "package"),
            ("e_package_destination", "package", "destination"),
        ],
    )

    issue = _single_issue(level, "road_crosses_through_unconnected_node")

    assert issue.severity == "error"
    assert issue.related_node_id == "marker"
    assert issue.related_edge_id == "e_start_package"


def test_visual_clarity_rejects_unconnected_road_endpoint_touches_segment() -> None:
    level = _level(
        nodes={
            "start": (0.0, 0.0, ["e_start_package"]),
            "package": (2.0, 0.0, []),
            "side_a": (1.0, 0.0, ["e_side"]),
            "destination": (1.0, 1.0, []),
        },
        edges=[
            ("e_start_package", "start", "package"),
            ("e_side", "side_a", "destination"),
        ],
    )

    issue = _single_issue(level, "unconnected_road_endpoint_touches_segment")

    assert issue.severity == "error"
    assert issue.related_node_id == "side_a"
    assert issue.related_edge_id == "e_start_package"


def test_visual_clarity_rejects_unconnected_parallel_road_overlap() -> None:
    level = _level(
        nodes={
            "start": (0.0, 0.0, ["e_start_package"]),
            "package": (2.0, 0.0, []),
            "side_a": (1.0, 0.0, ["e_side"]),
            "destination": (3.0, 0.0, []),
        },
        edges=[
            ("e_start_package", "start", "package"),
            ("e_side", "side_a", "destination"),
        ],
    )

    issue = _single_issue(level, "unconnected_parallel_road_overlap")

    assert issue.severity == "error"
    assert issue.related_edge_ids == ("e_start_package", "e_side")


def test_generated_level_validation_rejects_visual_topology_errors() -> None:
    generated = GeneratedLevel(
        level_document=_level(
            nodes={
                "start": (0.0, 0.0, ["e_start_package"]),
                "package": (2.0, 0.0, []),
                "side_a": (1.0, -1.0, ["e_side"]),
                "destination": (1.0, 1.0, []),
            },
            edges=[
                ("e_start_package", "start", "package"),
                ("e_side", "side_a", "destination"),
            ],
        ),
        solution=SolutionModel(
            levelID="level_visual_topology",
            description="No taps.",
            expectedOutcome="completed",
            maxTaps=0,
            requiresWithinTimeLimit=True,
            actions=[],
        ),
        template_name="visual_topology",
        difficulty="easy",
        seed=1,
    )

    result = GeneratedLevelValidationService().validate(
        generated,
        preset=DifficultyService().get_preset("easy"),
        overwrite=True,
        enforce_difficulty=False,
    )

    assert "implicit_intersection_without_graph_node" in result.error_codes


def _single_issue(level: LevelDocument, code: str):
    issues = [
        issue
        for issue in VisualClarityValidationService().report_for_level(level).issues
        if issue.code == code
    ]
    assert len(issues) == 1
    return issues[0]


def _level(
    *,
    nodes: dict[str, tuple[float, float, list[str]]],
    edges: list[tuple[str, str, str]],
) -> LevelDocument:
    return LevelDocument(
        id="level_visual_topology",
        name="Visual Topology",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id=node_id, x=x, y=y, outgoingEdgeIDs=outgoing_edge_ids)
                for node_id, (x, y, outgoing_edge_ids) in nodes.items()
            ],
            edges=[
                RouteEdgeModel(id=edge_id, fromNodeID=from_node_id, toNodeID=to_node_id)
                for edge_id, from_node_id, to_node_id in edges
            ],
        ),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=30,
        parTaps=0,
    )
