from __future__ import annotations

from dataclasses import replace

import pytest

from app.models import (
    AssignedStateEffect,
    CompositionGraph,
    CompositionState,
    MotifEdgeStateChangeKind,
    MotifPort,
    MotifPortType,
    OpenCompositionPort,
)
from app.models.graph_recipe import GraphRecipeEdge, GraphRecipeNode
from app.motifs import default_motif_registry
from app.services import PuzzleComposerService, PuzzleCompositionError


def _edge_state(*, availability: str = "always", usage_limit: int | None = None) -> CompositionState:
    return CompositionState(
        blueprint_id="blueprint",
        unfulfilled_decision_ids=("decision_a", "decision_b"),
        open_ports=(),
        objective_phase_boundaries=(),
        current_graph=CompositionGraph(
            nodes=(GraphRecipeNode("start", "start"), GraphRecipeNode("end", "destination")),
            edges=(GraphRecipeEdge("start", "end", availability, usage_limit),),
        ),
    )


def test_edge_insertion_rewires_selected_edge_and_qualifies_motif_ids() -> None:
    state = _edge_state(availability="beforePackage", usage_limit=1)
    motif = default_motif_registry().get("straight_segment").build()

    successor = PuzzleComposerService().insert_motif_into_edge(
        state,
        edge_index=0,
        motif=motif,
        instance_id="spacing_a",
        objective_phase_index=0,
        fulfilled_decision_ids=("decision_a",),
    )

    assert state.current_graph.edges == (
        GraphRecipeEdge("start", "end", "beforePackage", 1),
    )
    assert successor.current_graph.node_ids == (
        "start",
        "end",
        "spacing_a__entry",
        "spacing_a__exit",
    )
    assert successor.current_graph.edges == (
        GraphRecipeEdge("start", "spacing_a__entry", "beforePackage", 1),
        GraphRecipeEdge("spacing_a__entry", "spacing_a__exit"),
        GraphRecipeEdge("spacing_a__exit", "end"),
    )
    assert successor.open_ports == ()
    assert successor.unfulfilled_decision_ids == ("decision_b",)
    assert successor.placed_motif_ids == ("straight_segment",)
    assert successor.validate() == ()


def test_edge_insertion_keeps_unconsumed_nested_ports_open() -> None:
    state = _edge_state()
    motif = default_motif_registry().get("split_and_rejoin").build()

    successor = PuzzleComposerService().insert_motif_into_edge(
        state,
        edge=state.current_graph.edges[0],
        motif=motif,
        instance_id="split_a",
        objective_phase_index=1,
    )

    assert {port.port_type for port in successor.open_ports} == {
        MotifPortType.BRANCH_INSERTION_POINT,
        MotifPortType.REJOIN_INPUT,
    }
    assert all(port.instance_id == "split_a" for port in successor.open_ports)
    assert all(port.objective_phase_index == 1 for port in successor.open_ports)
    assert successor.rejoin_count == 1


def test_edge_insertion_retargets_effect_assigned_to_replaced_edge() -> None:
    state = replace(
        _edge_state(availability="afterPackage"),
        assigned_state_effects=(
            AssignedStateEffect(
                "transition",
                "shortcut",
                "start",
                "end",
                MotifEdgeStateChangeKind.OPEN,
            ),
        ),
    )
    motif = default_motif_registry().get("straight_segment").build()

    successor = PuzzleComposerService().insert_motif_into_edge(
        state,
        edge_index=0,
        motif=motif,
        instance_id="inserted",
        objective_phase_index=0,
    )

    assert successor.assigned_state_effects[0].from_node_id == "start"
    assert successor.assigned_state_effects[0].to_node_id == "inserted__entry"
    assert successor.validate() == ()


def _branch_state() -> tuple[CompositionState, OpenCompositionPort]:
    source = OpenCompositionPort(
        "root",
        MotifPort("branch", "hub", MotifPortType.BRANCH_INSERTION_POINT),
        0,
    )
    state = CompositionState(
        blueprint_id="blueprint",
        unfulfilled_decision_ids=("decision_a",),
        open_ports=(source,),
        objective_phase_boundaries=(),
        current_graph=CompositionGraph(
            nodes=(
                GraphRecipeNode("hub", "switch"),
                GraphRecipeNode("main"),
            ),
            edges=(GraphRecipeEdge("hub", "main"),),
        ),
    )
    return state, source


def test_branch_expansion_adds_real_alternate_and_exposes_nested_ports() -> None:
    state, source = _branch_state()
    motif = default_motif_registry().get("recoverable_detour").build()

    successor = PuzzleComposerService().expand_branch(
        state,
        source_port=source,
        motif=motif,
        instance_id="detour_a",
        fulfilled_decision_ids=("decision_a",),
    )

    assert state.switch_count == 0
    assert successor.switch_count == 2
    assert successor.current_graph.edges[0] == GraphRecipeEdge("hub", "main")
    assert successor.current_graph.edges[1] == GraphRecipeEdge(
        "hub", "detour_a__entry"
    )
    assert source.id not in {port.id for port in successor.open_ports}
    assert "detour_a:main_entry" not in {port.id for port in successor.open_ports}
    assert {port.port_type for port in successor.open_ports}.issuperset(
        {
            MotifPortType.MAIN_ROUTE_EXIT,
            MotifPortType.REJOIN_INPUT,
            MotifPortType.RECOVERY_EXIT,
        }
    )
    assert successor.unfulfilled_decision_ids == ()
    assert successor.partial_strategic_metrics.meaningful_decision_count == 1
    assert successor.partial_strategic_metrics.recovery_count == 1
    assert successor.validate() == ()


def test_branch_expansion_rejects_wrong_or_closed_source_before_graph_change() -> None:
    state, source = _branch_state()
    motif = default_motif_registry().get("straight_segment").build()
    wrong_type = replace(
        source,
        port=MotifPort("exit", "hub", MotifPortType.MAIN_ROUTE_EXIT),
    )
    wrong_state = replace(state, open_ports=(wrong_type,))

    with pytest.raises(PuzzleCompositionError, match="not_branch_expansion"):
        PuzzleComposerService().expand_branch(
            wrong_state,
            source_port=wrong_type,
            motif=motif,
            instance_id="segment",
        )
    with pytest.raises(PuzzleCompositionError, match="source_port_not_open"):
        PuzzleComposerService().expand_branch(
            state,
            source_port="missing:branch",
            motif=motif,
            instance_id="segment",
        )

    assert state.current_graph.edges == (GraphRecipeEdge("hub", "main"),)


def test_reusing_instance_id_is_rejected_deterministically() -> None:
    state = _edge_state()
    motif = default_motif_registry().get("straight_segment").build()
    first = PuzzleComposerService().insert_motif_into_edge(
        state,
        edge_index=0,
        motif=motif,
        instance_id="same",
        objective_phase_index=0,
    )

    with pytest.raises(PuzzleCompositionError, match="instance_node_collision"):
        PuzzleComposerService().insert_motif_into_edge(
            first,
            edge_index=0,
            motif=motif,
            instance_id="same",
            objective_phase_index=0,
        )
