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


def _rejoin_state() -> tuple[
    CompositionState,
    tuple[OpenCompositionPort, OpenCompositionPort],
    OpenCompositionPort,
]:
    left = OpenCompositionPort(
        "left",
        MotifPort("exit", "left_end", MotifPortType.REJOIN_INPUT),
        1,
    )
    right = OpenCompositionPort(
        "right",
        MotifPort("exit", "right_end", MotifPortType.RECOVERY_EXIT),
        1,
    )
    target = OpenCompositionPort(
        "merge",
        MotifPort("entry", "merge", MotifPortType.MAIN_ROUTE_ENTRY),
        1,
    )
    state = CompositionState(
        blueprint_id="blueprint",
        unfulfilled_decision_ids=("join_branches",),
        open_ports=(left, right, target),
        objective_phase_boundaries=(),
        current_graph=CompositionGraph(
            nodes=(
                GraphRecipeNode("left_end"),
                GraphRecipeNode("right_end", "recovery"),
                GraphRecipeNode("merge"),
                GraphRecipeNode("exit"),
            ),
            edges=(GraphRecipeEdge("merge", "exit"),),
        ),
    )
    return state, (left, right), target


def test_rejoin_atomically_connects_two_branches_and_consumes_ports() -> None:
    state, sources, target = _rejoin_state()

    successor = PuzzleComposerService().attach_rejoin(
        state,
        source_ports=sources,
        target_port=target,
        fulfilled_decision_ids=("join_branches",),
    )

    assert state.current_graph.edges == (GraphRecipeEdge("merge", "exit"),)
    assert successor.current_graph.edges[-2:] == (
        GraphRecipeEdge("left_end", "merge"),
        GraphRecipeEdge("right_end", "merge"),
    )
    assert successor.open_ports == ()
    assert successor.unfulfilled_decision_ids == ()
    assert successor.rejoin_count == 1
    assert successor.validate() == ()


def test_rejoin_requires_a_real_merge_and_rejects_duplicate_connectors() -> None:
    state, sources, target = _rejoin_state()
    service = PuzzleComposerService()

    with pytest.raises(PuzzleCompositionError, match="requires_two_branches"):
        service.connect_rejoin(
            state,
            source_port=sources[0],
            target_port=target,
        )

    existing = replace(
        state,
        current_graph=CompositionGraph(
            nodes=state.current_graph.nodes,
            edges=(
                *state.current_graph.edges,
                GraphRecipeEdge("left_end", "merge"),
            ),
        ),
    )
    with pytest.raises(PuzzleCompositionError, match="edge_exists"):
        service.connect_rejoin(
            existing,
            source_port=sources[0],
            target_port=target,
        )


def _return_state(*, source_phase: int = 2, target_phase: int = 0) -> tuple[
    CompositionState,
    OpenCompositionPort,
    OpenCompositionPort,
]:
    source = OpenCompositionPort(
        "later",
        MotifPort("return_out", "later_exit", MotifPortType.RETURN_PATH_OUTPUT),
        source_phase,
    )
    target = OpenCompositionPort(
        "earlier",
        MotifPort("return_in", "hub", MotifPortType.RETURN_PATH_INPUT),
        target_phase,
    )
    state = CompositionState(
        blueprint_id="blueprint",
        unfulfilled_decision_ids=("return_to_hub",),
        open_ports=(source, target),
        objective_phase_boundaries=(),
        current_graph=CompositionGraph(
            nodes=(
                GraphRecipeNode("hub", "switch"),
                GraphRecipeNode("objective", "package"),
                GraphRecipeNode("later_exit"),
            ),
            edges=(
                GraphRecipeEdge("hub", "objective"),
                GraphRecipeEdge("objective", "later_exit"),
            ),
        ),
    )
    return state, source, target


def test_cross_phase_return_closes_cycle_and_records_revisit() -> None:
    state, source, target = _return_state()

    successor = PuzzleComposerService().connect_cross_phase_return(
        state,
        source_port=source,
        target_port=target,
        fulfilled_decision_ids=("return_to_hub",),
        usage_limit=1,
    )

    assert state.current_graph.edges[-1] == GraphRecipeEdge(
        "objective", "later_exit"
    )
    assert successor.current_graph.edges[-1] == GraphRecipeEdge(
        "later_exit", "hub", "afterPackage", 1
    )
    assert successor.open_ports == ()
    assert successor.unfulfilled_decision_ids == ()
    assert successor.cycle_count == 1
    assert successor.rejoin_count == 0
    assert successor.partial_strategic_metrics.revisit_count == 1
    assert successor.validate() == ()


def test_cross_phase_return_rejects_wrong_phase_or_non_cycle() -> None:
    same_phase_state, source, target = _return_state(source_phase=1, target_phase=1)
    service = PuzzleComposerService()

    with pytest.raises(PuzzleCompositionError, match="return_path_not_earlier"):
        service.connect_return_path(
            same_phase_state,
            source_port=source,
            target_port=target,
        )

    state, source, target = _return_state()
    disconnected = replace(
        state,
        current_graph=CompositionGraph(
            nodes=state.current_graph.nodes,
            edges=(GraphRecipeEdge("hub", "objective"),),
        ),
    )
    with pytest.raises(PuzzleCompositionError, match="does_not_close_cycle"):
        service.connect_cross_phase_return(
            disconnected,
            source_port=source,
            target_port=target,
        )

    assert disconnected.current_graph.edges == (GraphRecipeEdge("hub", "objective"),)


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
