from __future__ import annotations

import json
from pathlib import Path

from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.models.recipe_topology_rules import RecipeTopologyRules
from app.recipes.recipe_family_registry import RecipeFamilyRegistry
from app.services.decision_profile_service import DecisionProfileService
from app.services.difficulty_service import DifficultyService
from app.services.topology_solver_service import TopologySolverService
from app.services.v2_production_path_baseline_service import (
    DEFAULT_V2_PRODUCTION_PATH_BASELINE_SUITES,
    V2ProductionPathBaselineService,
)


FIXTURES = Path(__file__).parent / "fixtures" / "v2_generator_baseline"


def test_baseline_suite_catalog_exercises_every_difficulty_through_v2() -> None:
    assert [suite.difficulty for suite in DEFAULT_V2_PRODUCTION_PATH_BASELINE_SUITES] == [
        "tutorial",
        "easy",
        "medium",
        "hard",
        "expert",
    ]
    assert all(suite.count > 0 for suite in DEFAULT_V2_PRODUCTION_PATH_BASELINE_SUITES)


def test_checked_in_baseline_covers_registry_and_production_path() -> None:
    payload = json.loads((FIXTURES / "baseline.json").read_text(encoding="utf-8"))
    expected_families = set(RecipeFamilyRegistry().valid_family_names()) - {"mixed"}

    assert payload["generatorArchitecture"] == "v2_legacy"
    assert payload["usesLevelGenerationService"] is True
    assert payload["usesBatchOrchestrationService"] is True
    assert payload["templateBypassUsed"] is False
    assert {suite["difficulty"] for suite in payload["suites"]} == set(
        DifficultyService().valid_names
    )
    assert {item["family"] for item in payload["recipeFamilySnapshots"]} == expected_families
    assert payload["antiTrivialityFixtures"] == {
        "oneTap": "one_tap_recipe.json",
        "staticPolicy": "static_policy_recipe.json",
    }


def test_one_tap_and_static_policy_fixtures_freeze_v2_limitations() -> None:
    one_tap, one_tap_expected = _analyze_fixture("one_tap_recipe.json")
    static_policy, static_expected = _analyze_fixture("static_policy_recipe.json")

    assert one_tap.required_decision_count == one_tap_expected["minimumRequiredDecisions"]
    assert one_tap.required_decision_count <= 1
    assert one_tap.front_loaded_legacy_solution_possible is one_tap_expected["frontLoadedStaticPolicy"]
    assert static_policy.required_decision_count == static_expected["minimumRequiredDecisions"]
    assert static_policy.ordered_dependency_count == static_expected["orderedDependencyCount"]
    assert static_policy.independent_decision_ratio == static_expected["independentDecisionRatio"]
    assert static_policy.front_loaded_legacy_solution_possible is static_expected["frontLoadedStaticPolicy"]


def test_recipe_snapshots_are_deterministic() -> None:
    service = V2ProductionPathBaselineService()

    first = service._recipe_family_snapshots()
    second = service._recipe_family_snapshots()

    assert first == second


def _analyze_fixture(name: str):
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    rules = RecipeTopologyRules(
        allows_cycles=False,
        allows_rejoin=False,
        allows_revisit=False,
        allows_return_path=False,
        allows_ring=False,
        allowed_cycle_count=0,
        requires_package_gate=False,
        requires_unique_solution=True,
        requires_swift_runtime_validation=False,
    )
    recipe = GraphRecipe(
        level_id=f"fixture_{payload['name']}",
        difficulty=payload["difficulty"],
        nodes=tuple(GraphRecipeNode(node_id, role) for node_id, role in payload["nodes"]),
        edges=tuple(GraphRecipeEdge(*edge) for edge in payload["edges"]),
        required_path=tuple(payload["requiredPath"]),
        tap_node_ids=(),
        family_name=payload["name"],
        variant_name="fixture",
        mechanic_tags=("static_policy",),
        primary_mechanic_tag="static_policy",
        topology_class="two_switch_order" if payload["name"] == "static_policy" else "single_branch",
        topology_rules=rules,
        mechanic_metadata={"topologyRules": rules.to_metadata()},
    )
    preset = DifficultyService().get_preset(payload["difficulty"])
    search = TopologySolverService().search(recipe, preset)

    assert search.succeeded, search.failure_reasons
    return DecisionProfileService().analyze(recipe, search.solutions), payload["expected"]
