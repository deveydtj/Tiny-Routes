from __future__ import annotations

from ..models.generated_level import GeneratedLevel
from ..models.graph_recipe import GraphRecipe
from ..random_source import RandomSource
from .difficulty_service import DifficultyService
from .graph_builder_service import GraphBuilderService
from .graph_layout_service import GraphLayoutPlannerService
from .level_naming_service import LevelNamingService
from .road_shape_service import RoadShapeService
from .solution_builder_service import SolutionBuilderService


class RecipeToLevelBuilderService:
    def __init__(self) -> None:
        self.difficulty = DifficultyService()
        self.naming = LevelNamingService()
        self.solution_builder = SolutionBuilderService()
        self.layout_planner = GraphLayoutPlannerService()
        self.road_shape_service = RoadShapeService()

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
        layout_plan = self.layout_planner.plan_layout(recipe, preset, rng, layout_variant_name)
        positions = layout_plan.positions
        recipe_edges = [
            (edge.from_node_id, edge.to_node_id)
            for edge in recipe.edges
        ]
        road_shape_plan = self.road_shape_service.plan_for_graph(
            positions,
            recipe_edges,
            required_path=recipe.required_path,
            strategy=road_shape_strategy,
            important_node_ids=("start", recipe.package_node_id, recipe.destination_node_id),
        )
        builder = GraphBuilderService()
        for node in recipe.nodes:
            builder.add_node(node.id, *positions[node.id])
        for edge in recipe.edges:
            builder.add_edge(
                edge.from_node_id,
                edge.to_node_id,
                road_shape=road_shape_plan.edge_shapes[(edge.from_node_id, edge.to_node_id)],
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
                f"Selected layout strategy: {layout_plan.strategy}",
                f"Selected layout variant: {layout_plan.variant}",
                f"Selected road-shape strategy: {road_shape_plan.strategy}",
                f"Road-shape score: {road_shape_plan.score}",
            ],
            recipe_family=recipe.family_name,
            recipe_variant=recipe.variant_name,
            abstract_graph_signature=recipe.abstract_signature,
            selected_layout_variant=layout_plan.variant,
            selected_road_shape_strategy=road_shape_plan.strategy,
            abstract_solution_metadata=recipe.solved_metadata,
            layout_metadata=layout_plan.metadata,
            road_shape_metadata=road_shape_plan.metadata,
        )

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
