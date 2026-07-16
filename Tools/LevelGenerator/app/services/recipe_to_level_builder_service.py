from __future__ import annotations

from dataclasses import replace

from tiny_routes_core.models import LevelRules, SwitchInteractionMode

from ..models.generated_level import GeneratedLevel
from ..models.graph_recipe import GraphRecipe
from ..models.layout_constraints import ConstraintViolation
from ..models.layout_graph import LayoutGraph
from ..models.layout_result import LayoutResult
from ..random_source import RandomSource
from .difficulty_service import DifficultyService
from .decision_profile_service import DecisionProfileService
from .graph_builder_service import GraphBuilderService
from .graph_layout_service import GraphLayoutPlannerService
from .graph_layout_service import GraphLayoutService
from .layout_repair_service import LayoutRepairService
from .layout_readability_validator import LayoutReadabilityValidator
from .level_naming_service import LevelNamingService
from .road_shape_service import RoadShapeService
from .solution_builder_service import SolutionBuilderService
from .runtime_solution_search_service import RuntimeSolutionSearchService
from .topology_solver_service import TopologySolverService


class RecipeToLevelBuilderService:
    def __init__(self) -> None:
        self.difficulty = DifficultyService()
        self.naming = LevelNamingService()
        self.solution_builder = SolutionBuilderService()
        self.runtime_solution_search = RuntimeSolutionSearchService()
        self.topology_solver = TopologySolverService()
        self.layout_planner = GraphLayoutPlannerService()
        self.road_shape_service = RoadShapeService()
        self.decision_profiles = DecisionProfileService()
        self.layout_repair = LayoutRepairService()
        self.layout_readability = LayoutReadabilityValidator()

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
        if recipe.solved_metadata is None:
            recipe = self.topology_solver.solve(recipe, preset)
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
        layout_graph = LayoutGraph.from_recipe(recipe)
        edge_id_by_pair = {
            (edge.from_node_id, edge.to_node_id): edge.edge_id for edge in layout_graph.edges
        }
        initial_shapes = {
            edge_id_by_pair[edge]: self.road_shape_service.pick_for_positions(
                *positions[edge[0]], *positions[edge[1]]
            )
            for edge in recipe_edges
        }
        geometry = GraphLayoutService(
            minimum_node_distance=preset.minimum_node_distance,
        )

        def evaluate(candidate_positions, _candidate_shapes):
            violations = [
                ConstraintViolation(
                    "node_spacing_failure",
                    f"Nodes {first} and {second} overlap.",
                    node_id=second,
                )
                for first, second in geometry.overlapping_pairs(candidate_positions)
            ]
            violations.extend(
                ConstraintViolation(
                    "implicit_intersection_without_node",
                    "Roads cross without an explicit node.",
                    edge_id=first or second,
                )
                for first, second in geometry.edge_crossings(
                    candidate_positions,
                    [
                        (edge.from_node_id, edge.to_node_id, edge.edge_id)
                        for edge in layout_graph.edges
                    ],
                )
            )
            return violations

        repaired = self.layout_repair.repair(
            LayoutResult(positions=positions), layout_graph, initial_shapes, evaluate
        )
        positions = repaired.positions
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
                availability=edge.availability,
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
        level.rules = LevelRules(
            switch_interaction_mode=SwitchInteractionMode.LIVE_LOOKAHEAD,
            switch_lookahead_seconds=max(
                LevelRules.DEFAULT_LOOKAHEAD_SECONDS,
                preset.minimum_decision_window_seconds,
            ),
            switch_tap_cooldown_seconds=LevelRules.DEFAULT_TAP_COOLDOWN_SECONDS,
        )
        level._rules_present = True
        readability = self.layout_readability.report_for_level(
            level,
            preset=preset,
            layout_metadata=layout_plan.metadata,
        )
        if readability.has_errors:
            first = readability.errors[0]
            error = ValueError(
                f"Layout readability rejected before runtime timing: {first.message}"
            )
            error.code = first.code
            raise error
        description = "Follow the generated graph recipe route and rotate each switch before arrival."
        if recipe.solved_metadata is None:  # defensive: the solver contract guarantees metadata
            raise ValueError("runtime solution search requires solved topology metadata")
        runtime_solution = self.runtime_solution_search.search(level, recipe.solved_metadata)
        if not runtime_solution.passed:
            error = ValueError(
                f"Runtime solution search failed: {runtime_solution.failure_reason or 'unknown failure'}"
            )
            error.code = runtime_solution.failure_reason or "runtime_solution_search_failed"
            raise error
        solution = self.solution_builder.build_verified_runtime_solution(
            recipe.level_id,
            runtime_solution,
            description,
            solution_route=recipe.required_path,
        )
        self.solution_builder.apply_generation_metadata(
            solution,
            template_name=recipe.family_name,
            seed=seed,
            recipe_family=recipe.family_name,
            recipe_variant=recipe.variant_name,
            solution_route=recipe.required_path,
        )
        decision_profile = self.decision_profiles.analyze(
            recipe,
            topology_solutions=(recipe.solved_metadata,),
            runtime_solution=runtime_solution,
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
            runtime_solution_search_result=runtime_solution,
            layout_metadata={
                **layout_plan.metadata,
                "layoutRepairAttemptCount": len(repaired.attempted_repair_operations),
                "layoutRepairSuccessCount": len(repaired.repair_operations),
                "layoutRepairs": [
                    {
                        "kind": operation.kind.value,
                        "targetID": operation.target_id,
                        "deltaColumn": operation.delta_column,
                        "deltaRow": operation.delta_row,
                        "reason": operation.reason,
                    }
                    for operation in repaired.repair_operations
                ],
                "remainingRepairViolations": [violation.code for violation in repaired.violations],
            },
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
            decision_profile=decision_profile,
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
