"""Fail-closed policy for candidates entering a production V3 transaction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..models.blueprint_stage_result import BlueprintStageResult
from ..models.planning_horizon import PlanningHorizon, PlanningHorizonReport
from ..models.policy_evaluation import PolicyEvaluationResult
from ..models.strategy_search import StrategyTrace
from ..models.strategy_stage_result import StrategyStageResult
from .v3_candidate_pipeline_coordinator import V3CandidatePipelineResult


_STAGE_ORDER = (
    "blueprint",
    "composition",
    "strategy",
    "layout",
    "runtime",
    "quality",
)


@dataclass(frozen=True, order=True)
class ProductionPipelinePolicyIssue:
    code: str
    level_id: str
    detail: str


class ProductionPipelinePolicyError(ValueError):
    """Raised before staging when selected evidence uses a weak path."""


class ProductionPipelinePolicyService:
    """Prove that selected candidates never used a legacy or relaxed fallback.

    Typed V3 stage results prove stage ordering.  These explicit provenance
    fields prove what each handler actually executed, so a handler cannot wrap
    a recipe, direct motif fixture, template, or relaxed playtest path and call
    the result production V3.
    """

    def validate(
        self, pipeline_results: Iterable[V3CandidatePipelineResult]
    ) -> tuple[ProductionPipelinePolicyIssue, ...]:
        results = tuple(pipeline_results)
        issues: list[ProductionPipelinePolicyIssue] = []
        if not results:
            return (
                ProductionPipelinePolicyIssue(
                    "production_pipeline_evidence_missing",
                    "<campaign>",
                    "A production campaign requires selected V3 pipeline evidence.",
                ),
            )

        for index, result in enumerate(results):
            if not isinstance(result, V3CandidatePipelineResult):
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_pipeline_evidence_invalid",
                        f"<selection:{index}>",
                        "Selected evidence is not a V3CandidatePipelineResult.",
                    )
                )
                continue
            level_id = result.request.level_id
            stages = result.stage_results
            if not result.passed or tuple(stage.stage for stage in stages) != _STAGE_ORDER:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_pipeline_incomplete",
                        level_id,
                        "All six locked V3 stages must pass before staging.",
                    )
                )
                continue

            for stage in stages:
                fields = stage.report_fields
                if fields.get("generatorArchitecture") != "production_v3":
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "non_v3_stage_architecture",
                            level_id,
                            f"{stage.stage} did not declare production_v3.",
                        )
                    )
                if fields.get("generatorArchitectureVersion") != 3:
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "non_v3_stage_version",
                            level_id,
                            f"{stage.stage} did not declare architecture version 3.",
                        )
                    )
                if fields.get("fallbackUsed") is not False:
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "production_fallback_used",
                            level_id,
                            f"{stage.stage} did not prove fallbackUsed=false.",
                        )
                    )

            composition = stages[1].report_fields
            if composition.get("execution") != "production_v3_composition":
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "weak_composition_path",
                        level_id,
                        "Composition must execute the blueprint-driven production V3 path.",
                    )
                )
            if composition.get("sourceKind") != "blueprint_composition":
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "weak_composition_source",
                        level_id,
                        "Templates, fixed recipes, and direct motif fixtures are forbidden.",
                    )
                )

            layout = stages[3].report_fields
            if layout.get("manualRepairRequired") is not False:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "manual_repair_path",
                        level_id,
                        "Production layout and road geometry cannot require manual repair.",
                    )
                )

            quality = stages[5].report_fields
            quality_result = result.quality_result
            blueprint_result = stages[0]
            strategy_result = stages[2]
            blueprint = (
                blueprint_result.blueprint
                if isinstance(blueprint_result, BlueprintStageResult)
                else None
            )
            strategy_search = (
                strategy_result.strategy_search
                if isinstance(strategy_result, StrategyStageResult)
                else None
            )
            static_policy_search = (
                strategy_result.static_policy_search
                if isinstance(strategy_result, StrategyStageResult)
                else None
            )
            policy_evaluation = (
                strategy_result.policy_evaluation
                if isinstance(strategy_result, StrategyStageResult)
                else None
            )
            planning_horizon = (
                strategy_result.planning_horizon
                if isinstance(strategy_result, StrategyStageResult)
                else None
            )
            optimal_trace = (
                strategy_search.canonical_optimal_strategy
                if strategy_search is not None
                else None
            )
            if blueprint is None:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_blueprint_evidence_missing",
                        level_id,
                        "Selected candidates require a validated typed blueprint.",
                    )
                )
            if optimal_trace is None:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_strategy_evidence_missing",
                        level_id,
                        "Selected candidates require a proven canonical optimal trace.",
                    )
                )
            else:
                for code, detail in self.optimal_consequence_issues(optimal_trace):
                    issues.append(
                        ProductionPipelinePolicyIssue(code, level_id, detail)
                    )
            if planning_horizon is None:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_planning_horizon_evidence_missing",
                        level_id,
                        "Selected candidates require trace-backed planning-horizon evidence.",
                    )
                )
                downstream_planning_count = None
                deep_planning_count = None
            elif optimal_trace is None:
                downstream_planning_count = None
                deep_planning_count = None
            else:
                planning_issues = self.optimal_planning_horizon_issues(
                    optimal_trace,
                    planning_horizon,
                )
                for code, detail in planning_issues:
                    issues.append(
                        ProductionPipelinePolicyIssue(code, level_id, detail)
                    )
                if planning_issues:
                    downstream_planning_count = None
                    deep_planning_count = None
                else:
                    (
                        downstream_planning_count,
                        deep_planning_count,
                    ) = self.optimal_planning_counts(
                        optimal_trace,
                        planning_horizon,
                    )

            if static_policy_search is None:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_static_policy_evidence_missing",
                        level_id,
                        "Selected candidates require exhaustive static-policy proof evidence.",
                    )
                )
            else:
                if static_policy_search.static_policy_solvable:
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "static_policy_solution_exists",
                            level_id,
                            "A permanent outgoing-road assignment completes every objective.",
                        )
                    )
                if not static_policy_search.exhaustive:
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "static_policy_search_incomplete",
                            level_id,
                            "Production requires exhaustive rejection of every permanent assignment.",
                        )
                    )

            greedy = self.policy_result(policy_evaluation, "greedy_objective")
            if policy_evaluation is None or not policy_evaluation.strategy_proof_exhaustive:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_policy_evidence_missing",
                        level_id,
                        "Selected candidates require exhaustive representative-policy evidence.",
                    )
                )
            if greedy is None:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "greedy_policy_evidence_missing",
                        level_id,
                        "Selected candidates require a greedy_objective policy evaluation.",
                    )
                )
            elif (
                result.request.difficulty.lower() in {"medium", "hard", "expert"}
                and greedy.success_count
            ):
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "greedy_policy_too_successful",
                        level_id,
                        "Medium, hard, and expert candidates must have zero successful "
                        f"greedy-objective runs (observed={greedy.success_count}).",
                    )
                )

            if quality_result is None or quality_result.puzzle_analysis is None:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_quality_evidence_missing",
                        level_id,
                        "Selected candidates require typed final puzzle analysis.",
                    )
                )
            elif quality_result.puzzle_analysis.optimal_accepted_taps < 2:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_one_tap_level",
                        level_id,
                        "Production candidates require at least two proven optimal accepted taps.",
                    )
                )
            if quality_result is not None and quality_result.puzzle_analysis is not None:
                analysis = quality_result.puzzle_analysis
                if analysis.equivalent_choices or analysis.no_op_choices:
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "equivalent_choice_present",
                            level_id,
                            "Final puzzle analysis must report zero equivalent or "
                            "no-op choices "
                            f"(equivalent={analysis.equivalent_choices}, "
                            f"noOp={analysis.no_op_choices}).",
                        )
                    )
                if (
                    static_policy_search is not None
                    and analysis.static_policy_result != static_policy_search
                ):
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "static_policy_evidence_mismatch",
                            level_id,
                            "Final puzzle analysis must preserve the strategy-stage static-policy proof.",
                        )
                    )
                analysis_greedy = self.analysis_policy_result(
                    analysis.agent_results,
                    "greedy_objective",
                )
                if analysis_greedy is None:
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "greedy_policy_evidence_missing",
                            level_id,
                            "Final puzzle analysis must preserve greedy_objective evidence.",
                        )
                    )
                elif greedy is not None and analysis_greedy != greedy:
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "greedy_policy_evidence_mismatch",
                            level_id,
                            "Final puzzle analysis must preserve the strategy-stage greedy evaluation.",
                        )
                    )
                if (
                    analysis_greedy is not None
                    and result.request.difficulty.lower()
                    in {"medium", "hard", "expert"}
                    and analysis_greedy.success_count
                ):
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "greedy_policy_too_successful",
                            level_id,
                            "Medium, hard, and expert final analysis must record zero "
                            f"successful greedy-objective runs (observed={analysis_greedy.success_count}).",
                        )
                    )
                meaningful_trace_count, post_state_decision_count = (
                    self.optimal_decision_counts(optimal_trace)
                    if optimal_trace is not None
                    else (None, None)
                )
                if (
                    analysis.meaningful_decisions < 2
                    or (
                        meaningful_trace_count is not None
                        and meaningful_trace_count < 2
                    )
                ):
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "insufficient_meaningful_decisions",
                            level_id,
                            "Production candidates require at least two meaningful "
                            "decisions in both final analysis and the proven optimum "
                            f"(analysis={analysis.meaningful_decisions}, "
                            f"trace={meaningful_trace_count}).",
                        )
                    )
                declared_adaptive_count = (
                    len(blueprint.adaptive_decision_ids)
                    if blueprint is not None
                    else None
                )
                declared_planning_count = (
                    len(blueprint.planning_decision_ids)
                    if blueprint is not None
                    else None
                )
                required_planning_count = max(
                    1,
                    analysis.planning_decisions,
                    declared_planning_count or 0,
                )
                if (
                    downstream_planning_count is not None
                    and downstream_planning_count < required_planning_count
                ):
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "insufficient_downstream_planning_decisions",
                            level_id,
                            "Production candidates require every claimed planning "
                            "decision to be backed by a meaningful optimal choice "
                            "whose correct road depends on more than the immediately "
                            "adjacent edge "
                            f"(required={required_planning_count}, "
                            f"trace={downstream_planning_count}).",
                        )
                    )
                if (
                    deep_planning_count is not None
                    and result.request.difficulty.lower()
                    in {"medium", "hard", "expert"}
                    and deep_planning_count < 1
                ):
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "insufficient_deep_planning_horizon",
                            level_id,
                            "Medium, hard, and expert candidates require a meaningful "
                            "optimal choice that reasons across at least two upcoming "
                            "decisions or an objective-state phase boundary.",
                        )
                    )
                if (
                    analysis.adaptive_decisions < 1
                    or (
                        declared_adaptive_count is not None
                        and declared_adaptive_count < 1
                    )
                    or (
                        post_state_decision_count is not None
                        and post_state_decision_count < 1
                    )
                ):
                    issues.append(
                        ProductionPipelinePolicyIssue(
                            "insufficient_adaptive_decisions",
                            level_id,
                            "Production candidates require a blueprint-declared adaptive "
                            "decision, final adaptive analysis, and a meaningful optimal "
                            "decision after an earlier objective or route-state change "
                            f"(blueprint={declared_adaptive_count}, "
                            f"analysis={analysis.adaptive_decisions}, "
                            f"postStateTrace={post_state_decision_count}).",
                        )
                    )
            if (
                quality_result is None
                or quality_result.hard_gate is None
                or not quality_result.hard_gate.accepted
            ):
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "production_hard_gate_failed",
                        level_id,
                        "Selected candidates require accepted non-compensating hard gates.",
                    )
                )
            if quality.get("antiTrivialityStatus") != "passed":
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "anti_triviality_evidence_missing",
                        level_id,
                        "Production quality must explicitly report passed anti-triviality gates.",
                    )
                )
            if quality.get("generationProfile") != "production":
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "non_production_quality_profile",
                        level_id,
                        "The relaxed playtest portfolio is not production eligible.",
                    )
                )
            if quality.get("qualityThresholdsRelaxed") is not False:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "relaxed_quality_thresholds",
                        level_id,
                        "Production quality thresholds must be locked and unrelaxed.",
                    )
                )
            if quality.get("manualApprovalRequired") is not False:
                issues.append(
                    ProductionPipelinePolicyIssue(
                        "manual_approval_path",
                        level_id,
                        "Production selection cannot depend on manual approval.",
                    )
                )

        return tuple(sorted(set(issues)))

    def require(
        self, pipeline_results: Iterable[V3CandidatePipelineResult]
    ) -> None:
        issues = self.validate(pipeline_results)
        if not issues:
            return
        summary = "; ".join(
            f"{issue.level_id}:{issue.code}" for issue in issues
        )
        raise ProductionPipelinePolicyError(
            f"production_pipeline_policy_failed: {summary}"
        )

    @staticmethod
    def optimal_decision_counts(optimal_trace: StrategyTrace) -> tuple[int, int]:
        """Measure decisions from the proof trace, not mutable report counters.

        A decision is post-state only when an earlier action completed an
        objective or changed road state. A state transition caused while taking
        the current action cannot retroactively make that same choice adaptive.
        """

        meaningful_count = 0
        post_state_count = 0
        prior_state_change = False
        for action in optimal_trace.actions:
            evidence = action.consequence_evidence
            if (
                action.meaningful_decision is True
                and evidence is not None
                and evidence.meaningful
            ):
                meaningful_count += 1
                if prior_state_change:
                    post_state_count += 1
            transition = action.state_transition
            if transition is not None and transition.changes_state:
                prior_state_change = True
        return meaningful_count, post_state_count

    @staticmethod
    def optimal_consequence_issues(
        optimal_trace: StrategyTrace,
    ) -> tuple[tuple[str, str], ...]:
        """Fail closed when a trace counter is not backed by exact consequences."""

        issues: list[tuple[str, str]] = []
        for index, action in enumerate(optimal_trace.actions):
            evidence = action.consequence_evidence
            if evidence is None:
                issues.append(
                    (
                        "decision_consequence_evidence_missing",
                        f"Optimal action {index} at {action.node_id} has no exact "
                        "choice-consequence comparison.",
                    )
                )
                continue
            if not evidence.exhaustive:
                issues.append(
                    (
                        "decision_consequence_evidence_incomplete",
                        f"Optimal action {index} at {action.node_id} has incomplete "
                        "choice-consequence evidence.",
                    )
                )
            if action.meaningful_decision is not evidence.meaningful:
                issues.append(
                    (
                        "meaningful_decision_evidence_mismatch",
                        f"Optimal action {index} at {action.node_id} declares "
                        f"meaningful={action.meaningful_decision}, but its material "
                        f"consequences prove meaningful={evidence.meaningful}.",
                    )
                )
            if evidence.equivalent_choice_count:
                issues.append(
                    (
                        "equivalent_choice_present",
                        f"Decision {index} at {action.node_id} contains "
                        f"{evidence.equivalent_choice_count} redundant choice(s) "
                        "with identical future consequences.",
                    )
                )
        return tuple(issues)

    @staticmethod
    def optimal_planning_horizon_issues(
        optimal_trace: StrategyTrace,
        planning_horizon: PlanningHorizonReport,
    ) -> tuple[tuple[str, str], ...]:
        """Require horizon evidence to describe the canonical optimum exactly."""

        if not planning_horizon.strategy_proof_exhaustive:
            return (
                (
                    "production_planning_horizon_evidence_incomplete",
                    "Planning-horizon classification must use an exhaustive "
                    "strategy proof.",
                ),
            )
        if len(planning_horizon.decisions) != len(optimal_trace.actions):
            return (
                (
                    "planning_horizon_evidence_mismatch",
                    "Planning-horizon evidence must contain exactly one entry for "
                    "every canonical optimal action "
                    f"(report={len(planning_horizon.decisions)}, "
                    f"trace={len(optimal_trace.actions)}).",
                ),
            )

        issues: list[tuple[str, str]] = []
        for index, (action, decision) in enumerate(
            zip(optimal_trace.actions, planning_horizon.decisions)
        ):
            if (
                decision.decision_ordinal != index
                or decision.node_id != action.node_id
                or decision.optimal_edge_id != action.selected_edge_id
            ):
                issues.append(
                    (
                        "planning_horizon_evidence_mismatch",
                        f"Planning-horizon entry {index} does not match canonical "
                        f"action {action.node_id}:{action.selected_edge_id}.",
                    )
                )
        return tuple(issues)

    @staticmethod
    def optimal_planning_counts(
        optimal_trace: StrategyTrace,
        planning_horizon: PlanningHorizonReport,
    ) -> tuple[int, int]:
        """Count meaningful downstream and multi-decision planning evidence."""

        downstream_count = 0
        deep_count = 0
        for action, decision in zip(
            optimal_trace.actions,
            planning_horizon.decisions,
        ):
            evidence = action.consequence_evidence
            if not (
                action.meaningful_decision is True
                and evidence is not None
                and evidence.meaningful
            ):
                continue
            if decision.horizon.rank >= PlanningHorizon.ONE_TRANSITION.rank:
                downstream_count += 1
            if decision.horizon.rank >= PlanningHorizon.TWO_TRANSITIONS.rank:
                deep_count += 1
        return downstream_count, deep_count

    @staticmethod
    def policy_result(
        policy_evaluation,
        policy_name: str,
    ) -> PolicyEvaluationResult | None:
        if policy_evaluation is None:
            return None
        try:
            return policy_evaluation.evaluation_for(policy_name)
        except KeyError:
            return None

    @staticmethod
    def analysis_policy_result(
        agent_results: Iterable[PolicyEvaluationResult],
        policy_name: str,
    ) -> PolicyEvaluationResult | None:
        return next(
            (item for item in agent_results if item.policy_name == policy_name),
            None,
        )
