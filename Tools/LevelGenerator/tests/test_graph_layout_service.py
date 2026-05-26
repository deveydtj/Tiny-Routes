from __future__ import annotations

from app.services.graph_layout_service import BoundingBox, GraphLayoutService


def test_overlap_detection() -> None:
    layout = GraphLayoutService(minimum_node_distance=0.5)

    assert layout.has_overlaps({"a": (0, 0), "b": (0.1, 0.1)}) is True
    assert layout.has_overlaps({"a": (0, 0), "b": (1, 1)}) is False


def test_bounds_checking() -> None:
    layout = GraphLayoutService(bounds=BoundingBox(-1, 1, -1, 1))

    assert layout.is_inside_bounds(0, 0) is True
    assert layout.is_inside_bounds(2, 0) is False


def test_transform_helpers_snap_and_keep_shape() -> None:
    layout = GraphLayoutService(bounds=BoundingBox(-2, 2, -2, 2), grid_size=0.05)
    positions = {"a": (-1, 0), "b": (1, 0)}

    assert layout.scale_positions(positions, 0.5) == {"a": (-0.5, 0.0), "b": (0.5, 0.0)}
    assert layout.translate_positions(positions, 0.1, -0.1) == {"a": (-0.9, -0.1), "b": (1.1, -0.1)}
    assert layout.rotate_positions({"a": (1, 0)}, 90) == {"a": (0.0, 1.0)}


def test_edge_crossing_detection_ignores_shared_endpoints() -> None:
    layout = GraphLayoutService()
    positions = {"a": (0, 0), "b": (1, 1), "c": (0, 1), "d": (1, 0), "e": (2, 1)}

    crossings = layout.edge_crossings(
        positions,
        [("a", "b", "ab"), ("c", "d", "cd"), ("b", "e", "be")],
    )

    assert crossings == [("ab", "cd")]


def test_readability_summary_counts_spacing_issues() -> None:
    layout = GraphLayoutService()
    positions = {"a": (0, 0), "b": (1, 0), "near": (0.5, 0.02)}

    summary = layout.readability_summary(positions, [("a", "b", "ab")], minimum_edge_spacing=0.1)

    assert summary["edgeSpacingIssues"] == 1
