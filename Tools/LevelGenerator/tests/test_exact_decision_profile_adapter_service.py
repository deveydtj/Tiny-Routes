from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from app.models.runtime_solution_search import (
    RuntimeDecisionTimingDiagnostic,
    RuntimeSolutionAction,
    RuntimeSolutionSearchResult,
)
from app.services import (
    DecisionProfileService,
    StaticPolicySolverService,
    StrategySearchService,
)


def _adaptive_revisit_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "exact_profile_fixture",
            "name": "Exact Profile Fixture",
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
                    {"id": "destination", "x": 2, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "to_hub", "fromNodeID": "start", "toNodeID": "hub"},
                    {"id": "to_pickup", "fromNodeID": "hub", "toNodeID": "pickup"},
                    {"id": "to_destination", "fromNodeID": "hub", "toNodeID": "destination"},
                    {"id": "return", "fromNodeID": "pickup", "toNodeID": "hub"},
                ],
            },
        }
    )


def test_exact_profile_adapts_proof_evidence_without_legacy_route_enumeration(
    monkeypatch,
) -> None:
    level = _adaptive_revisit_level()
    strategy = StrategySearchService().search(level)
    static_policy = StaticPolicySolverService().solve(level)
    runtime = RuntimeSolutionSearchResult(
        True,
        actions=(
            RuntimeSolutionAction(1.0, "hub"),
            RuntimeSolutionAction(3.5, "hub"),
        ),
        diagnostics=(
            RuntimeDecisionTimingDiagnostic("hub", 0, 1, 0.5, 1.5),
            RuntimeDecisionTimingDiagnostic("hub", 1, 2, 2.0, 4.0),
        ),
    )
    service = DecisionProfileService()
    monkeypatch.setattr(
        service,
        "_enumerate_routes",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("legacy enumeration must not run")
        ),
    )

    profile = service.analyze_exact(level, strategy, static_policy, runtime)

    assert profile.required_decision_count == 2
    assert profile.unique_switch_count == 1
    assert profile.repeated_switch_decision_count == 1
    assert profile.switch_state_change_on_revisit_count == 1
    assert profile.ordered_dependency_count >= 1
    assert profile.package_phase_decisions_before == 1
    assert profile.package_phase_decisions_after == 1
    assert profile.package_phase_transition_count == 2
    assert profile.route_revisit_count == 1
    assert profile.destination_before_package_choice_count == 1
    assert profile.failure_outcome_types == ("destination_before_package",)
    assert profile.minimum_window_seconds == 1.0
    assert profile.average_window_seconds == 1.5
    assert profile.minimum_decision_spacing_seconds == 2.5
    assert profile.multiple_taps_in_window_count == 1
    assert not profile.front_loaded_legacy_solution_possible
    assert profile.no_op_or_equivalent_choice_count == 0


def test_exact_profile_uses_static_policy_proof_for_frontload_compatibility() -> None:
    level = _adaptive_revisit_level()
    payload = level.to_dict()
    payload["graph"]["edges"] = [
        edge for edge in payload["graph"]["edges"] if edge["id"] != "return"
    ]
    payload["graph"]["nodes"][2]["outgoingEdgeIDs"] = ["pickup_finish"]
    payload["graph"]["edges"].append(
        {
            "id": "pickup_finish",
            "fromNodeID": "pickup",
            "toNodeID": "destination",
        }
    )
    static_level = LevelDocument.from_dict(payload)

    profile = DecisionProfileService().analyze_exact(
        static_level,
        StrategySearchService().search(static_level),
        StaticPolicySolverService().solve(static_level),
    )

    assert profile.front_loaded_legacy_solution_possible
