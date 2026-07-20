from __future__ import annotations

from app.models import (
    CompositionGraph,
    CompositionSearchChoice,
    CompositionState,
    CompositionStrategicConstraints,
    LayoutFootprintEstimate,
    PartialStrategicMetrics,
)
from app.models.graph_recipe import GraphRecipeEdge, GraphRecipeNode
from app.services import (
    CompositionBacktrackingService,
    CompositionStrategicPruningService,
)


def _constraints() -> CompositionStrategicConstraints:
    return CompositionStrategicConstraints(
        blueprint_id="blueprint",
        objective_count_range=(0, 2),
        meaningful_decision_range=(2, 4),
        adaptive_decision_minimum=1,
        dependency_depth_range=(1, 3),
        revisit_range=(1, 2),
        recovery_range=(1, 2),
        switch_count_range=(1, 3),
        maximum_switch_degree=3,
        layout_width_range=(1, 8),
        layout_height_range=(1, 5),
        adaptive_decision_ids=("adaptive",),
        revisit_decision_ids=("revisit",),
    )


def _state(
    *,
    decisions: tuple[str, ...] = ("adaptive", "revisit"),
    metrics: PartialStrategicMetrics = PartialStrategicMetrics(),
    edges: tuple[GraphRecipeEdge, ...] = (
        GraphRecipeEdge("hub", "exit"),
        GraphRecipeEdge("hub", "alternate"),
    ),
    footprint: LayoutFootprintEstimate = LayoutFootprintEstimate(1, 1),
) -> CompositionState:
    node_ids = {node_id for edge in edges for node_id in (edge.from_node_id, edge.to_node_id)}
    return CompositionState(
        blueprint_id="blueprint",
        unfulfilled_decision_ids=decisions,
        open_ports=(),
        objective_phase_boundaries=(),
        current_graph=CompositionGraph(
            tuple(GraphRecipeNode(node_id) for node_id in sorted(node_ids)),
            edges,
        ),
        estimated_layout_footprint=footprint,
        partial_strategic_metrics=metrics,
    )


def test_partial_state_is_retained_when_remaining_work_can_reach_every_minimum() -> None:
    assessment = CompositionStrategicPruningService(_constraints()).assess(_state())

    assert assessment.is_feasible
    assert assessment.rejection_reasons == ()


def test_pruning_reports_every_unreachable_or_exceeded_constraint_stably() -> None:
    state = _state(
        decisions=(),
        metrics=PartialStrategicMetrics(
            meaningful_decision_count=5,
            adaptive_decision_count=0,
            dependency_depth=4,
            revisit_count=0,
            recovery_count=0,
        ),
        edges=(
            GraphRecipeEdge("hub", "a"),
            GraphRecipeEdge("hub", "b"),
            GraphRecipeEdge("hub", "c"),
            GraphRecipeEdge("hub", "d"),
        ),
        footprint=LayoutFootprintEstimate(9, 6),
    )

    assessment = CompositionStrategicPruningService(_constraints()).assess(state)

    assert assessment.should_prune
    assert assessment.rejection_reasons == tuple(sorted(assessment.rejection_reasons))
    assert "composition_prune_meaningful_decision_max_exceeded:5:4" in assessment.rejection_reasons
    assert (
        "composition_prune_adaptive_decision_minimum_unreachable:0:1"
        in assessment.rejection_reasons
    )
    assert "composition_prune_dependency_depth_max_exceeded:4:3" in assessment.rejection_reasons
    assert "composition_prune_revisit_minimum_unreachable:0:1" in assessment.rejection_reasons
    assert "composition_prune_recovery_minimum_unreachable:0:1" in assessment.rejection_reasons
    assert "composition_prune_switch_degree_max_exceeded:4:3" in assessment.rejection_reasons
    assert "composition_prune_layout_width_max_exceeded:9:8" in assessment.rejection_reasons
    assert "composition_prune_layout_height_max_exceeded:6:5" in assessment.rejection_reasons


def test_backtracking_prunes_impossible_successor_and_records_reason() -> None:
    initial = _state(decisions=("adaptive", "revisit"))
    service = CompositionStrategicPruningService(_constraints())

    def impossible(state: CompositionState) -> CompositionState:
        return state.evolve(unfulfilled_decision_ids=())

    def feasible(state: CompositionState) -> CompositionState:
        return state.evolve(
            unfulfilled_decision_ids=(),
            partial_strategic_metrics=PartialStrategicMetrics(2, 1, 1, 1, 1),
        )

    choices = (
        CompositionSearchChoice("impossible", impossible, motif_index=0),
        CompositionSearchChoice("feasible", feasible, motif_index=1),
    )
    result = CompositionBacktrackingService().search(
        initial,
        lambda _state: choices,
        composition_budget=4,
        prune=service.rejection_reasons,
    )

    assert result.status == "completed"
    assert result.attempted_branch_count == 2
    assert "composition_prune_adaptive_decision_minimum_unreachable:0:1" in result.failure_reasons
    assert [entry.outcome for entry in result.trace] == ["pruned", "accepted"]
