from __future__ import annotations

from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.graph_layout_service import BoundingBox, GraphLayoutPlannerService, GraphLayoutService


def test_overlap_detection() -> None:
    layout = GraphLayoutService(minimum_node_distance=0.5)

    assert layout.has_overlaps({"a": (0, 0), "b": (0.1, 0.1)}) is True
    assert layout.has_overlaps({"a": (0, 0), "b": (1, 1)}) is False


def test_bounds_checking() -> None:
    layout = GraphLayoutService(bounds=BoundingBox(-1, 1, -1, 1))

    assert layout.is_inside_bounds(0, 0) is True
    assert layout.is_inside_bounds(2, 0) is False


def test_transform_helpers_snap_and_keep_shape() -> None:
    layout = GraphLayoutService(bounds=BoundingBox(-2, 2, -2, 2), grid_size=0.05)
    positions = {"a": (-1, 0), "b": (1, 0)}

    assert layout.scale_positions(positions, 0.5) == {"a": (-0.5, 0.0), "b": (0.5, 0.0)}
    assert layout.translate_positions(positions, 0.1, -0.1) == {"a": (-0.9, -0.1), "b": (1.1, -0.1)}
    assert layout.rotate_positions({"a": (1, 0)}, 90) == {"a": (0.0, 1.0)}


def test_edge_crossing_detection_ignores_shared_endpoints() -> None:
    layout = GraphLayoutService()
    positions = {"a": (0, 0), "b": (1, 1), "c": (0, 1), "d": (1, 0), "e": (2, 1)}

    crossings = layout.edge_crossings(
        positions,
        [("a", "b", "ab"), ("c", "d", "cd"), ("b", "e", "be")],
    )

    assert crossings == [("ab", "cd")]


def test_readability_summary_counts_spacing_issues() -> None:
    layout = GraphLayoutService()
    positions = {"a": (0, 0), "b": (1, 0), "near": (0.5, 0.02)}

    summary = layout.readability_summary(positions, [("a", "b", "ab")], minimum_edge_spacing=0.1)

    assert summary["edgeSpacingIssues"] == 1


def test_layout_planner_strategies_stay_inside_preset_bounds() -> None:
    planner = GraphLayoutPlannerService()
    preset = DifficultyService().get_preset("expert")
    recipes = [
        _recipe("straight_delivery"),
        _recipe("package_gate"),
        _recipe("return_loop"),
        _recipe("ring_route"),
        _recipe("four_way_intersection"),
    ]

    for index, recipe in enumerate(recipes):
        result = planner.plan_layout(recipe, preset, RandomSource(index), "normal")

        assert result.is_valid, (result.strategy, result.validation_issues)
        assert result.strategy in planner.strategy_names
        assert all(GraphLayoutService(BoundingBox(*preset.coordinate_bounds)).is_inside_bounds(*point) for point in result.positions.values())


def test_layout_planner_keeps_important_nodes_spaced() -> None:
    planner = GraphLayoutPlannerService()
    preset = DifficultyService().get_preset("easy")
    recipe = _recipe("package_gate")

    result = planner.plan_layout(recipe, preset, RandomSource(7), "wide")

    layout = GraphLayoutService(BoundingBox(*preset.coordinate_bounds))
    assert layout.point_distance(result.positions["start"], result.positions["package"]) >= preset.minimum_node_distance * 1.6
    assert layout.point_distance(result.positions["package"], result.positions["destination"]) >= preset.minimum_node_distance * 2.0


def test_layout_planner_variation_changes_layout_hash() -> None:
    planner = GraphLayoutPlannerService()
    preset = DifficultyService().get_preset("easy")
    recipe = _recipe("single_switch")

    normal = planner.plan_layout(recipe, preset, RandomSource(4), "normal")
    wide = planner.plan_layout(recipe, preset, RandomSource(4), "wide")

    assert normal.metadata["layoutHash"] != wide.metadata["layoutHash"]


def test_layout_planner_rejects_clustered_layouts() -> None:
    planner = GraphLayoutPlannerService()
    preset = DifficultyService().get_preset("easy")
    recipe = _recipe("single_switch")
    positions = {
        node.id: (0.0, 0.0)
        for node in recipe.nodes
    }

    issues = planner.validate_layout(recipe, preset, positions)

    assert "layout_node_cluster" in {issue.code for issue in issues}
    assert "layout_important_nodes_too_close" in {issue.code for issue in issues}


def _recipe(family_name: str) -> GraphRecipe:
    if family_name == "package_gate":
        nodes = ("start", "switch_a", "package", "switch_b", "destination", "dead_end_a", "dead_end_b")
        edges = (
            ("start", "switch_a"),
            ("switch_a", "dead_end_a"),
            ("switch_a", "package"),
            ("package", "switch_b"),
            ("switch_b", "dead_end_b"),
            ("switch_b", "destination"),
        )
        route = ("start", "switch_a", "package", "switch_b", "destination")
        taps = ("switch_a", "switch_b")
    elif family_name == "return_loop":
        nodes = ("start", "switch_a", "package", "switch_b", "loop_a", "destination", "dead_end_a")
        edges = (
            ("start", "switch_a"),
            ("switch_a", "dead_end_a"),
            ("switch_a", "package"),
            ("package", "switch_b"),
            ("switch_b", "loop_a"),
            ("loop_a", "switch_a"),
            ("switch_b", "destination"),
        )
        route = ("start", "switch_a", "package", "switch_b", "destination")
        taps = ("switch_a", "switch_b")
    elif family_name == "ring_route":
        nodes = ("start", "hub", "ring_a", "ring_b", "package", "gate", "destination", "dead_end_a", "dead_end_b")
        edges = (
            ("start", "hub"),
            ("hub", "ring_a"),
            ("hub", "package"),
            ("ring_a", "ring_b"),
            ("ring_b", "gate"),
            ("ring_b", "dead_end_a"),
            ("package", "ring_b"),
            ("gate", "dead_end_b"),
            ("gate", "destination"),
        )
        route = ("start", "hub", "package", "ring_b", "gate", "destination")
        taps = ("hub", "ring_b", "gate")
    elif family_name == "four_way_intersection":
        nodes = ("start", "hub", "north", "east", "package", "destination", "dead_end_a")
        edges = (
            ("start", "hub"),
            ("hub", "north"),
            ("hub", "east"),
            ("hub", "dead_end_a"),
            ("hub", "package"),
            ("package", "destination"),
        )
        route = ("start", "hub", "package", "destination")
        taps = ("hub",)
    elif family_name == "single_switch":
        nodes = ("start", "switch_a", "package", "destination", "dead_end_a")
        edges = (
            ("start", "switch_a"),
            ("switch_a", "dead_end_a"),
            ("switch_a", "package"),
            ("package", "destination"),
        )
        route = ("start", "switch_a", "package", "destination")
        taps = ("switch_a",)
    else:
        nodes = ("start", "node_a", "package", "destination")
        edges = (("start", "node_a"), ("node_a", "package"), ("package", "destination"))
        route = nodes
        taps = ()

    return GraphRecipe(
        level_id="level_999",
        difficulty="easy",
        nodes=tuple(GraphRecipeNode(node_id, _role(node_id)) for node_id in nodes),
        edges=tuple(GraphRecipeEdge(from_id, to_id) for from_id, to_id in edges),
        required_path=route,
        tap_node_ids=taps,
        family_name=family_name,
        variant_name="test",
    )


def _role(node_id: str) -> str:
    if node_id == "start":
        return "start"
    if node_id == "package":
        return "package"
    if node_id == "destination":
        return "destination"
    if node_id.startswith("dead_end"):
        return "dead_end"
    if node_id.startswith("switch") or node_id in {"hub", "gate"}:
        return "switch"
    return "route"
