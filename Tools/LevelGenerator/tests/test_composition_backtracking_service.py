from __future__ import annotations

from app.models import (
    CompositionGraph,
    CompositionSearchChoice,
    CompositionState,
)
from app.models.graph_recipe import GraphRecipeEdge, GraphRecipeNode
from app.services import CompositionBacktrackingService, PuzzleCompositionError


def _state(
    blueprint_id: str = "blueprint",
    decisions: tuple[str, ...] = ("decision",),
) -> CompositionState:
    return CompositionState(
        blueprint_id=blueprint_id,
        unfulfilled_decision_ids=decisions,
        open_ports=(),
        objective_phase_boundaries=(),
        current_graph=CompositionGraph(
            nodes=(
                GraphRecipeNode("start", "start"),
                GraphRecipeNode("end", "destination"),
            ),
            edges=(GraphRecipeEdge("start", "end"),),
        ),
    )


def test_search_retries_motifs_in_stable_order_and_records_rejections() -> None:
    calls: list[str] = []

    def reject(state: CompositionState) -> CompositionState:
        calls.append("reject")
        raise PuzzleCompositionError("composition_motif_incompatible:first")

    def complete(state: CompositionState) -> CompositionState:
        calls.append("complete")
        return state.evolve(unfulfilled_decision_ids=())

    def unused(state: CompositionState) -> CompositionState:
        calls.append("unused")
        return state

    def expand(_state: CompositionState):
        # Deliberately scrambled: explicit indices define deterministic order.
        return (
            CompositionSearchChoice(
                "later_port",
                unused,
                motif_id="motif_a",
                port_id="port_b",
                port_index=1,
            ),
            CompositionSearchChoice(
                "second_motif",
                complete,
                motif_id="motif_b",
                port_id="port_a",
                motif_index=1,
            ),
            CompositionSearchChoice(
                "first_motif",
                reject,
                motif_id="motif_a",
                port_id="port_a",
            ),
        )

    result = CompositionBacktrackingService().search(
        _state(),
        expand,
        composition_budget=10,
    )

    assert result.is_successful
    assert result.solution_state is not None
    assert result.solution_state.unfulfilled_decision_ids == ()
    assert result.attempted_branch_count == 2
    assert calls == ["reject", "complete"]
    assert result.rejection_counts[0].to_dict() == {
        "reason": "composition_motif_incompatible:first",
        "count": 1,
    }


def test_search_backtracks_from_dead_end_before_trying_sibling_branch() -> None:
    calls: list[str] = []

    def first(state: CompositionState) -> CompositionState:
        calls.append("first")
        return state.evolve(unfulfilled_decision_ids=("dead_end",))

    def second(state: CompositionState) -> CompositionState:
        calls.append("second")
        return state.evolve(unfulfilled_decision_ids=())

    def expand(state: CompositionState):
        if state.unfulfilled_decision_ids == ("dead_end",):
            return ()
        return (
            CompositionSearchChoice("first", first, motif_index=0),
            CompositionSearchChoice("second", second, motif_index=1),
        )

    result = CompositionBacktrackingService().search(
        _state(),
        expand,
        composition_budget=5,
    )

    assert result.status == "completed"
    assert calls == ["first", "second"]
    assert "composition_search_dead_end" in result.failure_reasons
    assert [entry.outcome for entry in result.trace] == [
        "accepted",
        "dead_end",
        "accepted",
    ]


def test_search_tries_another_blueprint_realization_deterministically() -> None:
    first = _state("blueprint_a", ("blocked",))
    second = _state("blueprint_b", ())

    result = CompositionBacktrackingService().search(
        (second, first),
        lambda _state: (),
        composition_budget=2,
    )

    assert result.status == "completed"
    assert result.solution_state is second
    assert result.expanded_state_count == 1
    assert result.failure_reasons == ("composition_search_dead_end",)


def test_search_stops_at_declared_budget_with_reproducible_evidence() -> None:
    def reject(_state: CompositionState) -> CompositionState:
        raise PuzzleCompositionError("composition_candidate_rejected")

    choices = tuple(
        CompositionSearchChoice(f"choice_{index}", reject, motif_index=index)
        for index in range(3)
    )
    service = CompositionBacktrackingService()

    first = service.search(_state(), lambda _state: choices, composition_budget=1)
    second = service.search(
        _state(),
        lambda _state: reversed(choices),
        composition_budget=1,
    )

    assert first == second
    assert first.status == "budget_exhausted"
    assert first.attempted_branch_count == 1
    assert first.budget_exhausted
    assert first.failure_reasons == (
        "composition_candidate_rejected",
        "composition_search_budget_exhausted",
    )
