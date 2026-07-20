from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from app.services import (
    SearchLimitRejectionService,
    StaticPolicySearchConfig,
    StaticPolicySolverService,
    StrategySearchConfig,
    StrategySearchService,
)


def _static_policy_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "static_policy_fixture",
            "name": "Static Policy Fixture",
            "startNodeID": "start",
            "packageNodeID": "pickup",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
            "parTaps": 1,
            "objectives": [
                {
                    "id": "pickup",
                    "nodeID": "pickup",
                    "kind": "pickup",
                    "sequenceIndex": 0,
                    "revealPolicy": "always",
                },
                {
                    "id": "destination",
                    "nodeID": "destination",
                    "kind": "destination",
                    "sequenceIndex": 1,
                    "revealPolicy": "always",
                },
            ],
            "graph": {
                "nodes": [
                    {
                        "id": "start",
                        "x": 0,
                        "y": 0,
                        "outgoingEdgeIDs": ["early_destination", "to_pickup"],
                    },
                    {
                        "id": "pickup",
                        "x": 1,
                        "y": 0,
                        "outgoingEdgeIDs": ["finish"],
                    },
                    {
                        "id": "destination",
                        "x": 2,
                        "y": 0,
                        "outgoingEdgeIDs": [],
                    },
                ],
                "edges": [
                    {
                        "id": "early_destination",
                        "fromNodeID": "start",
                        "toNodeID": "destination",
                    },
                    {"id": "to_pickup", "fromNodeID": "start", "toNodeID": "pickup"},
                    {"id": "finish", "fromNodeID": "pickup", "toNodeID": "destination"},
                ],
            },
        }
    )


def _adaptive_revisit_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "adaptive_revisit_fixture",
            "name": "Adaptive Revisit Fixture",
            "startNodeID": "start",
            "packageNodeID": "pickup",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
            "parTaps": 2,
            "objectives": [
                {
                    "id": "pickup",
                    "nodeID": "pickup",
                    "kind": "pickup",
                    "sequenceIndex": 0,
                    "revealPolicy": "always",
                },
                {
                    "id": "destination",
                    "nodeID": "destination",
                    "kind": "destination",
                    "sequenceIndex": 1,
                    "revealPolicy": "always",
                },
            ],
            "graph": {
                "nodes": [
                    {"id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": ["to_hub"]},
                    {
                        "id": "hub",
                        "x": 1,
                        "y": 0,
                        "outgoingEdgeIDs": ["to_pickup", "to_destination"],
                    },
                    {"id": "pickup", "x": 1, "y": 1, "outgoingEdgeIDs": ["return"]},
                    {
                        "id": "destination",
                        "x": 2,
                        "y": 0,
                        "outgoingEdgeIDs": [],
                    },
                ],
                "edges": [
                    {"id": "to_hub", "fromNodeID": "start", "toNodeID": "hub"},
                    {"id": "to_pickup", "fromNodeID": "hub", "toNodeID": "pickup"},
                    {
                        "id": "to_destination",
                        "fromNodeID": "hub",
                        "toNodeID": "destination",
                    },
                    {"id": "return", "fromNodeID": "pickup", "toNodeID": "hub"},
                ],
            },
        }
    )


def test_static_policy_solver_finds_a_permanent_assignment_witness() -> None:
    result = StaticPolicySolverService().solve(_static_policy_level())

    assert result.exhaustive
    assert result.static_policy_solvable
    assert not result.accepted_for_production
    assert result.rejection_reasons == ("static_policy_solution_exists",)
    assert result.tested_policy_count == result.total_policy_count == 2
    witness = result.successful_policies[0]
    assert tuple(
        (item.node_id, item.selected_edge_id) for item in witness.assignments
    ) == (("start", "to_pickup"),)
    assert witness.trace.succeeded
    assert witness.trace.final_state.completed_objective_ids == ("destination", "pickup")


def test_static_policy_solver_proves_an_adaptive_revisit_has_no_fixed_solution() -> None:
    result = StaticPolicySolverService().solve(_adaptive_revisit_level())

    assert result.exhaustive
    assert not result.static_policy_solvable
    assert result.accepted_for_production
    assert result.rejection_reasons == ()
    assert result.tested_policy_count == result.total_policy_count == 2


def test_assignment_budget_cannot_pass_static_policy_rejection_unproven() -> None:
    result = StaticPolicySolverService().solve(
        _static_policy_level(),
        config=StaticPolicySearchConfig(maximum_policy_assignments=1),
    )

    assert not result.exhaustive
    assert not result.proof_complete
    assert not result.accepted_for_production
    assert result.rejection_reasons == (
        "static_policy_search_incomplete",
        "static_policy_limit:static_policy_assignment_limit_reached",
    )


def test_search_limit_gate_rejects_exact_or_static_policy_uncertainty() -> None:
    level = _adaptive_revisit_level()
    limited_strategy = StrategySearchService().search(
        level,
        config=StrategySearchConfig(maximum_explored_states=1),
    )
    complete_static = StaticPolicySolverService().solve(level)

    strategy_gate = SearchLimitRejectionService().assess(
        limited_strategy,
        complete_static,
    )

    assert not strategy_gate.accepted
    assert "strategy_proof_search_incomplete" in strategy_gate.rejection_reasons
    assert "strategy_proof_limit:strategy_state_limit_reached" in (
        strategy_gate.rejection_reasons
    )

    complete_strategy = StrategySearchService().search(_static_policy_level())
    limited_static = StaticPolicySolverService().solve(
        _static_policy_level(),
        config=StaticPolicySearchConfig(maximum_policy_assignments=1),
    )
    static_gate = SearchLimitRejectionService().assess(
        complete_strategy,
        limited_static,
    )

    assert not static_gate.accepted
    assert static_gate.rejection_reasons == (
        "static_policy_proof_limit:static_policy_assignment_limit_reached",
        "static_policy_proof_search_incomplete",
    )


def test_found_static_policy_witness_is_conclusive_despite_later_budget_limit() -> None:
    level = _static_policy_level()
    payload = level.to_dict()
    payload["graph"]["nodes"][0]["outgoingEdgeIDs"] = [
        "to_pickup",
        "early_destination",
    ]
    reordered = LevelDocument.from_dict(payload)
    result = StaticPolicySolverService().solve(
        reordered,
        config=StaticPolicySearchConfig(maximum_policy_assignments=1),
    )

    assert result.static_policy_solvable
    assert result.proof_complete
    assert result.rejection_reasons == ("static_policy_solution_exists",)
    gate = SearchLimitRejectionService().assess(
        StrategySearchService().search(reordered),
        result,
    )
    assert gate.accepted
