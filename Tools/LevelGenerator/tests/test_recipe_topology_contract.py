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


def test_known_return_loop_aliases_are_quarantined_from_all_production_selection() -> None:
    registry = RecipeFamilyRegistry()
    difficulty = DifficultyService()
    expected = {
        "return_loop_intro",
        "return_loop_with_gate",
        "multi_switch_revisit",
    }

    assert set(registry.quarantined_family_names()) == expected
    assert "return_loop_intro" not in {
        family.name for family in registry.supported_families(difficulty.get_preset("medium"))
    }
    hard_supported = {
        family.name for family in registry.supported_families(difficulty.get_preset("hard"))
    }
    assert {"return_loop_with_gate", "multi_switch_revisit"}.isdisjoint(hard_supported)

    for family_name in sorted(expected):
        preset = difficulty.get_preset(
            registry.get_family(family_name).variants[0].difficulty_names[0]
        )
        with pytest.raises(ValueError, match="quarantined from production selection"):
            registry.choose_family(family_name, preset, RandomSource(44))


def test_repeated_builder_aliases_remain_available_only_as_audit_fixtures() -> None:
    controlled = _recipe("controlled_repeated_taps")
    controlled_graph = (
        controlled.required_path,
        tuple((edge.from_node_id, edge.to_node_id) for edge in controlled.edges),
        controlled.tap_node_ids,
    )

    for family_name in ("return_loop_with_gate", "multi_switch_revisit"):
        alias = _recipe(family_name)
        alias_graph = (
            alias.required_path,
            tuple((edge.from_node_id, edge.to_node_id) for edge in alias.edges),
            alias.tap_node_ids,
        )
        assert alias_graph == controlled_graph
        assert registry_reason(family_name) == "behavior_isomorphic_alias:controlled_repeated_taps"


def registry_reason(family_name: str) -> str | None:
    return RecipeFamilyRegistry().quarantine_reason(family_name)
