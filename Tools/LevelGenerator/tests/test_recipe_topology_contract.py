from __future__ import annotations

import pytest

from app.random_source import RandomSource
from app.recipes import RecipeFamilyRegistry
from app.services.difficulty_service import DifficultyService
from app.services.recipe_topology_contract_service import RecipeTopologyContractService
from test_support.recipe_topology_contract import assert_recipe_topology_contract


def _recipe(family_name: str, variant_index: int = 0):
    registry = RecipeFamilyRegistry()
    family = registry.get_family(family_name)
    variant = family.variants[variant_index]
    preset = DifficultyService().get_preset(variant.difficulty_names[0])
    return family.generate_recipe(
        "level_topology_contract",
        preset,
        RandomSource(4310 + variant_index),
        variant,
    )


def test_recipe_topology_contract_helper_returns_stable_graph_evidence() -> None:
    evidence = assert_recipe_topology_contract(_recipe("controlled_repeated_taps"))

    assert {"cycle", "revisit", "unique_success"}.issubset(evidence.detected_behaviors)
    assert evidence.to_dict()["status"] == "passed"


def test_false_return_loop_claim_fails_for_both_variants_with_stable_reason() -> None:
    for variant_index in (0, 1):
        evidence = RecipeTopologyContractService().analyze(
            _recipe("return_loop_intro", variant_index)
        )

        assert evidence.status == "failed"
        assert "claimed_cycle_not_detected" in evidence.reasons
        assert "claimed_revisit_not_detected" in evidence.reasons
        assert "cycle" in evidence.claimed_behaviors
        assert "cycle" not in evidence.detected_behaviors


def test_every_registered_family_variant_emits_status_and_reasons_deterministically() -> None:
    registry = RecipeFamilyRegistry()
    service = RecipeTopologyContractService()
    expected_count = sum(
        len(registry.get_family(family_name).variants)
        for family_name in registry.valid_family_names()
        if family_name != "mixed"
    )

    first = service.audit_registry(registry)
    second = service.audit_registry(registry)

    assert first == second
    assert len(first) == expected_count
    assert len({(item.family_name, item.variant_name) for item in first}) == expected_count
    for item in first:
        assert item.status in {"passed", "failed"}
        assert bool(item.reasons) is (item.status == "failed")


def test_known_legacy_mismatches_are_quarantined_from_all_production_selection() -> None:
    registry = RecipeFamilyRegistry()
    difficulty = DifficultyService()
    expected_by_difficulty = {
        "medium": {
            "return_loop_intro",
        },
        "hard": {
            "branch_then_rejoin_with_wrong_order",
            "return_loop_with_gate",
            "ring_route_gate",
            "multi_switch_revisit",
        },
        "expert": {
            "late_route_reversal",
            "multi_four_way_route",
        },
    }
    expected = {
        family_name
        for family_names in expected_by_difficulty.values()
        for family_name in family_names
    }

    assert set(registry.quarantined_family_names()) == expected
    for difficulty_name, family_names in expected_by_difficulty.items():
        supported = {
            family.name
            for family in registry.supported_families(
                difficulty.get_preset(difficulty_name)
            )
        }
        assert family_names.isdisjoint(supported)

    for family_name in sorted(expected):
        preset = difficulty.get_preset(
            registry.get_family(family_name).variants[0].difficulty_names[0]
        )
        with pytest.raises(ValueError, match="quarantined from production selection"):
            registry.choose_family(family_name, preset, RandomSource(44))


def test_mislabeled_ring_and_rejoin_families_remain_auditable_fixtures() -> None:
    expected_reasons = {
        "ring_route_gate": {
            "claimed_cycle_not_detected",
            "claimed_ring_not_detected",
        },
        "branch_then_rejoin_with_wrong_order": {
            "claimed_rejoin_not_detected",
        },
    }

    for family_name, expected in expected_reasons.items():
        for variant_index in (0, 1):
            evidence = RecipeTopologyContractService().analyze(
                _recipe(family_name, variant_index)
            )

            assert evidence.status == "failed"
            assert expected.issubset(evidence.reasons)
            assert expected == {
                reason
                for reason in evidence.reasons
                if reason.startswith("claimed_")
            }
            assert registry_reason(family_name) in expected


def test_advanced_builder_aliases_remain_available_only_as_audit_fixtures() -> None:
    aliases = {
        "multi_four_way_route": (
            "four_way_package_gate",
            "behavior_isomorphic_alias:four_way_package_gate",
        ),
        "late_route_reversal": (
            "controlled_repeated_taps",
            "behavior_isomorphic_alias:controlled_repeated_taps",
        ),
    }

    for family_name, (canonical_name, expected_reason) in aliases.items():
        alias = _recipe(family_name)
        canonical = _recipe(canonical_name)
        assert _behavior_graph(alias) == _behavior_graph(canonical)
        assert registry_reason(family_name) == expected_reason


def _behavior_graph(recipe) -> tuple[object, ...]:
    return (
        recipe.required_path,
        tuple((edge.from_node_id, edge.to_node_id) for edge in recipe.edges),
        recipe.tap_node_ids,
    )


def test_repeated_builder_aliases_remain_available_only_as_audit_fixtures() -> None:
    controlled = _recipe("controlled_repeated_taps")
    controlled_graph = _behavior_graph(controlled)

    for family_name in ("return_loop_with_gate", "multi_switch_revisit"):
        alias = _recipe(family_name)
        assert _behavior_graph(alias) == controlled_graph
        assert registry_reason(family_name) == "behavior_isomorphic_alias:controlled_repeated_taps"


def registry_reason(family_name: str) -> str | None:
    return RecipeFamilyRegistry().quarantine_reason(family_name)
