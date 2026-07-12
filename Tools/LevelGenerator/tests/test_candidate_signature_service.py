from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from app.random_source import RandomSource
from app.recipes.recipe_family_registry import RecipeFamilyRegistry
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
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


def test_changing_node_positions_changes_layout_hash() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(10))
    changed = deepcopy(generated)
    changed.level_document.graph.nodes[0].x += 0.25
    service = CandidateSignatureService()

    assert service.signature_for(generated).layout_hash != service.signature_for(changed).layout_hash


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
