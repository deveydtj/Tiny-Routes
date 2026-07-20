from __future__ import annotations

from app.models import (
    AssignedStateEffect,
    CompositionGraph,
    CompositionState,
    CompositionTransformation,
    CompositionTransformationKind,
    CompositionTransformationProof,
    LayoutFootprintEstimate,
    MotifEdgeStateChangeKind,
    ObjectivePhaseBoundary,
)
from app.models.graph_recipe import GraphRecipeEdge, GraphRecipeNode
from app.services import CompositionTransformationService


def _phase_state() -> CompositionState:
    return CompositionState(
        blueprint_id="blueprint",
        unfulfilled_decision_ids=(),
        open_ports=(),
        objective_phase_boundaries=(),
        current_graph=CompositionGraph(
            nodes=(
                GraphRecipeNode("hub", "switch"),
                GraphRecipeNode("before_lane"),
                GraphRecipeNode("after_lane"),
                GraphRecipeNode("destination", "destination"),
            ),
            edges=(
                GraphRecipeEdge("hub", "before_lane", "beforePackage"),
                GraphRecipeEdge("hub", "after_lane", "afterPackage"),
                GraphRecipeEdge("before_lane", "destination"),
                GraphRecipeEdge("after_lane", "destination"),
                GraphRecipeEdge("before_lane", "hub"),
                GraphRecipeEdge("after_lane", "hub"),
            ),
        ),
        estimated_layout_footprint=LayoutFootprintEstimate(4, 2),
    )


def _accepting_service(calls: list[str]) -> CompositionTransformationService:
    def solve(state: CompositionState) -> CompositionTransformationProof:
        calls.append(state.signature)
        return CompositionTransformationProof(True, f"proof:{state.signature}")

    return CompositionTransformationService(solve)


def test_phase_exit_exchange_and_ring_reversal_each_require_new_solver_proof() -> None:
    calls: list[str] = []
    service = _accepting_service(calls)
    state = _phase_state()

    exchange = service.apply(
        state,
        CompositionTransformation(
            CompositionTransformationKind.EXCHANGE_PHASE_HUB_EXITS,
            edge_indices=(0, 1),
        ),
    )
    reversal = service.apply(
        state,
        CompositionTransformation(
            CompositionTransformationKind.REVERSE_RING_PHASE_ORDER,
            edge_indices=(0, 1),
        ),
    )

    assert exchange.is_accepted and reversal.is_accepted
    assert len(calls) == 2
    assert exchange.candidate_state_signature != state.signature
    assert reversal.candidate_state_signature != state.signature


def test_objective_can_move_to_a_different_compatible_branch() -> None:
    calls: list[str] = []
    state = _phase_state().evolve(
        objective_phase_boundaries=(
            ObjectivePhaseBoundary("pickup", 0, "before_lane", "before_lane"),
        )
    )

    result = _accepting_service(calls).apply(
        state,
        CompositionTransformation(
            CompositionTransformationKind.MOVE_OBJECTIVE_TO_BRANCH,
            node_ids=("after_lane", "destination"),
            objective_id="pickup",
        ),
    )

    assert result.transformed_state is not None
    boundary = result.transformed_state.objective_phase_boundaries[0]
    assert (boundary.entry_node_id, boundary.exit_node_id) == (
        "after_lane",
        "destination",
    )
    assert len(calls) == 1


def test_fatal_branch_becomes_recoverable_only_after_solver_accepts_it() -> None:
    calls: list[str] = []
    state = CompositionState(
        blueprint_id="blueprint",
        unfulfilled_decision_ids=(),
        open_ports=(),
        objective_phase_boundaries=(),
        current_graph=CompositionGraph(
            nodes=(
                GraphRecipeNode("hub", "switch"),
                GraphRecipeNode("failure", "failure_dead_end"),
                GraphRecipeNode("recovery", "recovery"),
            ),
            edges=(
                GraphRecipeEdge("hub", "failure"),
                GraphRecipeEdge("hub", "recovery"),
            ),
        ),
    )

    result = _accepting_service(calls).apply(
        state,
        CompositionTransformation(
            CompositionTransformationKind.CONVERT_FATAL_BRANCH_TO_RECOVERY,
            node_ids=("failure", "recovery"),
        ),
    )

    assert result.transformed_state is not None
    assert GraphRecipeEdge("failure", "recovery") in result.transformed_state.current_graph.edges
    assert result.transformed_state.partial_strategic_metrics.recovery_count == 1
    assert len(calls) == 1


def test_shortcut_trigger_and_branch_cost_choice_can_be_transformed() -> None:
    calls: list[str] = []
    state = _phase_state().evolve(
        assigned_state_effects=(
            AssignedStateEffect(
                "pickup_transition",
                "unlocked_shortcut",
                "hub",
                "after_lane",
                MotifEdgeStateChangeKind.OPEN,
            ),
        )
    )
    service = _accepting_service(calls)

    shortcut = service.apply(
        state,
        CompositionTransformation(
            CompositionTransformationKind.CHANGE_SHORTCUT_UNLOCK_OBJECTIVE,
            transition_id="pickup_transition",
            replacement_id="checkpoint_transition",
        ),
    )
    branch_cost = service.apply(
        _phase_state(),
        CompositionTransformation(
            CompositionTransformationKind.SWAP_BRANCH_COSTS,
            edge_indices=(0, 1),
        ),
    )

    assert shortcut.transformed_state is not None
    assert (
        shortcut.transformed_state.assigned_state_effects[0].transition_id
        == "checkpoint_transition"
    )
    assert branch_cost.transformed_state is not None
    assert branch_cost.transformed_state.current_graph.edges[0].to_node_id == "after_lane"
    assert len(calls) == 2


def test_readability_segment_can_be_inserted_and_removed_with_solver_rerun() -> None:
    calls: list[str] = []
    service = _accepting_service(calls)
    state = _phase_state()

    inserted = service.apply(
        state,
        CompositionTransformation(
            CompositionTransformationKind.INSERT_READABILITY_SEGMENT,
            edge_indices=(2,),
            replacement_id="spacing",
        ),
    )
    assert inserted.transformed_state is not None
    removed = service.apply(
        inserted.transformed_state,
        CompositionTransformation(
            CompositionTransformationKind.REMOVE_READABILITY_SEGMENT,
            node_ids=("spacing",),
        ),
    )

    assert removed.transformed_state is not None
    assert "spacing" not in removed.transformed_state.current_graph.node_ids
    assert len(calls) == 2


def test_solver_rejection_never_returns_a_transformed_state() -> None:
    calls: list[str] = []

    def reject(state: CompositionState) -> CompositionTransformationProof:
        calls.append(state.signature)
        return CompositionTransformationProof(
            False,
            "proof:rejected",
            ("unique_optimal_strategy_not_preserved",),
        )

    result = CompositionTransformationService(reject).apply(
        _phase_state(),
        CompositionTransformation(
            CompositionTransformationKind.SWAP_BRANCH_COSTS,
            edge_indices=(0, 1),
        ),
    )

    assert result.status == "solver_rejected"
    assert result.transformed_state is None
    assert result.solver_proof.rejection_reasons == (
        "unique_optimal_strategy_not_preserved",
    )
    assert len(calls) == 1
