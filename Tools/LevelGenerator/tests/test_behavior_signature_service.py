from __future__ import annotations

from dataclasses import replace

from app.random_source import RandomSource
from app.recipes import RecipeFamilyRegistry
from app.services.behavior_signature_service import BehaviorSignatureService
from app.services.difficulty_service import DifficultyService


def _recipe(family_name: str, variant_index: int = 0):
    registry = RecipeFamilyRegistry()
    family = registry.get_family(family_name)
    variant = family.variants[variant_index]
    preset = DifficultyService().get_preset(variant.difficulty_names[0])
    return family.generate_recipe(
        "level_behavior_isomorphism",
        preset,
        RandomSource(4810 + variant_index),
        variant,
    )


def test_known_builder_aliases_have_the_same_behavior_signature() -> None:
    service = BehaviorSignatureService()

    assert service.are_isomorphic(
        _recipe("multi_four_way_route"),
        _recipe("four_way_package_gate"),
    )
    for alias in ("late_route_reversal", "return_loop_with_gate", "multi_switch_revisit"):
        assert service.are_isomorphic(
            _recipe(alias),
            _recipe("controlled_repeated_taps"),
        )


def test_signature_reports_outcomes_recovery_and_optimal_strategy() -> None:
    signature = BehaviorSignatureService().signature_for(_recipe("split_path_rejoin"))

    assert signature.strategy_classes
    assert signature.optimal_cost_vector is not None
    assert signature.optimal_strategy_classes
    assert signature.has_unique_optimal_strategy
    assert all(count > 0 for _, count in signature.failure_outcomes)
    assert signature.digest == BehaviorSignatureService().signature_for(
        _recipe("split_path_rejoin")
    ).digest


def test_metadata_does_not_create_new_behavior() -> None:
    service = BehaviorSignatureService()
    recipe = _recipe("controlled_repeated_taps")
    renamed_metadata = replace(
        recipe,
        level_id="other_level",
        family_name="marketing_name_only",
        variant_name="visually_mirrored",
        notes=("layout and notes differ",),
        mechanic_tags=("different", "labels"),
        primary_mechanic_tag="different",
        topology_class="different",
    )

    assert service.signature_for(recipe) == service.signature_for(renamed_metadata)


def test_runtime_edge_order_changes_behavior() -> None:
    service = BehaviorSignatureService()
    recipe = _recipe("single_switch_package_choice")
    choice_edges = [
        index
        for index, edge in enumerate(recipe.edges)
        if edge.from_node_id == "choice"
    ]
    assert len(choice_edges) == 2
    first, second = choice_edges
    edges = list(recipe.edges)
    edges[first], edges[second] = edges[second], edges[first]
    changed = replace(recipe, edges=tuple(edges))

    assert not service.are_isomorphic(recipe, changed)
