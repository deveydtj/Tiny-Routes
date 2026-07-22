"""Targeted, budgeted backtracking for complete campaign portfolios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..models.candidate_pool import CampaignCandidatePoolResult, CandidatePoolRequest
from .candidate_portfolio_selection_service import (
    CandidatePortfolioSelectionResult,
    CandidatePortfolioSelectionService,
    PortfolioConstraintFailure,
)


@dataclass(frozen=True)
class PortfolioBacktrackingConfig:
    max_rounds: int = 3
    additional_candidates_per_slot: int = 1
    max_attempts_per_slot_per_round: int = 4
    global_attempt_budget: int = 24

    def __post_init__(self) -> None:
        for field_name in (
            "max_rounds",
            "additional_candidates_per_slot",
            "max_attempts_per_slot_per_round",
            "global_attempt_budget",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")


@dataclass(frozen=True)
class PortfolioExpansionRecord:
    round_index: int
    constrained_level_ids: tuple[str, ...]
    attempts_added: int
    candidates_added: int
    trigger_reasons: tuple[tuple[str, int], ...]

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "roundIndex": self.round_index,
            "constrainedLevelIDs": list(self.constrained_level_ids),
            "attemptsAdded": self.attempts_added,
            "candidatesAdded": self.candidates_added,
            "triggerReasons": dict(self.trigger_reasons),
        }


@dataclass(frozen=True)
class CampaignPortfolioResult:
    selection: CandidatePortfolioSelectionResult
    candidate_pools: CampaignCandidatePoolResult
    expansions: tuple[PortfolioExpansionRecord, ...] = ()

    @property
    def candidates(self) -> list[object]:
        return self.selection.candidates

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "complete": True,
            "portfolioObjectiveScore": self.selection.objective_score,
            "exploredStates": self.selection.explored_states,
            "constraintRejections": dict(self.selection.constraint_rejections),
            "selectedCandidateIDs": [
                f"{candidate.level_id}:{candidate.seed}" for candidate in self.candidates
            ],
            "expansions": [item.to_report_dict() for item in self.expansions],
        }


class PortfolioBacktrackingFailure(ValueError):
    def __init__(
        self,
        message: str,
        *,
        constrained_level_ids: tuple[str, ...],
        expansions: tuple[PortfolioExpansionRecord, ...],
    ) -> None:
        super().__init__(message)
        self.constrained_level_ids = constrained_level_ids
        self.expansions = expansions


class CampaignPortfolioService:
    """Select a full campaign and replenish only slots that block completion."""

    def __init__(
        self,
        candidate_pool_service,
        selection_service: CandidatePortfolioSelectionService | None = None,
    ) -> None:
        if not callable(getattr(candidate_pool_service, "expand", None)):
            raise TypeError("candidate_pool_service must expose expand(...) ")
        self.candidate_pool_service = candidate_pool_service
        self.selection_service = selection_service or CandidatePortfolioSelectionService()

    def select_with_backtracking(
        self,
        pool_result: CampaignCandidatePoolResult,
        pool_request: CandidatePoolRequest,
        *,
        existing_signatures: Iterable[object] = (),
        config: PortfolioBacktrackingConfig | None = None,
    ) -> CampaignPortfolioResult:
        if not isinstance(pool_result, CampaignCandidatePoolResult):
            raise TypeError("pool_result must be a CampaignCandidatePoolResult")
        if not isinstance(pool_request, CandidatePoolRequest):
            raise TypeError("pool_request must be a CandidatePoolRequest")
        resolved = config or PortfolioBacktrackingConfig()
        production_signatures = tuple(existing_signatures)
        requested_levels = tuple(
            (slot.level_id, slot.difficulty) for slot in pool_request.slots
        )
        current = pool_result
        expansions: list[PortfolioExpansionRecord] = []
        remaining_budget = resolved.global_attempt_budget
        last_constrained: tuple[str, ...] = current.constrained_level_ids

        for round_index in range(resolved.max_rounds + 1):
            failure_reasons: tuple[tuple[str, int], ...] = ()
            if current.complete:
                try:
                    selection = self.selection_service.select(
                        current.candidate_pools,
                        requested_levels,
                        existing_signatures=production_signatures,
                    )
                except PortfolioConstraintFailure as error:
                    last_constrained = error.constrained_level_ids
                    failure_reasons = error.reasons
                else:
                    return CampaignPortfolioResult(
                        selection=selection,
                        candidate_pools=current,
                        expansions=tuple(expansions),
                    )
            else:
                last_constrained = current.constrained_level_ids
                failure_reasons = (("candidate_pool_shortfall", len(last_constrained)),)

            if round_index >= resolved.max_rounds or remaining_budget <= 0:
                break
            before_attempts = len(current.attempts)
            before_candidates = sum(len(pool.candidates) for pool in current.pools)
            expanded = self.candidate_pool_service.expand(
                current,
                pool_request,
                last_constrained,
                additional_candidates_per_slot=resolved.additional_candidates_per_slot,
                max_additional_attempts_per_slot=(
                    resolved.max_attempts_per_slot_per_round
                ),
                max_total_attempts=remaining_budget,
            )
            attempts_added = len(expanded.attempts) - before_attempts
            candidates_added = (
                sum(len(pool.candidates) for pool in expanded.pools)
                - before_candidates
            )
            remaining_budget -= attempts_added
            expansions.append(
                PortfolioExpansionRecord(
                    round_index=round_index + 1,
                    constrained_level_ids=last_constrained,
                    attempts_added=attempts_added,
                    candidates_added=candidates_added,
                    trigger_reasons=failure_reasons,
                )
            )
            current = expanded
            if attempts_added == 0:
                break

        levels = ", ".join(last_constrained) or "unknown slots"
        raise PortfolioBacktrackingFailure(
            "Portfolio backtracking exhausted its declared budget without a complete "
            f"campaign; constrained slots: {levels}.",
            constrained_level_ids=last_constrained,
            expansions=tuple(expansions),
        )
