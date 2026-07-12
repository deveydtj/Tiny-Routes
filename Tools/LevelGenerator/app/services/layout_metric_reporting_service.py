from __future__ import annotations

from .graph_layout_service import GraphLayoutService


class LayoutMetricReportingService:
    """Builds stable layout metrics separately from validation decisions."""

    def __init__(self, geometry: GraphLayoutService | None = None) -> None:
        self._geometry = geometry or GraphLayoutService()

    def readability_metrics(self, positions, edges, minimum_edge_spacing: float = 0.1) -> dict[str, int]:
        return self._geometry.readability_summary(positions, edges, minimum_edge_spacing)
