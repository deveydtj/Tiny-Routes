from __future__ import annotations

from dataclasses import replace

from app.models import (
    DecisionDependency,
    DecisionDependencyGraph,
    DecisionDependencyKind,
    DecisionNode,
    ObjectiveSpec,
    PuzzleBlueprint,
    StateTransitionSpec,
)
from app.services.difficulty_target_resolver import DifficultyTargetResolver


def _valid_blueprint() -> PuzzleBlueprint:
    target = DifficultyTargetResolver().resolve("easy")
    objectives = (
        ObjectiveSpec(
            id="pickup_a",
            kind="pickup",
            sequence_index=0,
            phase_entry_role="pickup_approach",
            phase_exit_role="pickup_departure",
        ),
        ObjectiveSpec(
            id="destination",
            kind="destination",
            sequence_index=1,
            phase_entry_role="destination_approach",
            phase_exit_role="level_complete",
        ),
    )
    decision_graph = DecisionDependencyGraph(
        decisions=(
            DecisionNode(
                id="hub_outbound",
                sequence_index=0,
                phase_index=0,
                switch_role="shared_hub",
                outgoing_edge_roles=("toward_pickup", "toward_destination"),
                required_outgoing_edge_role="toward_pickup",
            ),
            DecisionNode(
                id="hub_return",
                sequence_index=1,
                phase_index=1,
                switch_role="shared_hub",
                outgoing_edge_roles=("toward_pickup", "toward_destination"),
                required_outgoing_edge_role="toward_destination",
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
                required_source_outgoing_edge_role="toward_pickup",
            ),
        ),
        objective_phase_indices=(("pickup_a", 0), ("destination", 1)),
    )
    return PuzzleBlueprint(
        id="easy_return_to_hub",
        archetype="return_to_hub",
        experience_target=target,
        objectives=objectives,
        decision_graph=decision_graph,
        state_transitions=(
            StateTransitionSpec(
                id="pickup_opens_destination_route",
                from_phase_index=0,
                to_phase_index=1,
                trigger_objective_id="pickup_a",
                revealed_objective_ids=("destination",),
                opened_edge_roles=("toward_destination",),
            ),
        ),
        planning_decision_ids=("hub_outbound",),
        adaptive_decision_ids=("hub_return",),
        required_revisit_decision_ids=("hub_return",),
        successful_strategy_count_range=(1, 2),
        requires_unique_optimal_strategy=True,
        requires_static_policy_rejection=True,
        recoverable_mistake_target=1,
        fatal_mistake_cap=1,
        required_mechanic_categories=("hub_revisit",),
        forbidden_mechanic_combinations=(
            ("recoverable_detour", "unlock_shortcut"),
        ),
    )


def test_puzzle_blueprint_accepts_complete_graph_independent_intent() -> None:
    blueprint = _valid_blueprint()

    assert blueprint.objective_phases == blueprint.objectives
    assert blueprint.decision_ids == ("hub_outbound", "hub_return")
    assert blueprint.validate() == ()
    assert blueprint.is_valid is True


def test_puzzle_blueprint_canonicalizes_sequence_inputs() -> None:
    blueprint = _valid_blueprint()
    rebuilt = replace(
        blueprint,
        objectives=list(blueprint.objectives),
        planning_decision_ids=["hub_outbound"],
        forbidden_mechanic_combinations=[
            ["recoverable_detour", "unlock_shortcut"]
        ],
    )

    assert isinstance(rebuilt.objectives, tuple)
    assert rebuilt.planning_decision_ids == ("hub_outbound",)
    assert rebuilt.forbidden_mechanic_combinations == (
        ("recoverable_detour", "unlock_shortcut"),
    )
    assert rebuilt.validate() == ()


def test_puzzle_blueprint_reports_cross_reference_and_phase_issues() -> None:
    blueprint = _valid_blueprint()
    invalid_transition = StateTransitionSpec(
        id="unknown_trigger",
        from_phase_index=1,
        to_phase_index=2,
        trigger_decision_id="missing_decision",
        revealed_objective_ids=("missing_objective",),
        opened_edge_roles=("new_route",),
    )
    invalid = replace(
        blueprint,
        objectives=(blueprint.objectives[1], blueprint.objectives[0]),
        state_transitions=(invalid_transition,),
        adaptive_decision_ids=("missing_decision",),
        required_revisit_decision_ids=(),
    )

    issues = invalid.validate()
    assert "blueprint_objective_sequence_not_contiguous" in issues
    assert "blueprint_terminal_objective_not_final" in issues
    assert "blueprint_adaptive_decision_unknown:missing_decision" in issues
    assert "blueprint_required_revisit_count_below_target" not in issues
    assert "blueprint_revisit_not_declared:hub_return" in issues
    assert "blueprint_state_transition_phase_unknown:unknown_trigger" in issues
    assert (
        "blueprint_state_transition_decision_unknown:unknown_trigger:missing_decision"
        in issues
    )
    assert (
        "blueprint_state_transition_reference_unknown:unknown_trigger:missing_objective"
        in issues
    )


def test_puzzle_blueprint_enforces_production_strategy_and_target_constraints() -> None:
    invalid = replace(
        _valid_blueprint(),
        successful_strategy_count_range=(0, 3),
        requires_unique_optimal_strategy=False,
        requires_static_policy_rejection=False,
        recoverable_mistake_target=0,
        fatal_mistake_cap=2,
        required_mechanic_categories=("stateful_ring",),
        forbidden_mechanic_combinations=(("stateful_ring", "stateful_ring"),),
    )

    issues = invalid.validate()
    assert "blueprint_successful_strategy_range_invalid" in issues
    assert "blueprint_unique_optimal_strategy_not_required" in issues
    assert "blueprint_static_policy_rejection_not_required" in issues
    assert "blueprint_recoverable_mistake_target_below_target" in issues
    assert "blueprint_fatal_mistake_cap_above_target" in issues
    assert "blueprint_required_mechanic_not_allowed:stateful_ring" in issues
    assert "blueprint_forbidden_combination_duplicate_item:0" in issues
    assert "blueprint_forbidden_combination_required:0" in issues
