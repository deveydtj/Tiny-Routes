from __future__ import annotations

from ..models.generated_level import GeneratedLevel
from ..models.graph_recipe import GraphRecipe
from ..random_source import RandomSource
from ..templates.four_way_intersection_template import _variant_spec as four_way_variant_spec
from ..templates.package_gate_template import _variant_spec as package_gate_variant_spec
from ..templates.return_loop_template import _variant_spec as return_loop_variant_spec
from ..templates.ring_route_template import _positions_for_variant as ring_route_positions_for_variant
from ..templates.single_switch_template import _variant_spec as single_switch_variant_spec
from .difficulty_service import DifficultyService
from .graph_builder_service import GraphBuilderService
from .layout_variant_service import LayoutVariantService
from .level_naming_service import LevelNamingService
from .solution_builder_service import SolutionBuilderService


class RecipeToLevelBuilderService:
    def __init__(self) -> None:
        self.difficulty = DifficultyService()
        self.naming = LevelNamingService()
        self.solution_builder = SolutionBuilderService()
        self.layout_variants = LayoutVariantService()

    def build_level(
        self,
        recipe: GraphRecipe,
        level_number: int,
        seed: int = 0,
        layout_variant_name: str = "normal",
        road_shape_strategy: str = "auto",
    ) -> GeneratedLevel:
        issues = recipe.validate()
        if issues:
            raise ValueError(f"Invalid graph recipe: {', '.join(issues)}")

        preset = self.difficulty.get_preset(recipe.difficulty)
        rng = RandomSource(seed)
        base_positions = self._assign_positions(recipe)
        layout_variant = self.layout_variants.apply_variant(layout_variant_name, base_positions, rng, preset)
        positions = layout_variant.positions
        builder = GraphBuilderService()
        for node in recipe.nodes:
            builder.add_node(node.id, *positions[node.id])
        for edge_index, edge in enumerate(recipe.edges):
            builder.add_edge(
                edge.from_node_id,
                edge.to_node_id,
                road_shape=self._road_shape_for_strategy(road_shape_strategy, edge_index),
            )

        time_limit = self._time_limit(recipe.required_path, positions, preset.time_limit_padding_seconds)
        level = builder.build_level_document(
            level_id=recipe.level_id,
            name=self.naming.name_for_level_number(level_number),
            start_node_id="start",
            package_node_id=recipe.package_node_id,
            destination_node_id=recipe.destination_node_id,
            time_limit_seconds=time_limit,
            par_taps=len(recipe.tap_node_ids),
        )
        description = "Follow the generated graph recipe route and rotate each switch before arrival."
        try:
            solution = self.solution_builder.build_route_timed_tap_solution(
                recipe.level_id,
                list(recipe.tap_node_ids),
                list(recipe.required_path),
                positions,
                preset,
                description,
                route_edge_shapes={
                    (edge.fromNodeID, edge.toNodeID): edge.roadShape
                    for edge in level.graph.edges
                },
            )
        except ValueError:
            solution = self.solution_builder.build_tap_solution(
                recipe.level_id,
                list(recipe.tap_node_ids),
                preset,
                description,
            )
        return GeneratedLevel(
            level_document=level,
            solution=solution,
            template_name=recipe.family_name,
            difficulty=recipe.difficulty,
            seed=seed,
            generation_notes=[
                *recipe.notes,
                f"Abstract graph signature: {recipe.abstract_signature[:12]}",
                f"Selected layout variant: {layout_variant.name}",
                f"Selected road-shape strategy: {road_shape_strategy}",
            ],
            recipe_family=recipe.family_name,
            recipe_variant=recipe.variant_name,
            abstract_graph_signature=recipe.abstract_signature,
            selected_layout_variant=layout_variant.name,
            selected_road_shape_strategy=road_shape_strategy,
            abstract_solution_metadata=recipe.solved_metadata,
        )

    def _assign_positions(self, recipe: GraphRecipe) -> dict[str, tuple[float, float]]:
        template_positions = self._template_positions_for_recipe(recipe)
        if template_positions is not None:
            return template_positions

        route = list(recipe.required_path)
        x_step = 2.2 / max(len(route) - 1, 1)
        positions: dict[str, tuple[float, float]] = {}
        for index, node_id in enumerate(route):
            y = 0.0
            if node_id == recipe.package_node_id:
                y = 0.55
            elif node_id.startswith("switch_"):
                y = -0.2 if index % 2 == 0 else 0.2
            elif node_id == recipe.destination_node_id:
                y = -0.45
            positions[node_id] = (round(-1.1 + (index * x_step), 4), y)

        parent_counts: dict[str, int] = {}
        for edge in recipe.edges:
            if edge.to_node_id in positions:
                continue
            parent_position = positions[edge.from_node_id]
            count = parent_counts.get(edge.from_node_id, 0)
            parent_counts[edge.from_node_id] = count + 1
            y_offset = 0.72 if count % 2 == 0 else -0.72
            positions[edge.to_node_id] = (parent_position[0], round(parent_position[1] + y_offset, 4))
        return positions

    def _template_positions_for_recipe(self, recipe: GraphRecipe) -> dict[str, tuple[float, float]] | None:
        try:
            if recipe.family_name == "single_switch":
                include_approach = "approach" in {node.id for node in recipe.nodes}
                positions, _switch_id, _dead_end_id, _route = single_switch_variant_spec(
                    recipe.variant_name,
                    include_approach,
                )
                return positions
            if recipe.family_name == "package_gate":
                positions, _edges, _taps, _route = package_gate_variant_spec(recipe.variant_name)
                return positions
            if recipe.family_name == "return_loop":
                positions, _edges, _taps, _route = return_loop_variant_spec(recipe.variant_name)
                return positions
            if recipe.family_name == "ring_route":
                return ring_route_positions_for_variant(recipe.variant_name)
            if recipe.family_name == "four_way_intersection":
                positions, _edges, _taps, _route = four_way_variant_spec(recipe.variant_name)
                return positions
        except Exception:
            return None
        return None

    def _time_limit(
        self,
        route_node_ids: tuple[str, ...],
        positions: dict[str, tuple[float, float]],
        padding_seconds: int,
    ) -> int:
        distance = 0.0
        for from_node_id, to_node_id in zip(route_node_ids, route_node_ids[1:]):
            from_position = positions[from_node_id]
            to_position = positions[to_node_id]
            distance += abs(from_position[0] - to_position[0]) + abs(from_position[1] - to_position[1])
        return max(30, int(round(distance + padding_seconds + 6)))

    def _road_shape_for_strategy(self, strategy: str, edge_index: int) -> str | None:
        normalized = strategy.strip().lower().replace("-", "_")
        if normalized in {"", "auto"}:
            return None
        if normalized == "horizontal_first":
            return "horizontalFirst"
        if normalized == "vertical_first":
            return "verticalFirst"
        if normalized == "alternating":
            return "horizontalFirst" if edge_index % 2 == 0 else "verticalFirst"
        raise ValueError(f"Unknown road-shape strategy: {strategy}")
