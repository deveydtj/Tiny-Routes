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
