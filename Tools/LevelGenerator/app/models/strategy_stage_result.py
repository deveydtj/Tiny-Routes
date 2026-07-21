"""Typed boundary result for V3 exact and representative strategy analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .local_obviousness import LocalObviousnessReport
from .planning_horizon import PlanningHorizonReport
from .policy_evaluation import PolicyEvaluationReport
from .stage_result import CandidateStageResult
from .static_policy import (
    SearchLimitRejectionResult,
    StaticPolicySearchResult,
)
from .strategy_search import (
    AlternateSuccessReport,
    FailureRecoveryReport,
    StrategySearchResult,
    UniqueOptimalProof,
)


_STAGE = "strategy"
_ACCEPTED_CODE = "strategy_accepted"


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def _stable_codes(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        code = _identifier(value, "rejection reason")
        if code not in result:
            result.append(code)
    return tuple(result)


@dataclass(frozen=True)
class StrategyStageResult(CandidateStageResult):
    """Proof-bearing result that gates expensive layout and runtime work.

    A successful result requires exhaustive exact search, an accepted unique
    optimum, exhaustive rejection of permanent switch assignments, complete
    representative-policy evidence, and a passed search-limit gate.
    Rejected results retain every proof artifact completed before the failure.
    """

    passed: bool = False
    stage: str = _STAGE
    code: str = "strategy_evidence_incomplete"
    details: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    report_fields: dict[str, Any] = field(default_factory=dict)
    candidate_id: str = ""
    level_id: str = ""
    seed: int = 0
    difficulty: str = ""
    status: str = "rejected"
    strategy_search: StrategySearchResult | None = None
    unique_optimal_proof: UniqueOptimalProof | None = None
    static_policy_search: StaticPolicySearchResult | None = None
    policy_evaluation: PolicyEvaluationReport | None = None
    alternate_successes: AlternateSuccessReport | None = None
    failure_recovery: FailureRecoveryReport | None = None
    planning_horizon: PlanningHorizonReport | None = None
    local_obviousness: LocalObviousnessReport | None = None
    search_limit_gate: SearchLimitRejectionResult | None = None
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.stage != _STAGE:
            raise ValueError(f"stage must be {_STAGE!r}")
        if not isinstance(self.passed, bool):
            raise ValueError("passed must be a Boolean")
        object.__setattr__(
            self,
            "candidate_id",
            _identifier(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(self, "level_id", _identifier(self.level_id, "level_id"))
        object.__setattr__(
            self,
            "difficulty",
            _identifier(self.difficulty, "difficulty").lower(),
        )
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ValueError("seed must be an integer")

        self._validate_artifact_types()
        reasons = _stable_codes(tuple(self.rejection_reasons))
        object.__setattr__(self, "rejection_reasons", reasons)
        complete = self._has_accepted_evidence()

        if self.passed:
            if reasons:
                raise ValueError("an accepted strategy stage cannot have rejection reasons")
            if not complete:
                raise ValueError("accepted strategy stage requires complete proof evidence")
            if self.status != "accepted":
                raise ValueError("accepted strategy stage status must be 'accepted'")
            if self.code != _ACCEPTED_CODE:
                raise ValueError(f"accepted strategy stage code must be {_ACCEPTED_CODE!r}")
        else:
            if not reasons:
                raise ValueError("a rejected strategy stage requires rejection reasons")
            if self.status != "rejected":
                raise ValueError("rejected strategy stage status must be 'rejected'")
            if self.code != reasons[0]:
                raise ValueError("rejected strategy stage code must be its first reason")

    def _validate_artifact_types(self) -> None:
        expected_types = (
            ("strategy_search", self.strategy_search, StrategySearchResult),
            ("unique_optimal_proof", self.unique_optimal_proof, UniqueOptimalProof),
            ("static_policy_search", self.static_policy_search, StaticPolicySearchResult),
            ("policy_evaluation", self.policy_evaluation, PolicyEvaluationReport),
            ("alternate_successes", self.alternate_successes, AlternateSuccessReport),
            ("failure_recovery", self.failure_recovery, FailureRecoveryReport),
            ("planning_horizon", self.planning_horizon, PlanningHorizonReport),
            ("local_obviousness", self.local_obviousness, LocalObviousnessReport),
            ("search_limit_gate", self.search_limit_gate, SearchLimitRejectionResult),
        )
        for field_name, value, expected_type in expected_types:
            if value is not None and not isinstance(value, expected_type):
                raise TypeError(
                    f"{field_name} must be a {expected_type.__name__} or None"
                )
        level_reports = (
            ("policy evaluation", self.policy_evaluation),
            ("planning horizon", self.planning_horizon),
            ("local obviousness", self.local_obviousness),
        )
        for report_name, report in level_reports:
            if report is not None and report.level_id != self.level_id:
                raise ValueError(f"{report_name} level must match the stage level")

        search = self.strategy_search
        proof = self.unique_optimal_proof
        policy = self.policy_evaluation
        if search is not None and proof is not None:
            if proof.optimal_cost != search.optimal_cost:
                raise ValueError("unique-optimal proof cost must match strategy search")
            if proof.exhaustive != search.exhaustive:
                raise ValueError(
                    "unique-optimal proof exhaustiveness must match strategy search"
                )
        if search is not None and policy is not None:
            if policy.optimal_cost != search.optimal_cost:
                raise ValueError("policy optimum must match strategy search")

    def _has_accepted_evidence(self) -> bool:
        search = self.strategy_search
        proof = self.unique_optimal_proof
        static = self.static_policy_search
        policy = self.policy_evaluation
        alternates = self.alternate_successes
        failure_recovery = self.failure_recovery
        planning_horizon = self.planning_horizon
        local_obviousness = self.local_obviousness
        limit_gate = self.search_limit_gate
        return bool(
            search is not None
            and search.succeeded
            and search.exhaustive
            and proof is not None
            and proof.accepted
            and proof.exhaustive
            and static is not None
            and static.accepted_for_production
            and policy is not None
            and policy.strategy_proof_exhaustive
            and alternates is not None
            and alternates.exhaustive
            and failure_recovery is not None
            and failure_recovery.exhaustive
            and planning_horizon is not None
            and planning_horizon.strategy_proof_exhaustive
            and local_obviousness is not None
            and local_obviousness.strategy_proof_exhaustive
            and local_obviousness.accepted
            and limit_gate is not None
            and limit_gate.accepted
        )

    @classmethod
    def accepted(
        cls,
        *,
        candidate_id: str,
        level_id: str,
        seed: int,
        difficulty: str,
        strategy_search: StrategySearchResult,
        unique_optimal_proof: UniqueOptimalProof,
        static_policy_search: StaticPolicySearchResult,
        policy_evaluation: PolicyEvaluationReport,
        alternate_successes: AlternateSuccessReport,
        failure_recovery: FailureRecoveryReport,
        planning_horizon: PlanningHorizonReport,
        local_obviousness: LocalObviousnessReport,
        search_limit_gate: SearchLimitRejectionResult,
        details: str | None = None,
        metrics: dict[str, Any] | None = None,
        report_fields: dict[str, Any] | None = None,
    ) -> "StrategyStageResult":
        return cls(
            passed=True,
            code=_ACCEPTED_CODE,
            details=details,
            metrics=dict(metrics or {}),
            report_fields=dict(report_fields or {}),
            candidate_id=candidate_id,
            level_id=level_id,
            seed=seed,
            difficulty=difficulty,
            status="accepted",
            strategy_search=strategy_search,
            unique_optimal_proof=unique_optimal_proof,
            static_policy_search=static_policy_search,
            policy_evaluation=policy_evaluation,
            alternate_successes=alternate_successes,
            failure_recovery=failure_recovery,
            planning_horizon=planning_horizon,
            local_obviousness=local_obviousness,
            search_limit_gate=search_limit_gate,
        )

    @classmethod
    def rejected(
        cls,
        *,
        candidate_id: str,
        level_id: str,
        seed: int,
        difficulty: str,
        rejection_reasons: tuple[str, ...],
        strategy_search: StrategySearchResult | None = None,
        unique_optimal_proof: UniqueOptimalProof | None = None,
        static_policy_search: StaticPolicySearchResult | None = None,
        policy_evaluation: PolicyEvaluationReport | None = None,
        alternate_successes: AlternateSuccessReport | None = None,
        failure_recovery: FailureRecoveryReport | None = None,
        planning_horizon: PlanningHorizonReport | None = None,
        local_obviousness: LocalObviousnessReport | None = None,
        search_limit_gate: SearchLimitRejectionResult | None = None,
        details: str | None = None,
        metrics: dict[str, Any] | None = None,
        report_fields: dict[str, Any] | None = None,
    ) -> "StrategyStageResult":
        reasons = _stable_codes(tuple(rejection_reasons))
        if not reasons:
            raise ValueError("a rejected strategy stage requires rejection reasons")
        return cls(
            passed=False,
            code=reasons[0],
            details=details,
            metrics=dict(metrics or {}),
            report_fields=dict(report_fields or {}),
            candidate_id=candidate_id,
            level_id=level_id,
            seed=seed,
            difficulty=difficulty,
            status="rejected",
            strategy_search=strategy_search,
            unique_optimal_proof=unique_optimal_proof,
            static_policy_search=static_policy_search,
            policy_evaluation=policy_evaluation,
            alternate_successes=alternate_successes,
            failure_recovery=failure_recovery,
            planning_horizon=planning_horizon,
            local_obviousness=local_obviousness,
            search_limit_gate=search_limit_gate,
            rejection_reasons=reasons,
        )

    def to_report_dict(self) -> dict[str, Any]:
        payload = super().to_report_dict()
        search = self.strategy_search
        proof = self.unique_optimal_proof
        static = self.static_policy_search
        policy = self.policy_evaluation
        alternates = self.alternate_successes
        failure_recovery = self.failure_recovery
        planning_horizon = self.planning_horizon
        local_obviousness = self.local_obviousness
        limit_gate = self.search_limit_gate
        payload.update(
            {
                "rejectionReasons": list(self.rejection_reasons),
                "strategySearch": None
                if search is None
                else {
                    "succeeded": search.succeeded,
                    "exhaustive": search.exhaustive,
                    "exploredStateCount": search.explored_state_count,
                    "successfulStrategyCount": len(search.all_successful_strategies),
                    "failureOutcomeCount": len(search.failure_outcomes),
                    "limitReasons": list(search.limit_reasons),
                },
                "uniqueOptimalProof": None
                if proof is None
                else {
                    "accepted": proof.accepted,
                    "exhaustive": proof.exhaustive,
                    "isUnique": proof.is_unique,
                    "equalCostStrategyClassCount": len(
                        proof.equal_cost_strategy_classes
                    ),
                    "rejectionReasons": list(proof.rejection_reasons),
                },
                "staticPolicySearch": None
                if static is None
                else {
                    "acceptedForProduction": static.accepted_for_production,
                    "exhaustive": static.exhaustive,
                    "testedPolicyCount": static.tested_policy_count,
                    "totalPolicyCount": static.total_policy_count,
                    "successfulPolicyCount": len(static.successful_policies),
                    "limitReasons": list(static.limit_reasons),
                },
                "policyEvaluation": None
                if policy is None
                else {
                    "strategyProofExhaustive": policy.strategy_proof_exhaustive,
                    "policies": [
                        {
                            "name": evaluation.policy_name,
                            "runCount": evaluation.run_count,
                            "successRate": evaluation.success_rate,
                        }
                        for evaluation in policy.evaluations
                    ],
                },
                "alternateSuccesses": None
                if alternates is None
                else {
                    "exhaustive": alternates.exhaustive,
                    "classificationCount": len(alternates.classifications),
                    "limitReasons": list(alternates.limit_reasons),
                },
                "failureRecovery": None
                if failure_recovery is None
                else {
                    "exhaustive": failure_recovery.exhaustive,
                    "classificationCount": len(failure_recovery.classifications),
                    "limitReasons": list(failure_recovery.limit_reasons),
                },
                "planningHorizon": None
                if planning_horizon is None
                else {
                    "strategyProofExhaustive": (
                        planning_horizon.strategy_proof_exhaustive
                    ),
                    "decisionCount": len(planning_horizon.decisions),
                    "maximumHorizon": (
                        planning_horizon.maximum_horizon.value
                        if planning_horizon.maximum_horizon is not None
                        else None
                    ),
                },
                "localObviousness": None
                if local_obviousness is None
                else {
                    "accepted": local_obviousness.accepted,
                    "strategyProofExhaustive": (
                        local_obviousness.strategy_proof_exhaustive
                    ),
                    "decisionCount": len(local_obviousness.decisions),
                    "nonObviousDecisionCount": (
                        local_obviousness.non_obvious_decision_count
                    ),
                    "rejectionReasons": list(local_obviousness.rejection_reasons),
                },
                "searchLimitGate": None
                if limit_gate is None
                else {
                    "accepted": limit_gate.accepted,
                    "rejectionReasons": list(limit_gate.rejection_reasons),
                },
            }
        )
        return payload
