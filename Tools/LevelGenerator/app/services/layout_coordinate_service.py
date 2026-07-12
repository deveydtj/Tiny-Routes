from __future__ import annotations

from ..models.layout_constraints import BoundingBox
from .graph_layout_service import GraphLayoutService


class LayoutCoordinateService:
    """Owns coordinate transforms, snapping, bounds, and node placement checks."""

    def __init__(self, bounds: BoundingBox | None = None, minimum_node_distance: float = 0.2, grid_size: float = 0.05) -> None:
        self._geometry = GraphLayoutService(bounds, minimum_node_distance, grid_size)

    def snap_point(self, x: float, y: float) -> tuple[float, float]:
        return self._geometry.snap_point(x, y)

    def normalize(self, positions: dict[str, tuple[float, float]], padding: float = 0.05) -> dict[str, tuple[float, float]]:
        return self._geometry.normalize_positions(positions, padding)

    def validate(self, positions: dict[str, tuple[float, float]]) -> tuple[str, ...]:
        return tuple(self._geometry.validate_positions(positions))
