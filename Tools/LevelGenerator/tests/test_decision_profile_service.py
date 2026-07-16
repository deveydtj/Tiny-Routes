from app.models.abstract_puzzle_solution import AbstractPuzzleSolutionMetadata
from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.models.runtime_solution_search import (
    RuntimeDecisionTimingDiagnostic,
    RuntimeSolutionAction,
    RuntimeSolutionSearchResult,
)
from app.services.decision_profile_service import DecisionProfileService


def _recipe(nodes, edges, required_path, package="package", destination="destination"):
    return GraphRecipe(
        level_id="profile_test",
        difficulty="medium",
        nodes=tuple(GraphRecipeNode(node) for node in nodes),
        edges=tuple(GraphRecipeEdge(start, end) for start, end in edges),
        required_path=tuple(required_path),
        tap_node_ids=(),
        package_node_id=package,
        destination_node_id=destination,
    )


def _metadata(path):
    return AbstractPuzzleSolutionMetadata(
        decision_node_ids=(),
        solution_switch_states=(),
        required_path=tuple(path),
        alternate_path_count=0,
        dead_end_count=0,
        failure_path_count=0,
        false_route_count=0,
        loop_count=0,
        minimum_required_decisions=0,
        optional_tap_count=0,
        repeated_switch_usage=False,
        package_before_destination=True,
    )


def test_three_independent_switches_have_high_independent_ratio():
    recipe = _recipe(
        ("start", "s1", "s2", "s3", "package", "destination", "d1", "d2", "d3"),
        (
            ("start", "s1"), ("s1", "d1"), ("s1", "s2"),
            ("s2", "d2"), ("s2", "s3"), ("s3", "d3"),
            ("s3", "package"), ("package", "destination"),
        ),
        ("start", "s1", "s2", "s3", "package", "destination"),
    )

    profile = DecisionProfileService().analyze(recipe, (_metadata(recipe.required_path),))

    assert profile.required_decision_count == 3
    assert profile.unique_switch_count == 3
    assert profile.ordered_dependency_count == 0
    assert profile.independent_decision_ratio == 1.0


def test_revisit_state_reversal_is_a_dependency_and_attaches_runtime_metrics():
    recipe = _recipe(
        ("start", "switch", "package", "destination"),
        (("start", "switch"), ("switch", "package"), ("switch", "destination"), ("package", "switch")),
        ("start", "switch", "package", "switch", "destination"),
    )
    runtime = RuntimeSolutionSearchResult(
        True,
        actions=(RuntimeSolutionAction(1.0, "switch"), RuntimeSolutionAction(3.5, "switch")),
        diagnostics=(
            RuntimeDecisionTimingDiagnostic("switch", 0, 1, 0.5, 1.5),
            RuntimeDecisionTimingDiagnostic("switch", 1, 2, 2.0, 4.0),
        ),
    )

    profile = DecisionProfileService().analyze(recipe, (_metadata(recipe.required_path),), runtime)

    assert profile.route_revisit_count == 1
    assert profile.repeated_switch_decision_count == 1
    assert profile.switch_state_change_on_revisit_count == 1
    assert profile.ordered_dependency_count >= 1
    assert profile.minimum_window_seconds == 1.0
    assert profile.average_window_seconds == 1.5
    assert profile.minimum_decision_spacing_seconds == 2.5
    assert profile.multiple_taps_in_window_count == 1
    assert profile.front_loaded_legacy_solution_possible is False


def test_decorative_rejoining_branch_is_equivalent_no_op():
    recipe = _recipe(
        ("start", "switch", "left", "right", "rejoin", "package", "destination"),
        (
            ("start", "switch"), ("switch", "left"), ("switch", "right"),
            ("left", "rejoin"), ("right", "rejoin"), ("rejoin", "package"),
            ("package", "destination"),
        ),
        ("start", "switch", "left", "rejoin", "package", "destination"),
    )

    profile = DecisionProfileService().analyze(recipe, (_metadata(recipe.required_path),))

    assert profile.no_op_or_equivalent_choice_count == 1
    assert profile.equivalent_minimum_solution_count == 2
    assert profile.successful_alternate_route_count == 1


def test_failure_outcome_classifications_are_sorted_and_deterministic():
    recipe = _recipe(
        ("start", "switch", "dead", "destination", "package"),
        (("start", "switch"), ("switch", "dead"), ("switch", "destination"), ("switch", "package"),
         ("package", "destination")),
        ("start", "switch", "package", "destination"),
    )
    service = DecisionProfileService()

    first = service.analyze(recipe, (_metadata(recipe.required_path),))
    second = service.analyze(recipe, (_metadata(recipe.required_path),))

    assert first.failure_outcome_types == ("dead_end", "destination_before_package")
    assert first.failure_outcome_types == second.failure_outcome_types
    assert first.dead_end_choice_count == 1
    assert first.destination_before_package_choice_count == 1


def test_package_state_route_change_counts_opened_and_closed_roads():
    recipe = GraphRecipe(
        level_id="stateful_profile",
        difficulty="medium",
        nodes=tuple(
            GraphRecipeNode(node)
            for node in ("start", "gate", "outbound", "package", "destination")
        ),
        edges=(
            GraphRecipeEdge("start", "gate"),
            GraphRecipeEdge("gate", "outbound", "beforePackage"),
            GraphRecipeEdge("gate", "destination", "afterPackage"),
            GraphRecipeEdge("outbound", "package"),
            GraphRecipeEdge("package", "gate"),
        ),
        required_path=("start", "gate", "outbound", "package", "gate", "destination"),
        tap_node_ids=(),
    )

    profile = DecisionProfileService().analyze(recipe, (_metadata(recipe.required_path),))

    assert profile.package_phase_transition_count == 1
    assert profile.state_dependent_route_change_count == 1
    assert profile.roads_opened_after_package_count == 1
    assert profile.roads_closed_after_package_count == 1
    assert profile.impossible_availability_condition_count == 0
    assert profile.irrelevant_availability_condition_count == 0


def test_impossible_and_irrelevant_availability_conditions_are_detected():
    recipe = GraphRecipe(
        level_id="invalid_stateful_profile",
        difficulty="medium",
        nodes=tuple(
            GraphRecipeNode(node)
            for node in ("start", "pre", "package", "post", "dead", "destination")
        ),
        edges=(
            GraphRecipeEdge("start", "pre"),
            GraphRecipeEdge("pre", "package"),
            GraphRecipeEdge("pre", "dead", "afterPackage"),
            GraphRecipeEdge("package", "post"),
            GraphRecipeEdge("post", "destination", "afterPackage"),
        ),
        required_path=("start", "pre", "package", "post", "destination"),
        tap_node_ids=(),
    )

    profile = DecisionProfileService().analyze(recipe, (_metadata(recipe.required_path),))

    assert profile.impossible_availability_condition_count == 1
    assert profile.irrelevant_availability_condition_count == 1
    assert profile.state_dependent_route_change_count == 0
