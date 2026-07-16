from __future__ import annotations

from app.level_editor_imports import LevelDocument, RouteEdge, RouteGraph, RouteNode, Solution
from app.models.abstract_puzzle_solution import AbstractPuzzleSolutionMetadata
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


def test_visual_clarity_rejects_return_loop_false_shortcut() -> None:
    level = _return_loop_level(destination_y=-0.10)

    issue = _single_issue(
        level,
        "return_loop_false_shortcut",
        required_path=("start", "alpha", "package", "beta", "return", "alpha", "destination"),
    )

    assert issue.severity == "error"
    assert issue.related_node_id == "alpha"
    assert issue.related_edge_ids == ("e_return_alpha", "e_alpha_destination")


def test_visual_clarity_allows_clean_return_loop() -> None:
    level = _return_loop_level(destination_y=0.95)

    codes = {
        issue.code
        for issue in VisualClarityValidationService().report_for_level(
            level,
            required_path=("start", "alpha", "package", "beta", "return", "alpha", "destination"),
        ).issues
    }

    assert "return_loop_false_shortcut" not in codes


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
        solution=Solution(
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


def test_generated_level_validation_rejects_return_loop_false_shortcut() -> None:
    generated = GeneratedLevel(
        level_document=_return_loop_level(destination_y=-0.10),
        solution=Solution(
            levelID="level_return_loop_shortcut",
            description="Return-loop false shortcut fixture.",
            expectedOutcome="completed",
            maxTaps=0,
            requiresWithinTimeLimit=True,
            actions=[],
        ),
        template_name="visual_topology",
        difficulty="medium",
        seed=1,
        abstract_solution_metadata=_metadata_for_required_path(
            ("start", "alpha", "package", "beta", "return", "alpha", "destination")
        ),
    )

    result = GeneratedLevelValidationService().validate(
        generated,
        preset=DifficultyService().get_preset("medium"),
        overwrite=True,
        enforce_difficulty=False,
    )

    assert result.has_errors
    assert "return_loop_false_shortcut" in result.error_codes
    shortcut_message = next(message for message in result.messages if message.code == "return_loop_false_shortcut")
    assert shortcut_message.related_edge_ids == ("e_return_alpha", "e_alpha_destination")


def _single_issue(level: LevelDocument, code: str, required_path: tuple[str, ...] = ()):
    issues = [
        issue
        for issue in VisualClarityValidationService().report_for_level(level, required_path=required_path).issues
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
        graph=RouteGraph(
            nodes=[
                RouteNode(id=node_id, x=x, y=y, outgoingEdgeIDs=outgoing_edge_ids)
                for node_id, (x, y, outgoing_edge_ids) in nodes.items()
            ],
            edges=[
                RouteEdge(id=edge_id, fromNodeID=from_node_id, toNodeID=to_node_id)
                for edge_id, from_node_id, to_node_id in edges
            ],
        ),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=30,
        parTaps=0,
    )


def _return_loop_level(destination_y: float) -> LevelDocument:
    return _level(
        nodes={
            "start": (-1.0, 0.0, ["e_start_alpha"]),
            "alpha": (0.0, 0.0, ["e_alpha_destination", "e_alpha_package"]),
            "package": (0.1, 0.8, ["e_package_beta"]),
            "beta": (1.0, 0.8, ["e_beta_return"]),
            "return": (1.0, 0.08, ["e_return_alpha"]),
            "destination": (1.0, destination_y, []),
        },
        edges=[
            ("e_start_alpha", "start", "alpha"),
            ("e_alpha_destination", "alpha", "destination"),
            ("e_alpha_package", "alpha", "package"),
            ("e_package_beta", "package", "beta"),
            ("e_beta_return", "beta", "return"),
            ("e_return_alpha", "return", "alpha"),
        ],
    )


def _metadata_for_required_path(required_path: tuple[str, ...]) -> AbstractPuzzleSolutionMetadata:
    return AbstractPuzzleSolutionMetadata(
        decision_node_ids=(),
        solution_switch_states=(),
        required_path=required_path,
        alternate_path_count=0,
        dead_end_count=0,
        failure_path_count=0,
        false_route_count=0,
        loop_count=1,
        minimum_required_decisions=0,
        optional_tap_count=0,
        repeated_switch_usage=True,
        package_before_destination=True,
    )
