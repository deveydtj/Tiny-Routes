from __future__ import annotations

from ..level_numbering import format_level_id
from ..random_source import RandomSource
from ..services.difficulty_service import DifficultyService
from ..templates.single_switch_template import SingleSwitchTemplate
from .map_graph_simplifier import MapGraphSimplifier
from .osm_seed_importer import MapSeedGraph, MapSeedNode


class MapSeedToTemplateAdapter:
    """Applies simplified map geometry to generated templates while preserving game roles."""

    def adapt_to_generated_level(
        self,
        seed_graph: MapSeedGraph,
        level_number: int,
        difficulty: str = "easy",
        seed: int = 0,
    ):
        preset = DifficultyService().get_preset(difficulty)
        template = SingleSwitchTemplate()
        generated = template.generate(format_level_id(level_number), level_number, preset, RandomSource(seed))
        return self.apply_to_generated_level(seed_graph, generated, RandomSource(seed))

    def apply_to_generated_level(self, seed_graph: MapSeedGraph, generated, rng: RandomSource):
        simplified = MapGraphSimplifier().simplify(seed_graph, max_nodes=max(len(generated.level_document.graph.nodes), 3), seed=rng.seed)
        if len(simplified.nodes) < 3:
            generated.generation_notes.append("Map seed had too few usable nodes; procedural layout was kept.")
            return generated

        selected = self._select_role_nodes(simplified.nodes, generated, rng)
        for node in generated.level_document.graph.nodes:
            seed_node = selected.get(node.id)
            if seed_node is not None:
                node.x = seed_node.x
                node.y = seed_node.y

        generated.generation_notes.append(f"Map attribution: {simplified.attribution}")
        generated.generation_notes.append("Map seed geometry influenced generated node positions.")
        return generated

    def _select_role_nodes(self, seed_nodes: list[MapSeedNode], generated, rng: RandomSource) -> dict[str, MapSeedNode]:
        by_x = sorted(seed_nodes, key=lambda node: (node.x, node.y, node.id))
        by_degree_hint = sorted(seed_nodes, key=lambda node: (node.metadata.get("degree", 0), node.id), reverse=True)
        mapping: dict[str, MapSeedNode] = {}
        level = generated.level_document
        mapping[level.startNodeID] = by_x[0]
        mapping[level.destinationNodeID] = by_x[-1]
        mapping[level.packageNodeID] = by_x[len(by_x) // 2]

        remaining = [node for node in by_degree_hint if node not in mapping.values()]
        fallback = [node for node in by_x if node not in mapping.values()]
        switch_nodes = [node for node in level.graph.nodes if len(node.outgoingEdgeIDs) > 1]
        for index, level_node in enumerate(switch_nodes):
            candidates = remaining or fallback
            if not candidates:
                break
            selected = candidates[index % len(candidates)]
            mapping[level_node.id] = selected

        unmapped_level_nodes = [node for node in level.graph.nodes if node.id not in mapping]
        available = [node for node in by_x if node not in mapping.values()]
        for index, level_node in enumerate(unmapped_level_nodes):
            if not available:
                break
            mapping[level_node.id] = available[index % len(available)]
        return mapping
