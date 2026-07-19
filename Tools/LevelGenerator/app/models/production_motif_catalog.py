"""Evidence-backed coverage contract for the minimum V3 motif catalog."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .motif_evidence import MotifContractEvidence


class ProductionMotifCapability(str, Enum):
    BINARY_LATER_CONSEQUENCE = "binarySplitWithLaterConsequences"
    THREE_WAY_DISTINCT_HUB = "threeWayHubWithDistinctOutcomes"
    FOUR_WAY_DISTINCT_HUB = "fourWayHubWithDistinctOutcomes"
    UNEQUAL_SPLIT_REJOIN = "splitRejoinWithUnequalRouteCosts"
    OBJECTIVE_GATED_BRANCH = "objectiveGatedBranch"
    OBJECTIVE_UNLOCKED_SHORTCUT = "objectiveUnlockedShortcut"
    OBJECTIVE_CLOSED_RETURN = "objectiveClosedReturnRoad"
    CHANGED_HUB_REVISIT = "hubRevisitWithChangedDesiredExit"
    CHANGED_SWITCH_REVISIT = "switchRevisitWithChangedDesiredState"
    RECOVERABLE_LOOP = "recoverableLoop"
    PHASE_DEPENDENT_RING = "phaseDependentRingExits"
    DESTINATION_DECOY = "destinationBeforeObjectivesDecoy"
    NONFATAL_DETOUR = "nonfatalDetour"
    ONE_USE_CONNECTOR = "oneUseConnector"
    TWO_PHASE_REVERSAL = "twoPhaseRouteReversal"
    THREE_PHASE_RELAY = "threePhaseRelay"
    PARALLEL_UNIQUE_OPTIMUM = "parallelSuccessfulRoutesWithUniqueOptimum"
    DELAYED_DOWNSTREAM_CONSEQUENCE = "branchWithDelayedDownstreamConsequence"
    OBJECTIVE_BRANCH_CHANGES_AVAILABILITY = "objectiveBranchChangesLaterAvailability"
    READABILITY_SPACER = "readabilitySpacerLaneExpansion"


@dataclass(frozen=True)
class ProductionMotifCatalogEntry:
    capability: ProductionMotifCapability
    motif_id: str


@dataclass(frozen=True)
class ProductionMotifCatalogReport:
    entries: tuple[ProductionMotifCatalogEntry, ...]
    evidence: tuple[MotifContractEvidence, ...]
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.issues
