"""Non-compensating strategic gates for production V3 puzzles."""

from __future__ import annotations

from ..models.local_obviousness import LocalObviousnessReport
from ..models.production_puzzle_gate import (
    ProductionPuzzleGateCheck,
    ProductionPuzzleGateResult,
)
from ..models.puzzle_analysis import PuzzleAnalysis
from ..models.puzzle_experience_target import PuzzleExperienceTarget
from ..models.strategy_search import MeaningfulChoiceOutcomeKind, UniqueOptimalProof
from .unique_optimal_gate_service import UniqueOptimalGateService


_RECOVERABLE_OUTCOMES = frozenset(
    {
        MeaningfulChoiceOutcomeKind.RECOVERABLE_DETOUR.value,
        MeaningfulChoiceOutcomeKind.SUCCESSFUL_SLOWER_ROUTE.value,
        MeaningfulChoiceOutcomeKind.SUCCESSFUL_HIGHER_TAP_ROUTE.value,
        MeaningfulChoiceOutcomeKind.SUCCESSFUL_EQUAL_COST_ROUTE.value,
    }
)
_FATAL_OUTCOMES = frozenset(
    {
        MeaningfulChoiceOutcomeKind.IMMEDIATE_DEAD_END.value,
        MeaningfulChoiceOutcomeKind.OBJECTIVE_ORDER_FAILURE.value,
        MeaningfulChoiceOutcomeKind.LOOP_UNTIL_TIME_EXPIRES.value,
        MeaningfulChoiceOutcomeKind.STATE_TRAP.value,
    }
)
_GREEDY_SUCCESS_RATE_LIMITS = {
    "easy": 1.0,
    "medium": 0.35,
    "hard": 0.10,
    "expert": 0.0,
}


class ProductionPuzzleGateService:
    """Apply every hard rule before preference scoring or portfolio selection."""

    def __init__(
        self,
        unique_optimal_gate: UniqueOptimalGateService | None = None,
    ) -> None:
        self._unique_optimal_gate = unique_optimal_gate or UniqueOptimalGateService()

    def assess(
        self,
        analysis: PuzzleAnalysis,
        target: PuzzleExperienceTarget,
        *,
        unique_optimal_proof: UniqueOptimalProof | None,
        local_obviousness: LocalObviousnessReport | None,
        state_change_readable: bool | None,
        runtime_solution_robust: bool | None,
    ) -> ProductionPuzzleGateResult:
        """Return all failures deterministically instead of stopping at the first one."""

        greedy_limit = _GREEDY_SUCCESS_RATE_LIMITS.get(target.difficulty, 0.0)
        greedy = self._agent_result(analysis, "greedy_objective")
        recoverable_count = sum(
            item.count
            for item in analysis.recovery_failure_distribution
            if item.outcome_code in _RECOVERABLE_OUTCOMES
        )
        fatal_count = sum(
            item.count
            for item in analysis.recovery_failure_distribution
            if item.outcome_code in _FATAL_OUTCOMES
        )
        observed_failure_codes = {
            item.outcome_code
            for item in analysis.recovery_failure_distribution
            if item.outcome_code in _FATAL_OUTCOMES | _RECOVERABLE_OUTCOMES
        }
        unique = self._unique_optimal_gate.assess(analysis, unique_optimal_proof)
        checks = (
            self._check(
                "production_one_tap_level",
                analysis.optimal_accepted_taps >= 2,
                analysis.optimal_accepted_taps,
                "at least 2 optimal accepted taps",
            ),
            self._check(
                "insufficient_meaningful_decisions",
                analysis.meaningful_decisions >= target.meaningful_decision_range[0],
                analysis.meaningful_decisions,
                f"at least {target.meaningful_decision_range[0]}",
            ),
            self._check(
                "insufficient_planning_decisions",
                analysis.planning_decisions >= target.planning_decision_minimum,
                analysis.planning_decisions,
                f"at least {target.planning_decision_minimum}",
            ),
            self._check(
                "insufficient_adaptive_decisions",
                analysis.adaptive_decisions >= target.adaptive_decision_minimum,
                analysis.adaptive_decisions,
                f"at least {target.adaptive_decision_minimum}",
            ),
            self._check(
                "insufficient_dependency_depth",
                analysis.dependency_depth >= target.dependency_depth_range[0],
                analysis.dependency_depth,
                f"at least {target.dependency_depth_range[0]}",
            ),
            self._check(
                "static_policy_solution_exists",
                not analysis.static_policy_result.static_policy_solvable,
                analysis.static_policy_result.static_policy_solvable,
                "false",
            ),
            self._check(
                "static_policy_search_incomplete",
                analysis.static_policy_result.proof_complete,
                analysis.static_policy_result.proof_complete,
                "complete proof",
            ),
            self._check(
                "greedy_policy_evidence_missing",
                greedy is not None,
                greedy is not None,
                "greedy_objective policy result",
            ),
            self._check(
                "greedy_policy_too_successful",
                greedy is not None and greedy.success_rate <= greedy_limit,
                "missing" if greedy is None else round(greedy.success_rate, 9),
                f"success rate <= {greedy_limit}",
            ),
            self._check(
                "equivalent_choice_present",
                analysis.equivalent_choices == 0 and analysis.no_op_choices == 0,
                analysis.equivalent_choices + analysis.no_op_choices,
                "zero equivalent or no-op choices",
            ),
            self._check(
                "unique_optimal_not_proven",
                unique.accepted,
                ", ".join(unique.proof_rejection_reasons) or "proven",
                "one exhaustive, analysis-consistent optimal strategy class",
            ),
            self._check(
                "objective_sequence_trivial",
                analysis.objective_phases >= target.objective_count_range[0],
                analysis.objective_phases,
                f"at least {target.objective_count_range[0]} ordered objectives",
            ),
            self._check(
                "state_change_without_player_consequence",
                analysis.state_changes >= target.state_change_range[0]
                and analysis.adaptive_decisions > 0,
                f"{analysis.state_changes} changes, {analysis.adaptive_decisions} adaptive decisions",
                "target state-change minimum and at least one adaptive consequence",
            ),
            self._check(
                "insufficient_recoverable_mistakes",
                recoverable_count >= target.recoverable_mistake_range[0],
                recoverable_count,
                f"at least {target.recoverable_mistake_range[0]}",
            ),
            self._check(
                "excessive_fatal_mistakes",
                fatal_count <= target.fatal_mistake_cap,
                fatal_count,
                f"at most {target.fatal_mistake_cap}",
            ),
            self._check(
                "all_failures_are_instant_dead_ends",
                bool(observed_failure_codes)
                and observed_failure_codes
                != {MeaningfulChoiceOutcomeKind.IMMEDIATE_DEAD_END.value},
                ", ".join(sorted(observed_failure_codes)) or "none",
                "at least one recoverable or non-instant outcome",
            ),
            self._check(
                "all_optimal_decisions_locally_obvious",
                local_obviousness is not None
                and local_obviousness.strategy_proof_exhaustive
                and local_obviousness.accepted,
                (
                    "missing"
                    if local_obviousness is None
                    else ", ".join(local_obviousness.rejection_reasons) or "accepted"
                ),
                "exhaustive local-obviousness report with a non-obvious decision",
            ),
            self._check(
                "unreadable_state_change",
                state_change_readable is True,
                state_change_readable,
                "true",
            ),
            self._check(
                "runtime_solution_not_robust",
                runtime_solution_robust is True,
                runtime_solution_robust,
                "true",
            ),
        )
        return ProductionPuzzleGateResult(
            checks=checks,
            rejection_reasons=tuple(check.code for check in checks if not check.passed),
        )

    @staticmethod
    def _agent_result(analysis: PuzzleAnalysis, name: str):
        try:
            return analysis.agent_result_for(name)
        except KeyError:
            return None

    @staticmethod
    def _check(
        code: str,
        passed: bool,
        actual: object,
        required: str,
    ) -> ProductionPuzzleGateCheck:
        return ProductionPuzzleGateCheck(
            code=code,
            passed=bool(passed),
            actual=str(actual).lower() if isinstance(actual, bool) else str(actual),
            required=required,
        )

    gate = assess
