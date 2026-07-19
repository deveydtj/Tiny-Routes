"""Shared assertions for evidence-backed legacy recipe topology contracts."""

from __future__ import annotations

from app.models.graph_recipe import GraphRecipe
from app.models.recipe_topology_evidence import RecipeTopologyEvidence
from app.services.recipe_topology_contract_service import RecipeTopologyContractService


def assert_recipe_topology_contract(
    recipe: GraphRecipe,
    *,
    expected_status: str = "passed",
    expected_reasons: tuple[str, ...] = (),
    contract_service: RecipeTopologyContractService | None = None,
) -> RecipeTopologyEvidence:
    """Assert a stable audit result and return its graph-derived evidence."""

    analyzer = contract_service or RecipeTopologyContractService()
    evidence = analyzer.analyze(recipe)
    repeated = analyzer.analyze(recipe)

    assert evidence == repeated
    assert evidence.family_name == recipe.family_name
    assert evidence.variant_name == recipe.variant_name
    assert evidence.status == expected_status, evidence.to_dict()
    assert evidence.reasons == expected_reasons, evidence.to_dict()
    assert evidence.claimed_behaviors == tuple(dict.fromkeys(evidence.claimed_behaviors))
    assert evidence.detected_behaviors == tuple(dict.fromkeys(evidence.detected_behaviors))
    if expected_status == "passed":
        assert evidence.reasons == ()
    else:
        assert evidence.reasons
    return evidence
