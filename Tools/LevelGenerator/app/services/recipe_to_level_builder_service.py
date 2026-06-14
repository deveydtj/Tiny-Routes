from __future__ import annotations

from dataclasses import replace

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
        layout_orientation_preference: str = "horizontal",
        layout_size_profile: str = "standard_portrait",
        orientation_selection_reason: str = "default_horizontal",
        road_shape_strategy: str = "auto",
    ) -> GeneratedLevel:
        issues = recipe.validate()
        if issues:
            raise ValueError(f"Invalid graph recipe: {', '.join(issues)}")

        preset = self._preset_for_layout_size_profile(
            self.difficulty.get_preset(recipe.difficulty),
            layout_size_profile,
        )
        rng = RandomSource(seed)
        layout_plan = self.layout_planner.plan_layout(
            recipe,
            preset,
            rng,
            layout_variant_name,
            layout_orientation_preference=layout_orientation_preference,
            layout_size_profile=layout_size_profile,
            orientation_selection_reason=orientation_selection_reason,
        )
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
        edge_shapes = dict(road_shape_plan.edge_shapes)
        revisited_route_shape_overrides = self._apply_revisited_route_shape_overrides(
            edge_shapes,
            recipe.required_path,
        )
        if revisited_route_shape_overrides:
            road_shape_plan = self.road_shape_service.plan_for_assignment(
                positions,
                recipe_edges,
                edge_shapes,
                required_path=recipe.required_path,
                strategy=f"{road_shape_plan.strategy}_with_revisit_overrides",
                important_node_ids=("start", recipe.package_node_id, recipe.destination_node_id),
            )
        builder = GraphBuilderService()
        for node in recipe.nodes:
            builder.add_node(node.id, *positions[node.id])
        for edge in recipe.edges:
            builder.add_edge(
                edge.from_node_id,
                edge.to_node_id,
                road_shape=edge_shapes[(edge.from_node_id, edge.to_node_id)],
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
                lead_time_seconds=max(0.35, preset.min_tap_spacing_seconds + 0.05),
                route_edge_shapes={
                    (edge.fromNodeID, edge.toNodeID): edge.roadShape
                    for edge in level.graph.edges
                },
                route_edge_ids_by_pair={
                    (edge.fromNodeID, edge.toNodeID): edge.id
                    for edge in level.graph.edges
                },
                outgoing_edge_ids_by_node={
                    node.id: list(node.outgoingEdgeIDs)
                    for node in level.graph.nodes
                },
            )
        except ValueError:
            solution = self.solution_builder.build_tap_solution(
                recipe.level_id,
                list(recipe.tap_node_ids),
                preset,
                description,
            )
        self.solution_builder.apply_generation_metadata(
            solution,
            template_name=recipe.family_name,
            seed=seed,
            recipe_family=recipe.family_name,
            recipe_variant=recipe.variant_name,
            solution_route=recipe.required_path,
        )
        mechanic_notes = []
        if recipe.mechanic_tags:
            mechanic_notes.append(f"Mechanic tags: {', '.join(recipe.mechanic_tags)}")
        if recipe.primary_mechanic_tag:
            mechanic_notes.append(f"Primary mechanic tag: {recipe.primary_mechanic_tag}")
        if recipe.topology_class:
            mechanic_notes.append(f"Topology class: {recipe.topology_class}")
        if recipe.unlock_requirement:
            mechanic_notes.append(f"Unlock requirement: {recipe.unlock_requirement}")
        if recipe.prior_mechanic_dependency:
            mechanic_notes.append(f"Prior mechanic dependency: {recipe.prior_mechanic_dependency}")
        return GeneratedLevel(
            level_document=level,
            solution=solution,
            template_name=recipe.family_name,
            difficulty=recipe.difficulty,
            seed=seed,
            generation_notes=[
                *recipe.notes,
                *mechanic_notes,
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
            road_shape_metadata={
                **road_shape_plan.metadata,
                "revisitedRouteShapeOverrides": revisited_route_shape_overrides,
            },
            mechanic_tags=recipe.mechanic_tags,
            primary_mechanic_tag=recipe.primary_mechanic_tag,
            topology_class=recipe.topology_class,
            unlock_requirement=recipe.unlock_requirement,
            prior_mechanic_dependency=recipe.prior_mechanic_dependency,
            mechanic_metadata=recipe.mechanic_metadata,
        )

    def _preset_for_layout_size_profile(self, preset, layout_size_profile: str):
        if layout_size_profile != "large_portrait":
            return preset
        return replace(
            preset,
            coordinate_bounds=(-1.15, 1.15, -3.4, 1.35),
            minimum_node_distance=max(preset.minimum_node_distance, 0.24),
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

    def _apply_revisited_route_shape_overrides(
        self,
        edge_shapes: dict[tuple[str, str], str],
        required_path: tuple[str, ...],
    ) -> list[dict[str, str]]:
        overrides: list[dict[str, str]] = []
        seen: dict[str, int] = {}
        for index, node_id in enumerate(required_path):
            first_index = seen.get(node_id)
            if first_index is None:
                seen[node_id] = index
                continue
            if index <= first_index + 1:
                continue

            candidate_edges = [
                (node_id, required_path[first_index + 1]) if first_index + 1 < len(required_path) else None,
                (required_path[index - 1], node_id) if index > 0 else None,
            ]
            for edge in candidate_edges:
                if edge is None or edge not in edge_shapes:
                    continue
                previous = edge_shapes[edge]
                edge_shapes[edge] = "verticalFirst"
                if previous != "verticalFirst":
                    overrides.append(
                        {
                            "fromNodeID": edge[0],
                            "toNodeID": edge[1],
                            "fromRoadShape": previous,
                            "toRoadShape": "verticalFirst",
                        }
                    )
        return overrides
