from __future__ import annotations

from .graph_layout_service import GraphLayoutService


class LayoutGeometricValidationService:
    """Provides topology-agnostic edge and node geometry validation."""

    def __init__(self, geometry: GraphLayoutService | None = None) -> None:
        self._geometry = geometry or GraphLayoutService()

    def crossings(self, positions, edges) -> tuple[tuple[str | None, str | None], ...]:
        return tuple(self._geometry.edge_crossings(positions, edges))

    def spacing_issues(self, positions, edges, minimum_distance: float) -> tuple[tuple[str, str], ...]:
        return tuple(self._geometry.edge_spacing_issues(positions, edges, minimum_distance))
