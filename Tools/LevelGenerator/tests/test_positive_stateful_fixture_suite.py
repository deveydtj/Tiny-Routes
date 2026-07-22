from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from tiny_routes_core.graph import GraphIndex
from tiny_routes_core.validation import validate_level_objectives

from app.models import (
    PuzzleAnalysis,
    PuzzleOutcomeCount,
)
from app.services import (
    DifficultyTargetResolver,
    LocalObviousnessAnalysisService,
    PolicyEvaluationConfig,
    PolicyEvaluationService,
    ProductionPuzzleGateService,
    PuzzleStateTransitionService,
    StaticPolicySolverService,
    StrategySearchService,
    UniqueOptimalProofService,
)
from test_support.stateful_fixture import StatefulFixtureSpec, build_stateful_fixture


_MANIFEST = (
    Path(__file__).parent / "fixtures" / "positive_stateful" / "manifest.json"
)


def _fixture_cases() -> tuple[dict, ...]:
    payload = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == 1
    fixtures = tuple(payload["fixtures"])
    assert len(fixtures) == 8
    assert len({fixture["id"] for fixture in fixtures}) == len(fixtures)
    return fixtures


def _level_for(fixture: dict):
    return build_stateful_fixture(
        StatefulFixtureSpec(
            fixture_id=fixture["id"],
            difficulty=fixture["difficulty"],
            objective_count=fixture["objectiveCount"],
            hub_count=fixture["hubCount"],
            include_alternate_route=True,
            include_one_use_ring=fixture.get("includeOneUseRing", False),
            seed=1,
        )
    )


def _accepted_analysis(level, search, static_result, difficulty: str) -> PuzzleAnalysis:
    target = DifficultyTargetResolver().resolve(difficulty)
    optimum = search.canonical_optimal_strategy
    assert optimum is not None and search.optimal_cost is not None
    meaningful = tuple(action for action in optimum.actions if action.meaningful_decision)
    hub_visits = Counter(
        node_id
        for action in optimum.actions
        for node_id in action.visited_node_ids
        if node_id.startswith("hub_")
    )
    policies = PolicyEvaluationService().evaluate(
        level,
        search_result=search,
        config=PolicyEvaluationConfig(random_run_count=2),
    )
    recoverable_count = target.recoverable_mistake_range[0]
    return PuzzleAnalysis(
        meaningful_decisions=max(len(meaningful), target.meaningful_decision_range[0]),
        planning_decisions=target.planning_decision_minimum,
        adaptive_decisions=target.adaptive_decision_minimum,
        dependency_depth=target.dependency_depth_range[0],
        independent_decision_ratio=0.25,
        static_policy_result=static_result,
        agent_results=policies.evaluations,
        objective_phases=len(level.effective_objectives),
        state_changes=max(
            target.state_change_range[0],
            sum(
                bool(action.state_transition and action.state_transition.changes_state)
                for action in optimum.actions
            ),
        ),
        revisits=sum(max(0, count - 1) for count in hub_visits.values()),
        successful_strategy_classes=len(search.all_successful_strategies),
        optimal_uniqueness=True,
        recovery_failure_distribution=(
            PuzzleOutcomeCount("immediateDeadEnd", 1),
            PuzzleOutcomeCount("recoverableDetour", max(1, recoverable_count)),
        ),
        equivalent_choices=0,
        no_op_choices=0,
        optimal_accepted_taps=search.optimal_cost.accepted_taps,
        optimal_route_distance=search.optimal_cost.route_distance,
        optimal_travel_time_seconds=search.optimal_cost.travel_time_seconds,
        visual_complexity=target.layout_complexity_target,
    )


@pytest.mark.parametrize("fixture", _fixture_cases(), ids=lambda item: item["id"])
def test_named_positive_stateful_fixture_has_proven_strategy_and_passes_hard_gates(
    fixture: dict,
) -> None:
    level = _level_for(fixture)
    assert not validate_level_objectives(level)
    GraphIndex.build(level.graph)

    search = StrategySearchService().search(level)
    proof = UniqueOptimalProofService().prove(level, search)
    static_result = StaticPolicySolverService().solve(level)

    assert search.exhaustive and search.succeeded
    assert proof.accepted and proof.is_unique
    assert static_result.accepted_for_production
    assert search.optimal_cost is not None
    assert search.optimal_cost.accepted_taps >= 2
    assert tuple(level.effective_objectives) == tuple(
        sorted(level.effective_objectives, key=lambda item: item.sequenceIndex)
    )

    analysis = _accepted_analysis(level, search, static_result, fixture["difficulty"])
    obviousness = LocalObviousnessAnalysisService().assess(level, search)
    assert analysis.agent_result_for("greedy_objective").success_rate == 0
    assert obviousness.accepted and obviousness.non_obvious_decision_count > 0

    gate = ProductionPuzzleGateService().assess(
        analysis,
        DifficultyTargetResolver().resolve(fixture["difficulty"]),
        unique_optimal_proof=proof,
        local_obviousness=obviousness,
        state_change_readable=True,
        runtime_solution_robust=True,
    )
    assert gate.accepted
    assert all(check.passed for check in gate.checks)


@pytest.mark.parametrize("fixture", _fixture_cases(), ids=lambda item: item["id"])
def test_named_positive_stateful_fixture_realizes_declared_behavior(fixture: dict) -> None:
    level = _level_for(fixture)
    search = StrategySearchService().search(level)
    trace = search.canonical_optimal_strategy
    assert trace is not None

    transitions = tuple(
        action.state_transition
        for action in trace.actions
        if action.state_transition is not None
    )
    opened = {edge_id for item in transitions for edge_id in item.opened_edge_ids}
    closed = {edge_id for item in transitions for edge_id in item.closed_edge_ids}
    visited = (level.startNodeID, *(node for action in trace.actions for node in action.visited_node_ids))
    hub_visits = Counter(node for node in visited if node.startswith("hub_"))
    decision_hubs = {
        action.node_id for action in trace.actions if action.meaningful_decision
    }

    assert trace.final_state.completed_objective_ids == tuple(
        objective.id for objective in level.effective_objectives
    )
    assert sum(max(0, count - 1) for count in hub_visits.values()) >= fixture.get(
        "minimumHubRevisits", 0
    )
    assert len(decision_hubs) >= fixture.get("minimumDecisionHubs", 1)
    if fixture.get("requiresOpenedAndClosedRoads"):
        assert opened and closed
    if fixture.get("requiresAlternateSuccess"):
        assert len(search.all_successful_strategies) >= 2
        assert len(search.equal_cost_optimal_strategies) == 1
    if fixture.get("requiresRecoverableRing"):
        ring_traces = tuple(
            candidate
            for candidate in search.all_successful_strategies
            if any("_ring" in action.selected_edge_id for action in candidate.actions)
        )
        assert ring_traces
        assert any(
            action.state_transition and action.state_transition.consumed_edge_ids
            for candidate in ring_traces
            for action in candidate.actions
        )


@pytest.mark.parametrize("fixture", _fixture_cases(), ids=lambda item: item["id"])
def test_named_positive_stateful_optimal_trace_replays_exactly(fixture: dict) -> None:
    level = _level_for(fixture)
    trace = StrategySearchService().search(level).canonical_optimal_strategy
    assert trace is not None
    transitions = PuzzleStateTransitionService()
    state = transitions.initial_state(level)

    for action in trace.actions:
        available = transitions.available_actions(level, state)
        decision = next(
            candidate
            for candidate in available
            if candidate.selected_edge_id == action.selected_edge_id
        )
        replayed = transitions.transition(level, state, decision)
        assert replayed.traversed_edge_ids == action.traversed_edge_ids
        assert replayed.completed_objective_ids == action.completed_objective_ids
        state = replayed.state

    assert state == trace.final_state
    assert state.terminal_outcome.value == "success"
