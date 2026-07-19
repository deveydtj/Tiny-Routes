"""Validate Task 3.5 coverage using detected graph behavior."""

from __future__ import annotations

from ..models.motif_contract import (
    MotifDependencyEffect,
    MotifEdgeStateChangeKind,
    MotifGameplayEffect,
    MotifStructuralEffect,
)
from ..models.production_motif_catalog import (
    ProductionMotifCapability,
    ProductionMotifCatalogEntry,
    ProductionMotifCatalogReport,
)
from ..motifs.motif_registry import MotifRegistry
from .motif_contract_evidence_service import MotifContractEvidenceService


PRODUCTION_MOTIF_IDS = (
    "straight_segment",
    "recoverable_detour",
    "split_and_rejoin",
    "objective_gate",
    "package_branch",
    "return_loop",
    "ring_route",
    "three_way_hub",
    "four_way_hub",
    "road_opens_after_package",
    "shortcut_closes_after_package",
    "return_route_changes_after_package",
    "package_state_revisited_switch",
    "binary_delayed_consequence",
    "phase_dependent_ring_exits",
    "destination_before_objectives_decoy",
    "one_use_objective_connector",
    "objective_state_revisited_hub",
    "three_phase_relay",
    "parallel_unique_optimum",
    "objective_unlocked_shortcut",
    "objective_closed_return_road",
)


CATALOG_ENTRIES = (
    ProductionMotifCatalogEntry(ProductionMotifCapability.BINARY_LATER_CONSEQUENCE, "binary_delayed_consequence"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.THREE_WAY_DISTINCT_HUB, "three_way_hub"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.FOUR_WAY_DISTINCT_HUB, "four_way_hub"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.UNEQUAL_SPLIT_REJOIN, "recoverable_detour"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.OBJECTIVE_GATED_BRANCH, "objective_gate"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.OBJECTIVE_UNLOCKED_SHORTCUT, "objective_unlocked_shortcut"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.OBJECTIVE_CLOSED_RETURN, "objective_closed_return_road"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.CHANGED_HUB_REVISIT, "objective_state_revisited_hub"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.CHANGED_SWITCH_REVISIT, "package_state_revisited_switch"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.RECOVERABLE_LOOP, "return_loop"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.PHASE_DEPENDENT_RING, "phase_dependent_ring_exits"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.DESTINATION_DECOY, "destination_before_objectives_decoy"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.NONFATAL_DETOUR, "recoverable_detour"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.ONE_USE_CONNECTOR, "one_use_objective_connector"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.TWO_PHASE_REVERSAL, "return_route_changes_after_package"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.THREE_PHASE_RELAY, "three_phase_relay"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.PARALLEL_UNIQUE_OPTIMUM, "parallel_unique_optimum"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.DELAYED_DOWNSTREAM_CONSEQUENCE, "binary_delayed_consequence"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.OBJECTIVE_BRANCH_CHANGES_AVAILABILITY, "objective_gate"),
    ProductionMotifCatalogEntry(ProductionMotifCapability.READABILITY_SPACER, "straight_segment"),
)


class ProductionMotifCatalogService:
    def __init__(self, evidence_service: MotifContractEvidenceService | None = None) -> None:
        self._evidence_service = evidence_service or MotifContractEvidenceService()

    def validate(self, registry: MotifRegistry) -> ProductionMotifCatalogReport:
        issues: list[str] = []
        if {entry.capability for entry in CATALOG_ENTRIES} != set(ProductionMotifCapability):
            issues.append("production_motif_capability_coverage_incomplete")
        evidence_by_id = {}
        motifs_by_id = {}
        for motif_id in PRODUCTION_MOTIF_IDS:
            try:
                motif = registry.get(motif_id).build()
            except KeyError:
                issues.append(f"production_motif_missing:{motif_id}")
                continue
            motifs_by_id[motif_id] = motif
            evidence = self._evidence_service.analyze(motif)
            evidence_by_id[motif_id] = evidence
            issues.extend(f"production_motif_invalid:{motif_id}:{issue}" for issue in evidence.issues)

        signatures = [evidence.behavior_signature for evidence in evidence_by_id.values()]
        if len(evidence_by_id) < 20:
            issues.append(f"production_motif_count_insufficient:{len(evidence_by_id)}")
        if len(signatures) != len(set(signatures)):
            issues.append("production_motif_behavior_signature_duplicate")

        for entry in CATALOG_ENTRIES:
            motif = motifs_by_id.get(entry.motif_id)
            evidence = evidence_by_id.get(entry.motif_id)
            if motif is None or evidence is None:
                issues.append(f"production_motif_capability_missing:{entry.capability.value}")
            elif not self._has_capability(entry.capability, motif, evidence):
                issues.append(
                    f"production_motif_capability_evidence_missing:"
                    f"{entry.capability.value}:{entry.motif_id}"
                )
        return ProductionMotifCatalogReport(
            entries=CATALOG_ENTRIES,
            evidence=tuple(evidence_by_id[motif_id] for motif_id in PRODUCTION_MOTIF_IDS if motif_id in evidence_by_id),
            issues=tuple(dict.fromkeys(issues)),
        )

    def _has_capability(self, capability, motif, evidence) -> bool:
        effects = motif.effects
        assert effects is not None
        gameplay = set(effects.gameplay_effects)
        structural = set(evidence.detected_structural_effects)
        dependencies = set(evidence.detected_dependencies)
        changes = {change.kind for change in effects.edge_state_changes}
        unequal = len(set(evidence.successful_route_costs)) >= 2
        requirements = {
            ProductionMotifCapability.BINARY_LATER_CONSEQUENCE:
                evidence.maximum_outcome_count >= 2 and MotifDependencyEffect.EARLIER_CHOICE in dependencies,
            ProductionMotifCapability.THREE_WAY_DISTINCT_HUB:
                MotifStructuralEffect.HUB in structural and evidence.maximum_outcome_count >= 3,
            ProductionMotifCapability.FOUR_WAY_DISTINCT_HUB:
                MotifStructuralEffect.HUB in structural and evidence.maximum_outcome_count >= 4,
            ProductionMotifCapability.UNEQUAL_SPLIT_REJOIN:
                MotifStructuralEffect.REJOIN in structural and unequal,
            ProductionMotifCapability.OBJECTIVE_GATED_BRANCH:
                MotifGameplayEffect.OBJECTIVE_GATE in gameplay and bool(changes),
            ProductionMotifCapability.OBJECTIVE_UNLOCKED_SHORTCUT:
                MotifGameplayEffect.UNLOCK_SHORTCUT in gameplay and MotifEdgeStateChangeKind.OPEN in changes,
            ProductionMotifCapability.OBJECTIVE_CLOSED_RETURN:
                MotifGameplayEffect.CLOSE_BEHIND_ROUTE in gameplay and MotifEdgeStateChangeKind.CLOSE in changes,
            ProductionMotifCapability.CHANGED_HUB_REVISIT:
                MotifStructuralEffect.HUB in structural and MotifDependencyEffect.REVISIT in dependencies and bool(changes),
            ProductionMotifCapability.CHANGED_SWITCH_REVISIT:
                MotifDependencyEffect.REVISIT in dependencies and changes.issuperset({MotifEdgeStateChangeKind.OPEN, MotifEdgeStateChangeKind.CLOSE}),
            ProductionMotifCapability.RECOVERABLE_LOOP:
                MotifStructuralEffect.RETURN_CORRIDOR in structural and effects.introduces_recovery_exit,
            ProductionMotifCapability.PHASE_DEPENDENT_RING:
                MotifStructuralEffect.RING in structural and MotifDependencyEffect.OBJECTIVE_STATE in dependencies,
            ProductionMotifCapability.DESTINATION_DECOY:
                MotifGameplayEffect.DESTINATION_DECOY in gameplay and any(node.role == "destination" for node in motif.nodes),
            ProductionMotifCapability.NONFATAL_DETOUR:
                MotifGameplayEffect.ALTERNATE_SUCCESSFUL_DETOUR in gameplay and effects.introduces_recovery_exit,
            ProductionMotifCapability.ONE_USE_CONNECTOR:
                MotifGameplayEffect.ONE_USE_CONNECTOR in gameplay and MotifEdgeStateChangeKind.CONSUME in changes,
            ProductionMotifCapability.TWO_PHASE_REVERSAL:
                changes.issuperset({MotifEdgeStateChangeKind.OPEN, MotifEdgeStateChangeKind.CLOSE}) and effects.introduces_revisit,
            ProductionMotifCapability.THREE_PHASE_RELAY:
                len(effects.completed_objective_node_ids) >= 3 and effects.introduces_revisit,
            ProductionMotifCapability.PARALLEL_UNIQUE_OPTIMUM:
                MotifGameplayEffect.UNIQUE_OPTIMAL_ALTERNATE_ROUTE in gameplay
                and evidence.has_unique_optimal_success,
            ProductionMotifCapability.DELAYED_DOWNSTREAM_CONSEQUENCE:
                MotifGameplayEffect.DELAYED_CONSEQUENCE in gameplay and MotifDependencyEffect.EARLIER_CHOICE in dependencies,
            ProductionMotifCapability.OBJECTIVE_BRANCH_CHANGES_AVAILABILITY:
                bool(effects.completed_objective_node_ids) and bool(changes) and evidence.maximum_outcome_count >= 2,
            ProductionMotifCapability.READABILITY_SPACER:
                MotifStructuralEffect.SEGMENT in structural and not evidence.meaningful_decision_node_ids,
        }
        return requirements[capability]
