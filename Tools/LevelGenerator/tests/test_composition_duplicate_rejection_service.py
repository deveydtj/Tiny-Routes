from __future__ import annotations

from dataclasses import replace

from app.models import (
    CompositionDiversityConstraints,
    CompositionGraph,
    CompositionState,
    ObjectivePhaseBoundary,
)
from app.models.decision_dependency_graph import (
    DecisionDependency,
    DecisionDependencyGraph,
    DecisionDependencyKind,
    DecisionNode,
)
from app.models.graph_recipe import GraphRecipeEdge, GraphRecipeNode
from app.services import (
    CompositionDuplicateRejectionService,
    PuzzleBlueprintService,
)


def _complete_state(
    blueprint,
    *,
    prefix: str = "",
    motifs: tuple[str, ...] = ("branch", "rejoin"),
    extra_lane: bool = False,
) -> CompositionState:
    start = f"{prefix}start"
    objective_nodes = tuple(
        f"{prefix}objective_{index}" for index, _ in enumerate(blueprint.objectives)
    )
    lane = f"{prefix}lane"
    path = (start, *objective_nodes)
    if extra_lane:
        path = (start, lane, *objective_nodes)
    nodes = [GraphRecipeNode(start, "start")]
    if extra_lane:
        nodes.append(GraphRecipeNode(lane, "route"))
    nodes.extend(
        GraphRecipeNode(
            node_id,
            "destination" if index == len(objective_nodes) - 1 else "objective",
        )
        for index, node_id in enumerate(objective_nodes)
    )
    boundaries = tuple(
        ObjectivePhaseBoundary(
            objective.id,
            objective.sequence_index,
            path[index],
            objective_nodes[index],
        )
        for index, objective in enumerate(blueprint.objectives)
    )
    return CompositionState(
        blueprint_id=blueprint.id,
        unfulfilled_decision_ids=(),
        open_ports=(),
        objective_phase_boundaries=boundaries,
        current_graph=CompositionGraph(
            nodes=tuple(nodes),
            edges=tuple(
                GraphRecipeEdge(first, second)
                for first, second in zip(path, path[1:])
            ),
        ),
        placed_motif_ids=motifs,
    )


def test_renamed_compositions_are_rejected_as_behavior_isomorphic() -> None:
    blueprint = PuzzleBlueprintService().build_return_to_hub("medium", 301)
    first = _complete_state(blueprint)
    renamed = _complete_state(blueprint, prefix="renamed_")
    service = CompositionDuplicateRejectionService()

    first_assessment = service.assess("first", blueprint, first)
    duplicate = service.assess(
        "renamed",
        blueprint,
        renamed,
        (first_assessment.entry,),
    )

    assert first_assessment.is_accepted
    assert not duplicate.is_accepted
    assert duplicate.rejection_reasons == (
        "composition_duplicate_behavior_isomorphic:first",
    )
    assert duplicate.entry.behavior_signature == first_assessment.entry.behavior_signature


def test_motif_multiset_cap_ignores_placement_order() -> None:
    blueprint = PuzzleBlueprintService().build_return_to_hub("medium", 302)
    service = CompositionDuplicateRejectionService(
        CompositionDiversityConstraints(
            blueprint_archetype_cap=5,
            motif_multiset_cap=1,
            dependency_dag_cap=5,
        )
    )
    first = service.assess(
        "first",
        blueprint,
        _complete_state(blueprint, motifs=("branch", "rejoin")),
    )
    second = service.assess(
        "second",
        blueprint,
        _complete_state(
            blueprint,
            motifs=("rejoin", "branch"),
            extra_lane=True,
        ),
        (first.entry,),
    )

    assert first.entry.motif_multiset == (("branch", 1), ("rejoin", 1))
    assert second.rejection_reasons == ("composition_diversity_motif_multiset_cap",)


def test_archetype_and_dependency_caps_are_independent_hard_gates() -> None:
    source = PuzzleBlueprintService().build_return_to_hub("medium", 303)
    same_archetype = replace(source, id="same_archetype_blueprint")
    other_archetype = replace(source, id="other_archetype_blueprint", archetype="relay")

    archetype_service = CompositionDuplicateRejectionService(
        CompositionDiversityConstraints(1, 5, 5),
        behavior_signature_for=lambda state: state.blueprint_id,
    )
    first = archetype_service.assess("first", source, _complete_state(source))
    capped = archetype_service.assess(
        "second",
        same_archetype,
        _complete_state(same_archetype, motifs=("other",)),
        (first.entry,),
    )
    assert capped.rejection_reasons == (
        f"composition_diversity_blueprint_archetype_cap:{source.archetype}",
    )

    dag_service = CompositionDuplicateRejectionService(
        CompositionDiversityConstraints(5, 5, 1),
        behavior_signature_for=lambda state: state.blueprint_id,
    )
    first = dag_service.assess("first", source, _complete_state(source))
    capped = dag_service.assess(
        "second",
        other_archetype,
        _complete_state(other_archetype, motifs=("other",)),
        (first.entry,),
    )
    assert capped.rejection_reasons == (
        "composition_diversity_dependency_dag_cap",
    )


def test_dependency_signature_ignores_decision_and_role_renaming() -> None:
    source = PuzzleBlueprintService().build_return_to_hub("medium", 306)
    original = source.decision_graph
    renamed_ids = {
        decision.id: f"renamed_decision_{index}"
        for index, decision in enumerate(original.decisions)
    }
    renamed_objectives = {
        objective_id: f"renamed_objective_{index}"
        for index, (objective_id, _) in enumerate(original.objective_phase_indices)
    }
    role_ids: dict[str, str] = {}
    edge_role_ids: dict[str, str] = {}
    for decision in original.decisions:
        role_ids.setdefault(decision.switch_role, f"switch_role_{len(role_ids)}")
        for role in decision.outgoing_edge_roles:
            edge_role_ids.setdefault(role, f"edge_role_{len(edge_role_ids)}")
    renamed_graph = DecisionDependencyGraph(
        decisions=tuple(
            DecisionNode(
                renamed_ids[decision.id],
                decision.sequence_index,
                decision.phase_index,
                role_ids[decision.switch_role],
                tuple(edge_role_ids[role] for role in decision.outgoing_edge_roles),
                (
                    edge_role_ids[decision.required_outgoing_edge_role]
                    if decision.required_outgoing_edge_role is not None
                    else None
                ),
            )
            for decision in original.decisions
        ),
        dependencies=tuple(
            DecisionDependency(
                (
                    renamed_objectives[dependency.source_id]
                    if dependency.kind is DecisionDependencyKind.OBJECTIVE_STATE
                    else renamed_ids[dependency.source_id]
                ),
                renamed_ids[dependency.target_id],
                dependency.kind,
                (
                    edge_role_ids[dependency.required_source_outgoing_edge_role]
                    if dependency.required_source_outgoing_edge_role is not None
                    else None
                ),
            )
            for dependency in original.dependencies
        ),
        objective_phase_indices=tuple(
            (renamed_objectives[objective_id], phase_index)
            for objective_id, phase_index in original.objective_phase_indices
        ),
    )
    renamed = replace(source, decision_graph=renamed_graph)

    signature = CompositionDuplicateRejectionService.dependency_dag_signature_for
    assert signature(source) == signature(renamed)


def test_exact_behavior_signature_adapter_rejects_different_topologies_immediately() -> None:
    blueprint = PuzzleBlueprintService().build_return_to_hub("medium", 304)
    service = CompositionDuplicateRejectionService(
        behavior_signature_for=lambda _state: "exact-strategy-class-7"
    )
    first = service.assess("first", blueprint, _complete_state(blueprint))
    second = service.assess(
        "different_graph",
        blueprint,
        _complete_state(blueprint, extra_lane=True),
        (first.entry,),
    )

    assert second.rejection_reasons == (
        "composition_duplicate_behavior_isomorphic:first",
    )


def test_filter_pool_is_stable_and_rejected_entries_do_not_consume_caps() -> None:
    blueprint = PuzzleBlueprintService().build_return_to_hub("medium", 305)
    service = CompositionDuplicateRejectionService(
        CompositionDiversityConstraints(2, 2, 2)
    )
    result = service.filter_pool(
        (
            ("first", blueprint, _complete_state(blueprint)),
            ("duplicate", blueprint, _complete_state(blueprint, prefix="x_")),
            (
                "different",
                blueprint,
                _complete_state(blueprint, extra_lane=True, motifs=("lane",)),
            ),
        )
    )

    assert tuple(entry.candidate_id for entry in result.accepted_entries) == (
        "first",
        "different",
    )
    assert tuple(item.is_accepted for item in result.assessments) == (
        True,
        False,
        True,
    )
