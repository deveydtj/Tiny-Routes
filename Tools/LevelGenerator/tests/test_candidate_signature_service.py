from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

from app.random_source import RandomSource
from app.recipes.recipe_family_registry import RecipeFamilyRegistry
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.puzzle_blueprint_service import PuzzleBlueprintService
from app.services.recipe_to_level_builder_service import RecipeToLevelBuilderService
from app.templates.four_way_intersection_template import FourWayIntersectionTemplate
from app.templates.package_gate_template import PackageGateTemplate
from app.templates.single_switch_template import SingleSwitchTemplate


def test_same_generated_level_gets_same_signature() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(10))
    service = CandidateSignatureService()

    assert service.signature_for(generated) == service.signature_for(generated)


def test_changing_edge_changes_topology_hash() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(10))
    changed = deepcopy(generated)
    changed.level_document.graph.edges[0].toNodeID = "package"
    service = CandidateSignatureService()

    assert service.signature_for(generated).topology_hash != service.signature_for(changed).topology_hash


def test_changing_edge_availability_changes_topology_hash() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate(
        "level_012", 12, preset, RandomSource(10)
    )
    changed = deepcopy(generated)
    changed.level_document.graph.edges[0].availability = "afterPackage"
    service = CandidateSignatureService()

    assert (
        service.signature_for(generated).topology_hash
        != service.signature_for(changed).topology_hash
    )


def test_changing_node_positions_changes_layout_hash() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(10))
    changed = deepcopy(generated)
    changed.level_document.graph.nodes[0].x += 0.25
    service = CandidateSignatureService()

    assert service.signature_for(generated).layout_hash != service.signature_for(changed).layout_hash


def test_structural_behavior_signature_ignores_ids_and_layout() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate(
        "level_012", 12, preset, RandomSource(10)
    )
    renamed = deepcopy(generated)
    node_ids = {
        node.id: f"renamed_node_{index}"
        for index, node in enumerate(renamed.level_document.graph.nodes)
    }
    edge_ids = {
        edge.id: f"renamed_edge_{index}"
        for index, edge in enumerate(renamed.level_document.graph.edges)
    }
    for node in renamed.level_document.graph.nodes:
        node.id = node_ids[node.id]
        node.x += 50.0
        node.y -= 25.0
        node.outgoingEdgeIDs = [edge_ids[edge_id] for edge_id in node.outgoingEdgeIDs]
    for edge in renamed.level_document.graph.edges:
        edge.id = edge_ids[edge.id]
        edge.fromNodeID = node_ids[edge.fromNodeID]
        edge.toNodeID = node_ids[edge.toNodeID]
    renamed.level_document.startNodeID = node_ids[renamed.level_document.startNodeID]
    renamed.level_document.packageNodeID = node_ids[renamed.level_document.packageNodeID]
    renamed.level_document.destinationNodeID = node_ids[
        renamed.level_document.destinationNodeID
    ]
    for action in renamed.solution.actions:
        action.tapNodeID = node_ids[action.tapNodeID]
    service = CandidateSignatureService()

    original_signature = service.signature_for(generated)
    renamed_signature = service.signature_for(renamed)

    assert original_signature.topology_hash != renamed_signature.topology_hash
    assert original_signature.layout_hash != renamed_signature.layout_hash
    assert (
        original_signature.structural_behavior_signature
        == renamed_signature.structural_behavior_signature
    )


def test_changing_solution_tap_order_changes_solution_hash() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = PackageGateTemplate().generate("level_012", 12, preset, RandomSource(10))
    changed = deepcopy(generated)
    changed.solution.actions[0].tapNodeID = "finish_switch"
    changed.solution.actions[1].tapNodeID = "approach_switch"
    service = CandidateSignatureService()

    assert service.signature_for(generated).solution_hash != service.signature_for(changed).solution_hash


def test_four_way_signature_records_outgoing_and_revisit_shape() -> None:
    preset = DifficultyService().get_preset("expert")
    generated = FourWayIntersectionTemplate().generate("level_099", 99, preset, RandomSource(1))

    signature = CandidateSignatureService().signature_for(generated)

    assert signature.max_outgoing_edge_count == 4
    assert signature.has_four_way_switch is True
    assert signature.central_switch_revisit_count == 2


def test_signature_reports_recipe_topology_mechanics_path_and_orientation() -> None:
    preset = DifficultyService().get_preset("easy")
    family = RecipeFamilyRegistry().get_family("single_switch")
    recipe = family.generate_recipe("level_012", preset, RandomSource(10))
    generated = RecipeToLevelBuilderService().build_level(recipe, 12, seed=10, layout_variant_name="tall")

    signature = CandidateSignatureService().signature_for(generated)

    assert "single_switch" in signature.mechanic_tags
    assert signature.primary_mechanic_tag == "single_switch"
    assert signature.topology_class == "single_branch"
    assert signature.required_path_length == len(recipe.required_path) - 1
    assert signature.layout_orientation == "horizontal"
    assert signature.topology_diversity_score is None
    assert signature.diversity_score is None


def test_same_topology_with_different_layout_keeps_topology_class_auditable() -> None:
    preset = DifficultyService().get_preset("easy")
    family = RecipeFamilyRegistry().get_family("single_switch")
    recipe = family.generate_recipe("level_012", preset, RandomSource(10))
    builder = RecipeToLevelBuilderService()
    normal = builder.build_level(recipe, 12, seed=10, layout_variant_name="normal")
    tall = builder.build_level(recipe, 12, seed=10, layout_variant_name="tall")
    service = CandidateSignatureService()

    normal_signature = service.signature_for(normal)
    tall_signature = service.signature_for(tall)

    assert normal_signature.topology_class == tall_signature.topology_class == "single_branch"
    assert normal_signature.mechanic_tags == tall_signature.mechanic_tags
    assert "single_switch" in normal_signature.mechanic_tags
    assert normal_signature.topology_hash == tall_signature.topology_hash
    assert normal_signature.layout_hash != tall_signature.layout_hash


def test_mirrored_layout_retains_visual_shape_and_shared_canonical_silhouette() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(10))
    mirrored = deepcopy(generated)
    for node in mirrored.level_document.graph.nodes:
        node.x = 1.0 - node.x

    original_signature = CandidateSignatureService().signature_for(generated)
    mirrored_signature = CandidateSignatureService().signature_for(mirrored)

    assert original_signature.layout_silhouette != mirrored_signature.layout_silhouette
    assert original_signature.mirrored_layout_silhouette == mirrored_signature.mirrored_layout_silhouette
    assert original_signature.topology_hash == mirrored_signature.topology_hash


def test_same_topology_with_different_dependency_behavior_is_distinguishable() -> None:
    preset = DifficultyService().get_preset("easy")
    family = RecipeFamilyRegistry().get_family("single_switch")
    recipe = family.generate_recipe("level_012", preset, RandomSource(10))
    generated = RecipeToLevelBuilderService().build_level(recipe, 12, seed=10)
    changed = deepcopy(generated)
    changed.decision_profile = replace(
        generated.decision_profile,
        ordered_dependency_count=generated.decision_profile.ordered_dependency_count + 1,
    )
    service = CandidateSignatureService()

    original_signature = service.signature_for(generated)
    changed_signature = service.signature_for(changed)

    assert original_signature.topology_hash == changed_signature.topology_hash
    assert original_signature.decision_dependency_pattern != changed_signature.decision_dependency_pattern


def test_v3_signature_includes_complete_strategy_and_state_evidence() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate(
        "level_012", 12, preset, RandomSource(10)
    )
    blueprint = PuzzleBlueprintService().build_unlock_shortcut("easy", 10)
    transition = SimpleNamespace(
        objective_index_before=0,
        objective_index_after=1,
        completed_objective_ids=("pickup",),
        opened_edge_ids=("shortcut",),
        closed_edge_ids=("long_route",),
        consumed_edge_ids=(),
    )
    actions = (
        SimpleNamespace(
            node_id="hub",
            selected_edge_id="outbound",
            tap_count=1,
            traversed_edge_ids=("outbound",),
            visited_node_ids=("hub", "pickup"),
            completed_objective_ids=("pickup",),
            meaningful_decision=True,
            state_transition=transition,
        ),
        SimpleNamespace(
            node_id="hub",
            selected_edge_id="shortcut",
            tap_count=0,
            traversed_edge_ids=("shortcut",),
            visited_node_ids=("hub", "destination"),
            completed_objective_ids=("destination",),
            meaningful_decision=True,
            state_transition=SimpleNamespace(
                objective_index_before=1,
                objective_index_after=2,
                completed_objective_ids=("destination",),
                opened_edge_ids=(),
                closed_edge_ids=(),
                consumed_edge_ids=(),
            ),
        ),
    )
    trace = SimpleNamespace(
        actions=actions,
        outcome_code="success",
        cost=SimpleNamespace(
            accepted_taps=1,
            travel_time_seconds=8.0,
            route_distance=6.0,
        ),
    )
    strategy = SimpleNamespace(
        canonical_optimal_strategy=trace,
        all_successful_strategies=(trace,),
        failure_outcomes=(SimpleNamespace(outcome_code="state_trap"),),
    )
    static_policy = SimpleNamespace(
        exhaustive=True,
        tested_policy_count=6,
        total_policy_count=6,
        successful_policies=(),
        limit_reasons=(),
    )
    agent = SimpleNamespace(
        policy_name="greedy_objective",
        success_rate=0.25,
        average_taps=2.0,
        average_completion_time_seconds=12.0,
        average_route_distance=9.0,
        failure_types=(SimpleNamespace(code="dead_end", count=3),),
    )
    policy = SimpleNamespace(evaluations=(agent,))

    signature = CandidateSignatureService().signature_for(
        generated,
        blueprint=blueprint,
        strategy_result=strategy,
        static_policy_result=static_policy,
        policy_evaluation=policy,
    )

    assert signature.blueprint_archetype == "unlock_shortcut"
    assert signature.objective_count == 2
    assert signature.objective_kinds == ("pickup", "destination")
    assert signature.dependency_dag_signature
    assert signature.adaptive_decision_pattern
    assert signature.state_transition_pattern
    assert signature.static_policy_proof_signature
    assert signature.agent_performance_profile[0][:2] == (
        "greedy_objective",
        0.25,
    )
    assert signature.switch_degree_sequence
    assert signature.revisit_pattern == ((0, 1, 1),)
    assert signature.success_failure_distribution == (
        ("state_trap", 1),
        ("successful", 1),
    )
    assert signature.optimal_strategy_signature
    assert signature.layout_silhouette
    assert signature.road_state_visual_signature


def test_pipeline_signature_fails_closed_when_proof_evidence_is_missing() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate(
        "level_012", 12, preset, RandomSource(10)
    )
    result = SimpleNamespace(
        passed=True,
        candidate=generated,
        stage_results=(
            SimpleNamespace(stage="blueprint", blueprint=None),
            SimpleNamespace(
                stage="strategy",
                strategy_search=None,
                static_policy_search=None,
                policy_evaluation=None,
            ),
            SimpleNamespace(stage="quality", puzzle_analysis=None),
        ),
    )

    try:
        CandidateSignatureService().signature_for_pipeline_result(result)
    except ValueError as error:
        assert "incomplete signature evidence" in str(error)
    else:
        raise AssertionError("incomplete proof evidence must not enter a V3 pool")
