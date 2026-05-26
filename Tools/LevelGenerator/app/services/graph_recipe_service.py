from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from ..random_source import RandomSource


class GraphRecipeService:
    def generate_recipe(self, level_id: str, preset: DifficultyPreset, rng: RandomSource) -> GraphRecipe:
        required_path = self._required_path(preset, rng)
        switch_nodes = self._switch_nodes_for_path(required_path, preset)
        nodes = [GraphRecipeNode(node_id, self._role_for_node(node_id)) for node_id in required_path]
        edges: list[GraphRecipeEdge] = []
        dead_end_count = rng.randint(*preset.dead_end_count_range)
        if not switch_nodes:
            dead_end_count = 0

        for index in range(dead_end_count):
            parent = switch_nodes[index % len(switch_nodes)] if switch_nodes else required_path[max(0, len(required_path) - 2)]
            dead_id = f"dead_end_{chr(ord('a') + index)}"
            nodes.append(GraphRecipeNode(dead_id, "dead_end"))
            edges.append(GraphRecipeEdge(parent, dead_id))

        for from_node_id, to_node_id in zip(required_path, required_path[1:]):
            edges.append(GraphRecipeEdge(from_node_id, to_node_id))

        notes: list[str] = []
        tap_node_ids = list(switch_nodes)
        if preset.allow_return_loops and rng.bool(0.35) and len(required_path) >= 5:
            return_node = required_path[-2]
            target_node = switch_nodes[0] if switch_nodes else required_path[1]
            edges.append(GraphRecipeEdge(return_node, target_node))
            tap_node_ids.append(target_node)
            notes.append("return_loop")
        if preset.allow_ring_routes and rng.bool(0.35) and len(required_path) >= 6:
            edges.append(GraphRecipeEdge(required_path[-3], required_path[1]))
            notes.append("ring_loop")

        recipe = GraphRecipe(
            level_id=level_id,
            difficulty=preset.name,
            nodes=tuple(nodes),
            edges=tuple(edges),
            required_path=tuple(required_path),
            tap_node_ids=tuple(tap_node_ids[: preset.required_tap_range[1]]),
            notes=tuple(notes),
        )
        issues = recipe.validate()
        if issues:
            raise ValueError(f"Invalid graph recipe: {', '.join(issues)}")
        return recipe

    def _required_path(self, preset: DifficultyPreset, rng: RandomSource) -> list[str]:
        if preset.name == "tutorial":
            return ["start", "package", "destination"]
        if preset.name == "easy":
            return ["start", "switch_a", "package", "destination"]
        if preset.name == "medium":
            return ["start", "switch_a", "package", "switch_b", "destination"]
        hard_middle = ["switch_a", "package", "switch_b", "switch_c"]
        if rng.bool(0.5):
            hard_middle.append("switch_d")
        return ["start", *hard_middle, "destination"]

    def _switch_nodes_for_path(self, required_path: list[str], preset: DifficultyPreset) -> list[str]:
        switch_nodes = [node_id for node_id in required_path if node_id.startswith("switch_")]
        minimum, maximum = preset.required_tap_range
        return switch_nodes[: max(minimum, min(maximum, len(switch_nodes)))]

    def _role_for_node(self, node_id: str) -> str:
        if node_id == "start":
            return "start"
        if node_id == "package":
            return "package"
        if node_id == "destination":
            return "destination"
        if node_id.startswith("switch_"):
            return "switch"
        return "route"
