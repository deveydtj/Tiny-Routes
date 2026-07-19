from dataclasses import replace

from app.models.motif_contract import (
    MotifDependencyEffect,
    MotifEdgeStateChange,
    MotifEdgeStateChangeKind,
    MotifIncomingObjectiveState,
)
from app.models.graph_recipe import GraphRecipeEdge
from app.models.motif_port import MotifPortType
from app.models.production_motif_catalog import ProductionMotifCapability
from app.motifs.seed_motifs import default_motif_registry, seed_motif_factories
from app.services.motif_contract_evidence_service import MotifContractEvidenceService
from app.services.production_motif_catalog_service import (
    CATALOG_ENTRIES,
    PRODUCTION_MOTIF_IDS,
    ProductionMotifCatalogService,
)
from test_support import assert_motif_contract


def test_every_seed_motif_has_valid_typed_contract_evidence() -> None:
    analyzer = MotifContractEvidenceService()

    reports = tuple(
        assert_motif_contract(factory.build(), evidence_service=analyzer)
        for factory in seed_motif_factories()
    )
    assert all(report.explicit_exit_port_ids for report in reports)


def test_minimum_production_catalog_has_all_capabilities_and_distinct_behavior() -> None:
    report = ProductionMotifCatalogService().validate(default_motif_registry())

    assert report.issues == ()
    assert {entry.capability for entry in CATALOG_ENTRIES} == set(ProductionMotifCapability)
    assert len(PRODUCTION_MOTIF_IDS) >= 20
    assert len(report.evidence) == len(PRODUCTION_MOTIF_IDS)
    assert len({item.behavior_signature for item in report.evidence}) == len(report.evidence)


def test_hub_evidence_detects_three_and_four_distinct_outcomes() -> None:
    registry = default_motif_registry()
    analyzer = MotifContractEvidenceService()

    assert analyzer.analyze(registry.get("three_way_hub").build()).maximum_outcome_count == 3
    assert analyzer.analyze(registry.get("four_way_hub").build()).maximum_outcome_count == 4


def test_state_changes_are_observed_from_edge_availability_not_metadata() -> None:
    motif = default_motif_registry().get("objective_unlocked_shortcut").build()
    analyzer = MotifContractEvidenceService()

    report = analyzer.analyze(motif)
    assert report.observed_state_change_count == len(motif.effects.edge_state_changes)

    invalid_change = MotifEdgeStateChange(
        "entry", "outbound", MotifEdgeStateChangeKind.OPEN, "package"
    )
    invalid = replace(motif, effects=replace(motif.effects, edge_state_changes=(invalid_change,)))
    invalid_report = analyzer.analyze(invalid)
    assert "motif_evidence_state_change_not_observed" in invalid_report.issues


def test_equal_split_cannot_claim_a_meaningful_decision_or_dependency() -> None:
    motif = default_motif_registry().get("split_and_rejoin").build()
    analyzer = MotifContractEvidenceService()
    invalid = replace(
        motif,
        effects=replace(
            motif.effects,
            decision_node_ids=("entry",),
            expected_downstream_dependency=MotifDependencyEffect.EARLIER_CHOICE,
        ),
    )

    report = analyzer.analyze(invalid)

    assert "motif_evidence_decision_not_meaningful:entry" in report.issues
    assert "motif_evidence_dependency_not_detected:earlierChoice" in report.issues


def test_failure_and_recovery_contracts_require_explicit_typed_exits() -> None:
    motif = default_motif_registry().get("three_way_hub").build()
    analyzer = MotifContractEvidenceService()
    stripped = replace(
        motif,
        ports=tuple(
            port
            for port in motif.ports
            if port.port_type not in {MotifPortType.FAILURE_EXIT, MotifPortType.RECOVERY_EXIT}
        ),
    )

    report = analyzer.analyze(stripped)

    assert "motif_evidence_failure_exit_not_explicit" in report.issues
    assert "motif_evidence_recovery_exit_not_explicit" in report.issues


def test_difficulty_preconditions_and_composition_limits_are_enforced() -> None:
    motif = default_motif_registry().get("objective_gate").build()

    assert motif.validate_composition_context(
        difficulty="medium",
        objective_phase_index=0,
        incoming_objective_state=MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE,
    ) == ()
    assert motif.validate_composition_context(
        difficulty="easy",
        objective_phase_index=0,
        incoming_objective_state=MotifIncomingObjectiveState.AFTER_ACTIVE_OBJECTIVE,
        completed_objective_roles=("active_objective",),
        existing_effects=("secondEmbeddedObjective",),
        existing_instance_count=1,
    ) == (
        "motif_difficulty_not_allowed:objective_gate:easy",
        "motif_incoming_objective_state_mismatch:objective_gate",
        "motif_forbidden_objective_role_present:objective_gate:active_objective",
        "motif_incompatible_effect:objective_gate:secondEmbeddedObjective",
        "motif_composition_limit_reached:objective_gate:1",
    )


def test_behavior_signature_ignores_names_tags_and_prose() -> None:
    motif = default_motif_registry().get("binary_delayed_consequence").build()
    renamed = replace(
        motif,
        motif_id="misleading_objective_gate_name",
        intended_decision_effect="Unverified marketing prose.",
        mechanic_metadata=(("category", "four_way_hub"), ("tag", "unique")),
    )
    analyzer = MotifContractEvidenceService()

    assert analyzer.analyze(renamed).behavior_signature == analyzer.analyze(motif).behavior_signature


def test_exact_analysis_detects_objective_and_revisit_dependencies() -> None:
    motif = default_motif_registry().get("objective_state_revisited_hub").build()

    dependencies = set(MotifContractEvidenceService().analyze(motif).detected_dependencies)

    assert dependencies.issuperset({
        MotifDependencyEffect.OBJECTIVE_STATE,
        MotifDependencyEffect.REVISIT,
    })


def test_unique_optimal_claim_requires_one_strictly_cheapest_success() -> None:
    motif = default_motif_registry().get("parallel_unique_optimum").build()
    analyzer = MotifContractEvidenceService()

    report = analyzer.analyze(motif)

    assert report.successful_route_costs == (2, 3)
    assert report.has_unique_optimal_success is True

    tied = replace(
        motif,
        edges=motif.edges + (GraphRecipeEdge("slow_a", "exit"),),
    )
    tied_report = analyzer.analyze(tied)
    assert tied_report.successful_route_costs == (2, 2, 3)
    assert tied_report.has_unique_optimal_success is False
    assert "motif_evidence_unique_optimal_success_not_detected" in tied_report.issues
