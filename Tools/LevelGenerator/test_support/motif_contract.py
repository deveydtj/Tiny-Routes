"""Shared assertions for evidence-backed puzzle motif contracts."""

from __future__ import annotations

from app.models.motif_contract import (
    MotifDependencyEffect,
    MotifIncomingObjectiveState,
)
from app.models.motif_evidence import MotifContractEvidence
from app.models.motif_port import MotifPortType
from app.models.puzzle_motif import PuzzleMotif
from app.services.motif_contract_evidence_service import MotifContractEvidenceService


def assert_motif_contract(
    motif: PuzzleMotif,
    *,
    evidence_service: MotifContractEvidenceService | None = None,
) -> MotifContractEvidence:
    """Assert the complete typed contract and return its detected evidence."""

    validation_issues = motif.validate()
    assert validation_issues == (), validation_issues
    assert motif.ports, f"{motif.motif_id}: typed ports missing"
    assert motif.preconditions is not None, f"{motif.motif_id}: preconditions missing"
    assert motif.effects is not None, f"{motif.motif_id}: effects missing"

    analyzer = evidence_service or MotifContractEvidenceService()
    evidence = analyzer.analyze(motif)
    assert evidence.issues == (), evidence.issues
    assert set(evidence.detected_structural_effects).issuperset(
        motif.effects.structural_effects
    )
    assert set(evidence.meaningful_decision_node_ids).issuperset(
        motif.effects.decision_node_ids
    )
    assert evidence.observed_state_change_count == len(motif.effects.edge_state_changes)
    dependency = motif.effects.expected_downstream_dependency
    if dependency is not MotifDependencyEffect.NONE:
        assert dependency in evidence.detected_dependencies

    port_types = {port.port_type for port in motif.ports}
    assert MotifPortType.MAIN_ROUTE_ENTRY in port_types
    assert MotifPortType.MAIN_ROUTE_EXIT in port_types
    if motif.effects.introduces_failure_exit:
        assert MotifPortType.FAILURE_EXIT in port_types
    if motif.effects.introduces_recovery_exit:
        assert MotifPortType.RECOVERY_EXIT in port_types

    preconditions = motif.preconditions
    incoming_state = preconditions.required_incoming_objective_state
    if incoming_state is MotifIncomingObjectiveState.ANY:
        incoming_state = MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
    valid_context = {
        "difficulty": motif.allowed_difficulties[0],
        "objective_phase_index": preconditions.minimum_objective_phase_index,
        "incoming_objective_state": incoming_state,
        "completed_objective_roles": preconditions.required_completed_objective_roles,
    }
    assert motif.validate_composition_context(**valid_context) == ()

    for difficulty in {"tutorial", "easy", "medium", "hard", "expert"}.difference(
        motif.allowed_difficulties
    ):
        issues = motif.validate_composition_context(
            **(valid_context | {"difficulty": difficulty})
        )
        assert f"motif_difficulty_not_allowed:{motif.motif_id}:{difficulty}" in issues

    for required_role in preconditions.required_completed_objective_roles:
        incomplete_context = valid_context | {
            "completed_objective_roles": tuple(
                role
                for role in preconditions.required_completed_objective_roles
                if role != required_role
            ),
        }
        issues = motif.validate_composition_context(**incomplete_context)
        assert (
            f"motif_required_objective_role_missing:{motif.motif_id}:{required_role}"
            in issues
        )
    for forbidden_role in preconditions.forbidden_completed_objective_roles:
        issues = motif.validate_composition_context(
            **(
                valid_context
                | {
                    "completed_objective_roles": (
                        *preconditions.required_completed_objective_roles,
                        forbidden_role,
                    ),
                }
            )
        )
        assert (
            f"motif_forbidden_objective_role_present:{motif.motif_id}:{forbidden_role}"
            in issues
        )

    limit = motif.effects.maximum_instances_per_composition
    if limit is not None:
        issues = motif.validate_composition_context(
            **valid_context,
            existing_instance_count=limit,
        )
        assert f"motif_composition_limit_reached:{motif.motif_id}:{limit}" in issues
    for incompatible_effect in motif.effects.incompatible_effects:
        issues = motif.validate_composition_context(
            **valid_context,
            existing_effects=(incompatible_effect,),
        )
        assert (
            f"motif_incompatible_effect:{motif.motif_id}:{incompatible_effect}"
            in issues
        )

    return evidence
