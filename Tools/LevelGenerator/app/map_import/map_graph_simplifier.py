from __future__ import annotations

from collections import defaultdict, deque
import random

from .osm_seed_importer import MapSeedEdge, MapSeedGraph, MapSeedNode


class MapGraphSimplifier:
    def simplify(self, seed_graph: MapSeedGraph, max_nodes: int = 12, seed: int = 0) -> MapSeedGraph:
        deduped = self._remove_duplicate_edges(seed_graph)
        connected = self._largest_connected_component(deduped)
        connected = self._remove_isolated_nodes(connected)
        selected_nodes = self._select_nodes(connected, max_nodes=max_nodes, seed=seed)
        selected_ids = {node.id for node in selected_nodes}
        selected_edges = [
            edge
            for edge in connected.edges
            if edge.from_node_id in selected_ids and edge.to_node_id in selected_ids
        ]
        normalized_nodes = self._normalize_nodes(selected_nodes)
        return MapSeedGraph(nodes=normalized_nodes, edges=selected_edges, attribution=seed_graph.attribution)

    def _remove_duplicate_edges(self, seed_graph: MapSeedGraph) -> MapSeedGraph:
        seen: set[tuple[str, str]] = set()
        edges: list[MapSeedEdge] = []
        for edge in seed_graph.edges:
            key = (edge.from_node_id, edge.to_node_id)
            if key in seen:
                continue
            seen.add(key)
            edges.append(edge)
        return MapSeedGraph(nodes=list(seed_graph.nodes), edges=edges, attribution=seed_graph.attribution)

    def _remove_isolated_nodes(self, seed_graph: MapSeedGraph) -> MapSeedGraph:
        connected_ids = {
            node_id
            for edge in seed_graph.edges
            for node_id in (edge.from_node_id, edge.to_node_id)
        }
        return MapSeedGraph(
            nodes=[node for node in seed_graph.nodes if node.id in connected_ids],
            edges=list(seed_graph.edges),
            attribution=seed_graph.attribution,
        )

    def _select_nodes(self, seed_graph: MapSeedGraph, max_nodes: int, seed: int) -> list[MapSeedNode]:
        degree: dict[str, int] = defaultdict(int)
        for edge in seed_graph.edges:
            degree[edge.from_node_id] += 1
            degree[edge.to_node_id] += 1

        seeded_random = random.Random(seed)
        tie_breakers = {node.id: seeded_random.random() for node in seed_graph.nodes}
        sorted_nodes = sorted(
            seed_graph.nodes,
            key=lambda node: (-degree[node.id], self._turn_score(node), tie_breakers[node.id], node.id),
        )
        return sorted_nodes[:max_nodes]

    def _turn_score(self, node: MapSeedNode) -> float:
        highway = node.metadata.get("highway")
        if highway in {"traffic_signals", "stop", "crossing", "mini_roundabout"}:
            return -1.0
        return 0.0

    def _largest_connected_component(self, seed_graph: MapSeedGraph) -> MapSeedGraph:
        node_ids = {node.id for node in seed_graph.nodes}
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in seed_graph.edges:
            if edge.from_node_id in node_ids and edge.to_node_id in node_ids:
                adjacency[edge.from_node_id].add(edge.to_node_id)
                adjacency[edge.to_node_id].add(edge.from_node_id)

        seen: set[str] = set()
        components: list[set[str]] = []
        for node_id in node_ids:
            if node_id in seen:
                continue
            component: set[str] = set()
            queue = deque([node_id])
            while queue:
                current = queue.popleft()
                if current in component:
                    continue
                component.add(current)
                queue.extend(adjacency.get(current, set()))
            seen.update(component)
            components.append(component)

        largest = max(components, key=len, default=set())
        return MapSeedGraph(
            nodes=[node for node in seed_graph.nodes if node.id in largest],
            edges=[
                edge
                for edge in seed_graph.edges
                if edge.from_node_id in largest and edge.to_node_id in largest
            ],
            attribution=seed_graph.attribution,
        )

    def _normalize_nodes(self, nodes: list[MapSeedNode]) -> list[MapSeedNode]:
        if not nodes:
            return []
        min_x = min(node.x for node in nodes)
        max_x = max(node.x for node in nodes)
        min_y = min(node.y for node in nodes)
        max_y = max(node.y for node in nodes)
        width = max(max_x - min_x, 1e-9)
        height = max(max_y - min_y, 1e-9)
        normalized: list[MapSeedNode] = []
        for node in nodes:
            x = ((node.x - min_x) / width * 2.2) - 1.1
            y = ((node.y - min_y) / height * 2.0) - 1.0
            normalized.append(MapSeedNode(id=node.id, x=round(x, 4), y=round(y, 4), metadata=node.metadata))
        return normalized
