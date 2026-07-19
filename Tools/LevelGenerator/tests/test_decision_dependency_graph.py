from __future__ import annotations

from app.models import (
    DecisionDependency,
    DecisionDependencyGraph,
    DecisionDependencyKind,
    DecisionNode,
)


def _decision(
    decision_id: str,
    sequence_index: int,
    phase_index: int,
    *,
    switch_role: str | None = None,
    required_role: str | None = None,
) -> DecisionNode:
    return DecisionNode(
        id=decision_id,
        sequence_index=sequence_index,
        phase_index=phase_index,
        switch_role=switch_role or f"switch_{decision_id}",
        outgoing_edge_roles=("outbound", "return"),
        required_outgoing_edge_role=required_role,
    )


def test_dependency_graph_calculates_depth_and_independent_decisions() -> None:
    graph = DecisionDependencyGraph(
        decisions=(
            _decision("choose_branch", 0, 0, required_role="outbound"),
            _decision("choose_checkpoint", 1, 0, required_role="return"),
            _decision("choose_destination", 2, 1, required_role="outbound"),
            _decision("independent_detour", 3, 1),
        ),
        dependencies=(
            DecisionDependency(
                source_id="choose_branch",
                target_id="choose_checkpoint",
                kind=DecisionDependencyKind.EARLIER_CHOICE,
                required_source_outgoing_edge_role="outbound",
            ),
            DecisionDependency(
                source_id="choose_checkpoint",
                target_id="choose_destination",
                kind=DecisionDependencyKind.EARLIER_CHOICE,
                required_source_outgoing_edge_role="return",
            ),
        ),
    )

    assert graph.dependency_depth == 3
    assert graph.independent_decision_ids == (
        "choose_branch",
        "independent_detour",
    )
    assert graph.is_realizable is True
    assert graph.validate() == ()


def test_dependency_graph_realizes_objective_state_and_changed_revisit_exit() -> None:
    graph = DecisionDependencyGraph(
        decisions=(
            _decision(
                "hub_outbound",
                0,
                0,
                switch_role="shared_hub",
                required_role="outbound",
            ),
            _decision(
                "hub_return",
                1,
                1,
                switch_role="shared_hub",
                required_role="return",
            ),
        ),
        dependencies=(
            DecisionDependency(
                source_id="pickup_a",
                target_id="hub_return",
                kind=DecisionDependencyKind.OBJECTIVE_STATE,
            ),
            DecisionDependency(
                source_id="hub_outbound",
                target_id="hub_return",
                kind=DecisionDependencyKind.REVISIT,
                required_source_outgoing_edge_role="outbound",
            ),
        ),
        objective_phase_indices=(("pickup_a", 0),),
    )

    assert graph.independent_decision_ids == ("hub_outbound",)
    assert graph.dependency_depth == 2
    assert graph.validate() == ()


def test_dependency_graph_rejects_unrealizable_dependencies_and_cycles() -> None:
    graph = DecisionDependencyGraph(
        decisions=(
            _decision("first", 0, 0, required_role="outbound"),
            _decision("second", 1, 0, required_role="return"),
        ),
        dependencies=(
            DecisionDependency(
                source_id="second",
                target_id="first",
                kind=DecisionDependencyKind.EARLIER_CHOICE,
                required_source_outgoing_edge_role="return",
            ),
            DecisionDependency(
                source_id="first",
                target_id="second",
                kind=DecisionDependencyKind.EARLIER_CHOICE,
                required_source_outgoing_edge_role="outbound",
            ),
            DecisionDependency(
                source_id="missing_objective",
                target_id="second",
                kind=DecisionDependencyKind.OBJECTIVE_STATE,
            ),
        ),
    )

    issues = graph.validate()
    assert "decision_dependency_not_earlier:second:first" in issues
    assert "decision_dependency_objective_unknown:missing_objective" in issues
    assert any(issue.startswith("decision_dependency_cycle:") for issue in issues)
    assert graph.is_realizable is False


def test_revisit_requires_a_later_phase_same_switch_and_changed_exit() -> None:
    graph = DecisionDependencyGraph(
        decisions=(
            _decision("first", 0, 0, required_role="outbound"),
            _decision("revisit", 1, 0, required_role="outbound"),
        ),
        dependencies=(
            DecisionDependency(
                source_id="first",
                target_id="revisit",
                kind=DecisionDependencyKind.REVISIT,
                required_source_outgoing_edge_role="outbound",
            ),
        ),
    )

    issues = graph.validate()
    assert "decision_revisit_phase_not_later:first:revisit" in issues
    assert "decision_revisit_switch_mismatch:first:revisit" in issues
    assert "decision_revisit_role_unchanged:first:revisit" in issues


def test_dependency_kind_string_and_sequence_inputs_are_canonicalized() -> None:
    graph = DecisionDependencyGraph(
        decisions=[
            DecisionNode(
                id="first",
                sequence_index=0,
                phase_index=0,
                switch_role="first_switch",
                outgoing_edge_roles=["left", "right"],
                required_outgoing_edge_role="left",
            ),
            DecisionNode(
                id="second",
                sequence_index=1,
                phase_index=0,
                switch_role="second_switch",
                outgoing_edge_roles=["left", "right"],
            ),
        ],
        dependencies=[
            DecisionDependency(
                source_id="first",
                target_id="second",
                kind="earlierChoice",
                required_source_outgoing_edge_role="left",
            )
        ],
    )

    assert isinstance(graph.decisions, tuple)
    assert graph.decisions[0].outgoing_edge_roles == ("left", "right")
    assert graph.dependencies[0].kind is DecisionDependencyKind.EARLIER_CHOICE
    assert graph.validate() == ()
