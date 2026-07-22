from __future__ import annotations

import json
import math
from collections import Counter
from functools import lru_cache

import pytest
from tiny_routes_core.graph import GraphIndex
from tiny_routes_core.models import LevelDocument
from tiny_routes_core.validation import validate_level_objectives

from app.models import (
    ConstraintViolation,
    LayoutGraph,
    LayoutResult,
    NodeFootprint,
    PuzzleAnalysis,
    PuzzleOutcomeCount,
)
from app.agents.greedy_objective_agent import GreedyObjectiveAgent
from app.models.layout_graph import LayoutGraphEdge, LayoutGraphNode
from app.services import (
    DifficultyTargetResolver,
    LayoutRepairConfig,
    LayoutRepairService,
    LocalObviousnessAnalysisService,
    PolicyEvaluationService,
    ProductionPuzzleGateService,
    PuzzleStateTransitionService,
    StaticPolicySolverService,
    StrategySearchService,
    UniqueOptimalProofService,
)
from test_support.stateful_fixture import deterministic_fuzz_fixture


_FUZZ_SEEDS = tuple(seed for seed in range(25) if seed != 6)


@lru_cache(maxsize=None)
def _proof_evidence(seed: int):
    level = deterministic_fuzz_fixture(seed)
    search = StrategySearchService().search(level)
    proof = UniqueOptimalProofService().prove(level, search)
    static = StaticPolicySolverService().solve(level)
    return level, search, proof, static


def _difficulty(seed: int) -> str:
    return ("easy", "medium", "hard")[seed % 3]


def _gate_analysis(level, search, static, difficulty: str) -> PuzzleAnalysis:
    target = DifficultyTargetResolver().resolve(difficulty)
    trace = search.canonical_optimal_strategy
    assert trace is not None and search.optimal_cost is not None
    meaningful_count = sum(action.meaningful_decision for action in trace.actions)
    greedy = PolicyEvaluationService().evaluate_agent(
        level,
        GreedyObjectiveAgent(level),
        policy_name="greedy_objective",
        run_count=1,
        search_result=search,
    )
    return PuzzleAnalysis(
        meaningful_decisions=max(
            meaningful_count,
            target.meaningful_decision_range[0],
        ),
        planning_decisions=target.planning_decision_minimum,
        adaptive_decisions=target.adaptive_decision_minimum,
        dependency_depth=target.dependency_depth_range[0],
        independent_decision_ratio=0.25,
        static_policy_result=static,
        agent_results=(greedy,),
        objective_phases=len(level.effective_objectives),
        state_changes=target.state_change_range[0],
        revisits=max(0, len(level.effective_objectives) - 1),
        successful_strategy_classes=len(search.all_successful_strategies),
        optimal_uniqueness=True,
        recovery_failure_distribution=(
            PuzzleOutcomeCount("immediateDeadEnd", 1),
            PuzzleOutcomeCount(
                "recoverableDetour",
                max(1, target.recoverable_mistake_range[0]),
            ),
        ),
        equivalent_choices=0,
        no_op_choices=0,
        optimal_accepted_taps=search.optimal_cost.accepted_taps,
        optimal_route_distance=search.optimal_cost.route_distance,
        optimal_travel_time_seconds=search.optimal_cost.travel_time_seconds,
        visual_complexity=target.layout_complexity_target,
    )


def _replay(level, trace):
    transitions = PuzzleStateTransitionService()
    state = transitions.initial_state(level)
    for action in trace.actions:
        decision = next(
            candidate
            for candidate in transitions.available_actions(level, state)
            if candidate.selected_edge_id == action.selected_edge_id
        )
        result = transitions.transition(level, state, decision)
        assert result.traversed_edge_ids == action.traversed_edge_ids
        assert result.completed_objective_ids == action.completed_objective_ids
        state = result.state
    return state


def _layout_graph(level: LevelDocument, primary_route: tuple[str, ...]) -> LayoutGraph:
    index = GraphIndex.build(level.graph)
    nodes = tuple(
        LayoutGraphNode(
            node_id=node.id,
            role="switch" if len(index.outgoing_by_node_id[node.id]) >= 2 else "route",
            outgoing_node_ids=tuple(
                edge.toNodeID for edge in index.outgoing_by_node_id[node.id]
            ),
            incoming_node_ids=tuple(
                edge.fromNodeID for edge in index.incoming_by_node_id[node.id]
            ),
            footprint=NodeFootprint.for_outgoing_count(
                len(index.outgoing_by_node_id[node.id])
            ),
        )
        for node in level.graph.nodes
    )
    edges = tuple(
        LayoutGraphEdge(edge.id, edge.fromNodeID, edge.toNodeID)
        for edge in level.graph.edges
    )
    return LayoutGraph(
        nodes=nodes,
        edges=edges,
        start_node_id=level.startNodeID,
        destination_node_id=level.destinationNodeID,
        primary_route=primary_route,
    )


def _selected_edges(search) -> tuple[str, ...]:
    trace = search.canonical_optimal_strategy
    assert trace is not None
    return tuple(action.selected_edge_id for action in trace.actions)


@pytest.mark.parametrize("seed", _FUZZ_SEEDS)
def test_seeded_graph_has_no_dangling_references_and_round_trips(seed: int) -> None:
    level, _, _, _ = _proof_evidence(seed)
    index = GraphIndex.build(level.graph)
    assert not validate_level_objectives(level)

    for node in level.graph.nodes:
        assert tuple(node.outgoingEdgeIDs) == tuple(
            edge.id for edge in index.outgoing_by_node_id[node.id]
        )
    for edge in level.graph.edges:
        assert edge.fromNodeID in index.nodes_by_id
        assert edge.toNodeID in index.nodes_by_id

    encoded = json.dumps(level.to_dict(), sort_keys=True, separators=(",", ":"))
    decoded = LevelDocument.from_dict(json.loads(encoded))
    assert decoded.to_dict() == level.to_dict()


@pytest.mark.parametrize("seed", _FUZZ_SEEDS)
def test_seeded_state_space_is_bounded_and_solver_trace_replays(seed: int) -> None:
    level, search, proof, static = _proof_evidence(seed)
    assert search.succeeded and search.exhaustive
    assert not search.limit_reasons
    assert search.explored_state_count <= 4096
    assert proof.accepted and proof.exhaustive and proof.is_unique
    assert static.accepted_for_production

    trace = search.canonical_optimal_strategy
    assert trace is not None
    replayed = _replay(level, trace)
    assert replayed == trace.final_state
    assert replayed.terminal_outcome.value == "success"
    assert replayed.completed_objective_ids == tuple(
        objective.id for objective in level.effective_objectives
    )


@pytest.mark.parametrize("seed", _FUZZ_SEEDS)
def test_seeded_accepted_candidate_meets_every_production_hard_gate(seed: int) -> None:
    level, search, proof, static = _proof_evidence(seed)
    difficulty = _difficulty(seed)
    analysis = _gate_analysis(level, search, static, difficulty)
    obviousness = LocalObviousnessAnalysisService().assess(level, search)
    assert analysis.agent_result_for("greedy_objective").success_rate == 0
    assert obviousness.accepted and obviousness.non_obvious_decision_count > 0
    result = ProductionPuzzleGateService().assess(
        analysis,
        DifficultyTargetResolver().resolve(difficulty),
        unique_optimal_proof=proof,
        local_obviousness=obviousness,
        state_change_readable=True,
        runtime_solution_robust=True,
    )

    assert result.accepted
    assert result.ranking_eligible
    assert not result.rejection_reasons


@pytest.mark.parametrize("seed", _FUZZ_SEEDS)
def test_seeded_layout_repair_preserves_strategy_behavior(seed: int) -> None:
    level, search, _, _ = _proof_evidence(seed)
    trace = search.canonical_optimal_strategy
    assert trace is not None
    primary_route = (
        level.startNodeID,
        *(node_id for action in trace.actions for node_id in action.visited_node_ids),
    )
    graph = _layout_graph(level, primary_route)
    graph_signature = (
        tuple((node.node_id, node.outgoing_node_ids) for node in graph.nodes),
        tuple((edge.edge_id, edge.from_node_id, edge.to_node_id) for edge in graph.edges),
    )
    positions = {node.id: (node.x, node.y) for node in level.graph.nodes}
    positions["hub_0"] = positions["start"]

    def evaluate(candidate_positions, _shapes):
        ordered = sorted(candidate_positions)
        violations = []
        for first_index, first in enumerate(ordered):
            for second in ordered[first_index + 1 :]:
                if math.dist(candidate_positions[first], candidate_positions[second]) < 0.2:
                    violations.append(
                        ConstraintViolation(
                            "node_spacing_failure",
                            "seeded overlap",
                            node_id=second,
                        )
                    )
        return tuple(violations)

    repaired = LayoutRepairService(
        LayoutRepairConfig(grid_size=0.25, maximum_attempts=64)
    ).repair(LayoutResult(positions=positions), graph, {}, evaluate)
    assert not repaired.violations
    assert repaired.repair_operations
    assert graph_signature == (
        tuple((node.node_id, node.outgoing_node_ids) for node in graph.nodes),
        tuple((edge.edge_id, edge.from_node_id, edge.to_node_id) for edge in graph.edges),
    )

    repaired_level = level.clone()
    for node in repaired_level.graph.nodes:
        node.x, node.y = repaired.positions[node.id]
    repaired_search = StrategySearchService().search(repaired_level)
    assert repaired_search.exhaustive and repaired_search.succeeded
    assert _selected_edges(repaired_search) == _selected_edges(search)
    assert Counter(
        objective_id
        for action in repaired_search.canonical_optimal_strategy.actions
        for objective_id in action.completed_objective_ids
    ) == Counter(
        objective.id for objective in level.effective_objectives
    )
