from __future__ import annotations

from app.level_editor_imports import LevelDocument, RouteEdge, RouteGraph, RouteNode, SolutionAction, Solution
from app.models.generated_level import GeneratedLevel


def late_tap_chain_positions() -> dict[str, tuple[float, float]]:
    return {
        "start": (0.0, 0.0),
        "switch_a": (0.6, 0.6),
        "package": (1.2, 0.0),
        "switch_b": (1.8, 0.6),
        "switch_c": (2.4, 0.0),
        "switch_d": (3.0, 0.6),
        "destination": (3.6, 0.0),
        "dead_end_a": (0.6, -0.6),
        "dead_end_b": (1.8, 1.4),
        "dead_end_c": (2.4, -0.8),
        "dead_end_d": (3.0, 1.4),
    }


def late_tap_chain_route() -> list[str]:
    return ["start", "switch_a", "package", "switch_b", "switch_c", "switch_d", "destination"]


def late_tap_chain_tap_nodes() -> list[str]:
    return ["switch_a", "switch_b", "switch_c", "switch_d"]


def late_tap_chain_old_times() -> list[float]:
    return [1.0, 3.4, 4.6, 5.8]


def late_tap_chain_new_times() -> list[float]:
    return [0.77, 3.02, 4.14, 5.26]


def late_tap_chain_route_edge_shapes() -> dict[tuple[str, str], str | None]:
    return {
        ("start", "switch_a"): "horizontalFirst",
        ("switch_a", "package"): "horizontalFirst",
        ("package", "switch_b"): "horizontalFirst",
        ("switch_b", "switch_c"): "horizontalFirst",
        ("switch_c", "switch_d"): "horizontalFirst",
        ("switch_d", "destination"): "horizontalFirst",
    }


def build_late_tap_chain_generated_level(times: list[float]) -> GeneratedLevel:
    positions = late_tap_chain_positions()
    level = LevelDocument(
        id="level_late_tap_chain",
        name="Late Tap Chain",
        graph=RouteGraph(
            nodes=[
                RouteNode(id=node_id, x=x, y=y, outgoingEdgeIDs=_outgoing_edge_ids_for(node_id))
                for node_id, (x, y) in positions.items()
            ],
            edges=[
                RouteEdge(id="e_start_switch_a", fromNodeID="start", toNodeID="switch_a", roadShape="horizontalFirst"),
                RouteEdge(id="e_switch_a_dead_end", fromNodeID="switch_a", toNodeID="dead_end_a", roadShape="verticalFirst"),
                RouteEdge(id="e_switch_a_package", fromNodeID="switch_a", toNodeID="package", roadShape="horizontalFirst"),
                RouteEdge(id="e_package_switch_b", fromNodeID="package", toNodeID="switch_b", roadShape="horizontalFirst"),
                RouteEdge(id="e_switch_b_dead_end", fromNodeID="switch_b", toNodeID="dead_end_b", roadShape="verticalFirst"),
                RouteEdge(id="e_switch_b_switch_c", fromNodeID="switch_b", toNodeID="switch_c", roadShape="horizontalFirst"),
                RouteEdge(id="e_switch_c_dead_end", fromNodeID="switch_c", toNodeID="dead_end_c", roadShape="verticalFirst"),
                RouteEdge(id="e_switch_c_switch_d", fromNodeID="switch_c", toNodeID="switch_d", roadShape="horizontalFirst"),
                RouteEdge(id="e_switch_d_dead_end", fromNodeID="switch_d", toNodeID="dead_end_d", roadShape="verticalFirst"),
                RouteEdge(id="e_switch_d_destination", fromNodeID="switch_d", toNodeID="destination", roadShape="horizontalFirst"),
            ],
        ),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=30,
        parTaps=4,
    )
    solution = Solution(
        levelID=level.id,
        description="Rotate each switch before arrival.",
        expectedOutcome="completed",
        maxTaps=4,
        requiresWithinTimeLimit=True,
        actions=[
            SolutionAction(timeSeconds=time_seconds, tapNodeID=node_id)
            for time_seconds, node_id in zip(times, late_tap_chain_tap_nodes())
        ],
        isPlaceholder=None,
    )
    return GeneratedLevel(
        level_document=level,
        solution=solution,
        template_name="late_tap_fixture",
        difficulty="hard",
        seed=28,
    )


def _outgoing_edge_ids_for(node_id: str) -> list[str]:
    return {
        "start": ["e_start_switch_a"],
        "switch_a": ["e_switch_a_dead_end", "e_switch_a_package"],
        "package": ["e_package_switch_b"],
        "switch_b": ["e_switch_b_dead_end", "e_switch_b_switch_c"],
        "switch_c": ["e_switch_c_dead_end", "e_switch_c_switch_d"],
        "switch_d": ["e_switch_d_dead_end", "e_switch_d_destination"],
    }.get(node_id, [])
