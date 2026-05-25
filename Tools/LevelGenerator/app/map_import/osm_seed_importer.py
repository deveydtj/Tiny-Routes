from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class MapImportDependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class MapSeedNode:
    id: str
    x: float
    y: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MapSeedEdge:
    id: str
    from_node_id: str
    to_node_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MapSeedGraph:
    nodes: list[MapSeedNode]
    edges: list[MapSeedEdge]
    attribution: str = "Contains information from OpenStreetMap."


class OSMSeedImporter:
    def import_bbox(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        network_type: str = "drive",
    ) -> MapSeedGraph:
        ox = self._load_osmnx()
        graph = ox.graph_from_bbox(north, south, east, west, network_type=network_type)
        return self._from_osmnx_graph(graph)

    def import_place(self, place_name: str, network_type: str = "drive") -> MapSeedGraph:
        ox = self._load_osmnx()
        graph = ox.graph_from_place(place_name, network_type=network_type)
        return self._from_osmnx_graph(graph)

    def _load_osmnx(self):
        try:
            import osmnx as ox  # type: ignore[import-not-found]
        except ImportError as exc:
            raise MapImportDependencyError(
                "Optional map import dependencies are not installed. "
                "Install Tools/LevelGenerator/requirements-map.txt to use OSM imports."
            ) from exc
        return ox

    def _from_osmnx_graph(self, graph) -> MapSeedGraph:
        nodes = [
            MapSeedNode(id=str(node_id), x=float(data.get("x", 0.0)), y=float(data.get("y", 0.0)), metadata=dict(data))
            for node_id, data in graph.nodes(data=True)
        ]
        edges: list[MapSeedEdge] = []
        for index, (from_node, to_node, data) in enumerate(graph.edges(data=True)):
            edges.append(
                MapSeedEdge(
                    id=f"osm_edge_{index}",
                    from_node_id=str(from_node),
                    to_node_id=str(to_node),
                    metadata=dict(data),
                )
            )
        return MapSeedGraph(nodes=nodes, edges=edges)
