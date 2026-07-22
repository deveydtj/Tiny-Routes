from __future__ import annotations

import json

from tiny_routes_core.models import LevelDocument

from app.services import StaticPolicySolverService, StrategySearchService
from test_support.stateful_fixture import StatefulFixtureSpec, build_stateful_fixture


def _level() -> LevelDocument:
    return build_stateful_fixture(
        StatefulFixtureSpec(
            fixture_id="metamorphic_stateful_relay",
            objective_count=3,
            hub_count=1,
            include_alternate_route=True,
            include_one_use_ring=True,
            seed=1,
        )
    )


def _analysis_fingerprint(level: LevelDocument) -> tuple[object, ...]:
    search = StrategySearchService().search(level)
    static = StaticPolicySolverService().solve(level)
    trace = search.canonical_optimal_strategy
    assert trace is not None and search.optimal_cost is not None
    meaningful = tuple(action for action in trace.actions if action.meaningful_decision)
    return (
        search.exhaustive,
        search.optimal_cost,
        len(meaningful),
        tuple(action.tap_count for action in meaningful),
        tuple(len(action.completed_objective_ids) for action in trace.actions),
        tuple(
            (
                action.state_transition.objective_index_before,
                action.state_transition.objective_index_after,
                len(action.state_transition.opened_edge_ids),
                len(action.state_transition.closed_edge_ids),
                len(action.state_transition.consumed_edge_ids),
            )
            for action in trace.actions
            if action.state_transition is not None
        ),
        len(search.equal_cost_optimal_strategies),
        len(search.all_successful_strategies),
        len(search.failure_outcomes),
        static.static_policy_solvable,
        static.proof_complete,
        static.tested_policy_count,
        static.total_policy_count,
    )


def _rename_every_identifier(level: LevelDocument) -> LevelDocument:
    payload = level.to_dict()
    node_ids = [node["id"] for node in payload["graph"]["nodes"]]
    edge_ids = [edge["id"] for edge in payload["graph"]["edges"]]
    objective_ids = [objective["id"] for objective in payload["objectives"]]
    node_map = {value: f"renamed_node_{index}" for index, value in enumerate(node_ids)}
    edge_map = {value: f"renamed_edge_{index}" for index, value in enumerate(edge_ids)}
    objective_map = {
        value: f"renamed_objective_{index}"
        for index, value in enumerate(objective_ids)
    }

    payload["id"] = "renamed_level"
    for field_name in ("startNodeID", "packageNodeID", "destinationNodeID"):
        payload[field_name] = node_map[payload[field_name]]
    for node in payload["graph"]["nodes"]:
        node["id"] = node_map[node["id"]]
        node["outgoingEdgeIDs"] = [
            edge_map[edge_id] for edge_id in node["outgoingEdgeIDs"]
        ]
    for edge in payload["graph"]["edges"]:
        edge["id"] = edge_map[edge["id"]]
        edge["fromNodeID"] = node_map[edge["fromNodeID"]]
        edge["toNodeID"] = node_map[edge["toNodeID"]]
        rule = edge.get("availabilityRule", {})
        for field_name in (
            "requiredCompletedObjectiveIDs",
            "forbiddenCompletedObjectiveIDs",
        ):
            if field_name in rule:
                rule[field_name] = [
                    objective_map[value] for value in rule[field_name]
                ]
    for objective in payload["objectives"]:
        objective["id"] = objective_map[objective["id"]]
        objective["nodeID"] = node_map[objective["nodeID"]]
    return LevelDocument.from_dict(payload)


def _with_pass_through_node(level: LevelDocument) -> LevelDocument:
    payload = level.to_dict()
    nodes = {node["id"]: node for node in payload["graph"]["nodes"]}
    edge = next(
        edge for edge in payload["graph"]["edges"] if edge["id"] == "start_to_hub"
    )
    source = nodes[edge["fromNodeID"]]
    destination = nodes[edge["toNodeID"]]
    original_destination = edge["toNodeID"]
    edge["toNodeID"] = "metamorphic_pass_through"
    payload["graph"]["nodes"].append(
        {
            "id": "metamorphic_pass_through",
            "x": (source["x"] + destination["x"]) / 2,
            "y": (source["y"] + destination["y"]) / 2,
            "outgoingEdgeIDs": ["metamorphic_pass_through_edge"],
        }
    )
    payload["graph"]["edges"].append(
        {
            "id": "metamorphic_pass_through_edge",
            "fromNodeID": "metamorphic_pass_through",
            "toNodeID": original_destination,
        }
    )
    return LevelDocument.from_dict(payload)


def _reverse_mapping_order(value):
    if isinstance(value, dict):
        return {
            key: _reverse_mapping_order(item)
            for key, item in reversed(tuple(value.items()))
        }
    if isinstance(value, list):
        return [_reverse_mapping_order(item) for item in value]
    return value


def _locked_shortcut_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "locked_shortcut_metamorphic",
            "name": "Locked Shortcut Metamorphic",
            "startNodeID": "start",
            "packageNodeID": "destination",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
            "parTaps": 0,
            "objectives": [
                {
                    "id": "destination_objective",
                    "nodeID": "destination",
                    "kind": "destination",
                    "sequenceIndex": 0,
                    "revealPolicy": "always",
                }
            ],
            "graph": {
                "nodes": [
                    {
                        "id": "start",
                        "x": 0,
                        "y": 0,
                        "outgoingEdgeIDs": ["ordinary", "locked_shortcut"],
                    },
                    {
                        "id": "destination",
                        "x": 4,
                        "y": 0,
                        "outgoingEdgeIDs": [],
                    },
                ],
                "edges": [
                    {
                        "id": "ordinary",
                        "fromNodeID": "start",
                        "toNodeID": "destination",
                    },
                    {
                        "id": "locked_shortcut",
                        "fromNodeID": "start",
                        "toNodeID": "destination",
                        "availabilityRule": {"minimumObjectiveIndex": 1},
                    },
                ],
            },
        }
    )


def test_renaming_all_authored_ids_does_not_change_strategy_analysis() -> None:
    level = _level()
    renamed = _rename_every_identifier(level)

    assert _analysis_fingerprint(renamed) == _analysis_fingerprint(level)


def test_mirroring_coordinates_does_not_change_strategy_analysis() -> None:
    level = _level()
    mirrored = level.clone()
    for node in mirrored.graph.nodes:
        node.x = -node.x

    assert _analysis_fingerprint(mirrored) == _analysis_fingerprint(level)


def test_adding_pass_through_node_does_not_create_a_decision() -> None:
    level = _level()
    expanded = _with_pass_through_node(level)
    original_search = StrategySearchService().search(level)
    expanded_search = StrategySearchService().search(expanded)
    original_trace = original_search.canonical_optimal_strategy
    expanded_trace = expanded_search.canonical_optimal_strategy
    assert original_trace is not None and expanded_trace is not None

    original_decisions = tuple(
        action for action in original_trace.actions if action.meaningful_decision
    )
    expanded_decisions = tuple(
        action for action in expanded_trace.actions if action.meaningful_decision
    )
    assert len(expanded_decisions) == len(original_decisions)
    assert expanded_search.optimal_cost == original_search.optimal_cost
    assert StaticPolicySolverService().solve(expanded).static_policy_solvable is False


def test_reordering_unrelated_json_fields_does_not_change_output() -> None:
    level = _level()
    reordered_payload = _reverse_mapping_order(level.to_dict())
    reordered = LevelDocument.from_dict(
        json.loads(json.dumps(reordered_payload, separators=(",", ":")))
    )

    assert reordered.to_dict() == level.to_dict()
    assert _analysis_fingerprint(reordered) == _analysis_fingerprint(level)


def test_making_locked_road_always_available_changes_static_policy_proof() -> None:
    locked = _locked_shortcut_level()
    locked_result = StaticPolicySolverService().solve(locked)
    unlocked_payload = locked.to_dict()
    shortcut = next(
        edge
        for edge in unlocked_payload["graph"]["edges"]
        if edge["id"] == "locked_shortcut"
    )
    shortcut.pop("availabilityRule")
    unlocked_result = StaticPolicySolverService().solve(
        LevelDocument.from_dict(unlocked_payload)
    )

    assert locked_result.exhaustive and unlocked_result.exhaustive
    assert len(locked_result.successful_policies) == 1
    assert len(unlocked_result.successful_policies) == 2
    assert locked_result != unlocked_result
