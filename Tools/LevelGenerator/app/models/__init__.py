from .candidate_signature import CandidateSignature
from .difficulty_preset import DifficultyPreset
from .decision_profile import DecisionProfile
from .decision_dependency_graph import (
    DecisionDependency,
    DecisionDependencyGraph,
    DecisionDependencyKind,
    DecisionNode,
)
from .puzzle_blueprint import ObjectiveSpec, PuzzleBlueprint, StateTransitionSpec
from .puzzle_motif import MotifCompatibilityConstraints, PuzzleMotif
from .motif_contract import (
    MotifDependencyEffect,
    MotifEdgeStateChange,
    MotifEdgeStateChangeKind,
    MotifEffectContract,
    MotifGameplayEffect,
    MotifIncomingObjectiveState,
    MotifPreconditionContract,
    MotifStructuralEffect,
)
from .motif_evidence import MotifContractEvidence
from .production_motif_catalog import (
    ProductionMotifCapability,
    ProductionMotifCatalogEntry,
    ProductionMotifCatalogReport,
)
from .motif_port import MotifPort, MotifPortType
from .composition_state import (
    AssignedStateEffect,
    CompositionGraph,
    CompositionState,
    LayoutFootprintEstimate,
    ObjectivePhaseBoundary,
    OpenCompositionPort,
    PartialStrategicMetrics,
)
from .composition_search import (
    CompositionRejectionCount,
    CompositionSearchChoice,
    CompositionSearchResult,
    CompositionSearchTraceEntry,
)
from .composition_pruning import (
    CompositionPruningAssessment,
    CompositionStrategicConstraints,
)
from .composition_transformation import (
    CompositionTransformation,
    CompositionTransformationKind,
    CompositionTransformationProof,
    CompositionTransformationResult,
)
from .composition_diversity import (
    CompositionDiversityConstraints,
    CompositionDuplicateAssessment,
    CompositionPoolEntry,
    CompositionPoolResult,
)
from .puzzle_state import PuzzleState, PuzzleTerminalOutcome
from .strategy_search import (
    AlternateSuccessClassification,
    AlternateSuccessKind,
    AlternateSuccessReport,
    FailureRecoveryReport,
    MeaningfulChoiceClassification,
    MeaningfulChoiceKey,
    MeaningfulChoiceOutcomeKind,
    OptimalStrategyRequirements,
    StrategyAction,
    StrategyCost,
    StrategyEquivalenceClass,
    StrategyEquivalenceKey,
    StrategySearchResult,
    StrategyStateTransition,
    StrategyTrace,
    UniqueOptimalProof,
)
from .puzzle_experience_target import PuzzleExperienceTarget
from .generated_level import GeneratedLevel
from .generation_quality import GenerationQualityScore
from .generation_batch_plan import GenerationBatchPlan, GenerationBatchPlanEntry
from .generation_result import GenerationResult, SwiftTestSummary
from .graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from .layout_constraints import ConstraintViolation, LayoutConstraints, RepairOperation, ReservedIconClearance
from .layout_graph import GridCell, Lane, LayoutGraph, NodeFootprint, SwitchPortDirection
from .layout_result import LayerAssignment, LayoutLayerResult, LayoutResult
from .recipe_variant_spec import RecipeVariantSpec
from .recipe_lifecycle import RecipeLifecycleRecord, RecipeLifecycleStatus
from .recipe_topology_rules import RecipeTopologyRules
from .runtime_parity import RuntimeParityValidationResult
from .runtime_solution_search import (
    RuntimeDecisionTimingDiagnostic, RuntimeSolutionAction, RuntimeSolutionSearchResult,
)
from .simulation import SimulationResult, SimulationStep
from .template_spec import TemplateSpec
from .template_variant_spec import TemplateVariantSpec
from .stage_result import CandidateStageResult, StageResult

__all__ = [
    "DifficultyPreset",
    "DecisionProfile",
    "DecisionDependency",
    "DecisionDependencyGraph",
    "DecisionDependencyKind",
    "DecisionNode",
    "ObjectiveSpec",
    "PuzzleBlueprint",
    "StateTransitionSpec",
    "MotifCompatibilityConstraints",
    "PuzzleMotif",
    "MotifPort",
    "MotifPortType",
    "AssignedStateEffect",
    "CompositionGraph",
    "CompositionState",
    "LayoutFootprintEstimate",
    "ObjectivePhaseBoundary",
    "OpenCompositionPort",
    "PartialStrategicMetrics",
    "CompositionRejectionCount",
    "CompositionSearchChoice",
    "CompositionSearchResult",
    "CompositionSearchTraceEntry",
    "CompositionPruningAssessment",
    "CompositionStrategicConstraints",
    "CompositionTransformation",
    "CompositionTransformationKind",
    "CompositionTransformationProof",
    "CompositionTransformationResult",
    "CompositionDiversityConstraints",
    "CompositionDuplicateAssessment",
    "CompositionPoolEntry",
    "CompositionPoolResult",
    "PuzzleState",
    "PuzzleTerminalOutcome",
    "AlternateSuccessClassification",
    "AlternateSuccessKind",
    "AlternateSuccessReport",
    "FailureRecoveryReport",
    "MeaningfulChoiceClassification",
    "MeaningfulChoiceKey",
    "MeaningfulChoiceOutcomeKind",
    "StrategyAction",
    "StrategyCost",
    "StrategyEquivalenceClass",
    "StrategyEquivalenceKey",
    "StrategyStateTransition",
    "StrategySearchResult",
    "StrategyTrace",
    "OptimalStrategyRequirements",
    "UniqueOptimalProof",
    "MotifDependencyEffect",
    "MotifEdgeStateChange",
    "MotifEdgeStateChangeKind",
    "MotifEffectContract",
    "MotifGameplayEffect",
    "MotifIncomingObjectiveState",
    "MotifPreconditionContract",
    "MotifStructuralEffect",
    "MotifContractEvidence",
    "ProductionMotifCapability",
    "ProductionMotifCatalogEntry",
    "ProductionMotifCatalogReport",
    "PuzzleExperienceTarget",
    "CandidateSignature",
    "GeneratedLevel",
    "GenerationQualityScore",
    "GenerationBatchPlan",
    "GenerationBatchPlanEntry",
    "GenerationResult",
    "GraphRecipe",
    "GraphRecipeEdge",
    "GraphRecipeNode",
    "ConstraintViolation",
    "GridCell",
    "Lane",
    "LayerAssignment",
    "LayoutConstraints",
    "LayoutGraph",
    "LayoutLayerResult",
    "LayoutResult",
    "NodeFootprint",
    "RepairOperation",
    "ReservedIconClearance",
    "SwitchPortDirection",
    "RecipeTopologyRules",
    "RecipeLifecycleRecord",
    "RecipeLifecycleStatus",
    "RecipeVariantSpec",
    "RuntimeParityValidationResult",
    "RuntimeDecisionTimingDiagnostic",
    "RuntimeSolutionAction",
    "RuntimeSolutionSearchResult",
    "SimulationResult",
    "SimulationStep",
    "SwiftTestSummary",
    "TemplateSpec",
    "TemplateVariantSpec",
    "CandidateStageResult",
    "StageResult",
]
