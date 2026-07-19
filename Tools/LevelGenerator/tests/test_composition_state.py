from __future__ import annotations

from dataclasses import replace

import pytest

from app.models import (
    AssignedStateEffect,
    CompositionGraph,
    CompositionState,
    LayoutFootprintEstimate,
    MotifEdgeStateChangeKind,
    MotifPort,
    MotifPortType,
    ObjectivePhaseBoundary,
    OpenCompositionPort,
    PartialStrategicMetrics,
)
from app.models.graph_recipe import GraphRecipeEdge, GraphRecipeNode
from app.services import PuzzleBlueprintService


def test_initial_state_tracks_blueprint_work_and_phase_boundaries() -> None:
    blueprint = PuzzleBlueprintService().build_return_to_hub("medium", 17)

    state = CompositionState.initial(blueprint)

    assert state.blueprint_id == blueprint.id
    assert state.unfulfilled_decision_ids == blueprint.decision_ids
    assert tuple(
        (boundary.objective_id, boundary.phase_index)
        for boundary in state.objective_phase_boundaries
    ) == tuple(
        (objective.id, objective.sequence_index) for objective in blueprint.objectives
    )
    assert state.node_count == state.switch_count == 0
    assert state.validate() == ()


def test_state_tracks_graph_ports_effects_counts_footprint_and_metrics() -> None:
    blueprint = PuzzleBlueprintService().build_return_to_hub("medium", 3)
    graph = CompositionGraph(
        nodes=(
            GraphRecipeNode("hub", "switch"),
            GraphRecipeNode("pickup", "package"),
            GraphRecipeNode("exit"),
        ),
        edges=(
            GraphRecipeEdge("hub", "pickup", "beforePackage"),
            GraphRecipeEdge("hub", "exit", "afterPackage"),
            GraphRecipeEdge("pickup", "hub"),
        ),
    )
    port = OpenCompositionPort(
        "hub_motif",
        MotifPort("exit_port", "exit", MotifPortType.MAIN_ROUTE_EXIT),
        1,
    )
    effect = AssignedStateEffect(
        blueprint.state_transitions[0].id,
        blueprint.state_transitions[0].opened_edge_roles[0],
        "hub",
        "exit",
        MotifEdgeStateChangeKind.OPEN,
    )
    boundaries = tuple(
        replace(
            boundary,
            entry_node_id="hub",
            exit_node_id="pickup" if boundary.phase_index == 0 else "exit",
        )
        for boundary in CompositionState.initial(blueprint).objective_phase_boundaries
    )

    state = CompositionState(
        blueprint_id=blueprint.id,
        unfulfilled_decision_ids=(blueprint.decision_ids[-1],),
        open_ports=(port,),
        objective_phase_boundaries=boundaries,
        current_graph=graph,
        assigned_state_effects=(effect,),
        placed_motif_ids=("objective_state_revisited_hub",),
        cycle_count=1,
        rejoin_count=1,
        estimated_layout_footprint=LayoutFootprintEstimate(5, 4),
        partial_strategic_metrics=PartialStrategicMetrics(1, 1, 1, 1, 0),
    )

    assert state.node_count == 3
    assert state.switch_count == 1
    assert state.estimated_layout_footprint.area == 20
    assert state.validate() == ()
    assert state.signature == replace(state).signature


def test_evolve_is_immutable_and_rejects_dangling_open_ports() -> None:
    blueprint = PuzzleBlueprintService().build_unlock_shortcut("medium", 9)
    state = CompositionState.initial(blueprint)

    with pytest.raises(ValueError, match="composition_open_port_node_unknown"):
        state.evolve(
            open_ports=(
                OpenCompositionPort(
                    "missing_motif",
                    MotifPort("entry", "missing", MotifPortType.MAIN_ROUTE_ENTRY),
                    0,
                ),
            )
        )

    assert state.open_ports == ()


def test_validation_reports_noncontiguous_phases_and_unknown_effect_edge() -> None:
    state = CompositionState(
        blueprint_id="blueprint",
        unfulfilled_decision_ids=(),
        open_ports=(),
        objective_phase_boundaries=(ObjectivePhaseBoundary("destination", 1),),
        assigned_state_effects=(
            AssignedStateEffect(
                "transition",
                "shortcut",
                "a",
                "b",
                MotifEdgeStateChangeKind.OPEN,
            ),
        ),
    )

    assert state.validate() == (
        "composition_phase_boundaries_not_contiguous",
        "composition_state_effect_edge_unknown:transition:a:b",
    )
