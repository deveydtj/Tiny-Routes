"""Campaign-wide V3 candidate-pool requests and report evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .generated_level import GeneratedLevel


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


@dataclass(frozen=True)
class CandidatePoolSlot:
    """One requested campaign position, before portfolio selection."""

    level_id: str
    difficulty: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "level_id", _identifier(self.level_id, "level_id"))
        object.__setattr__(
            self,
            "difficulty",
            _identifier(self.difficulty, "difficulty").lower(),
        )


@dataclass(frozen=True)
class CandidatePoolRequest:
    """Deterministic bounds for building every requested slot in waves."""

    slots: tuple[CandidatePoolSlot, ...]
    candidates_per_slot: int
    max_attempts_per_slot: int
    wave_size: int = 1
    base_seed: int = 0
    max_workers: int = 1
    global_attempt_budget: int | None = None

    def __post_init__(self) -> None:
        slots = tuple(self.slots)
        if not slots:
            raise ValueError("candidate pool request requires at least one slot")
        if any(not isinstance(slot, CandidatePoolSlot) for slot in slots):
            raise TypeError("slots must contain CandidatePoolSlot values")
        level_ids = tuple(slot.level_id for slot in slots)
        if len(level_ids) != len(set(level_ids)):
            raise ValueError("candidate pool slot level IDs must be unique")
        if (
            not isinstance(self.candidates_per_slot, int)
            or isinstance(self.candidates_per_slot, bool)
            or self.candidates_per_slot < 2
        ):
            raise ValueError("candidates_per_slot must be at least two")
        for field_name in ("max_attempts_per_slot", "wave_size", "max_workers"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        if self.max_attempts_per_slot < self.candidates_per_slot:
            raise ValueError(
                "max_attempts_per_slot cannot be smaller than candidates_per_slot"
            )
        if not isinstance(self.base_seed, int) or isinstance(self.base_seed, bool):
            raise ValueError("base_seed must be an integer")
        if self.global_attempt_budget is not None and (
            not isinstance(self.global_attempt_budget, int)
            or isinstance(self.global_attempt_budget, bool)
            or self.global_attempt_budget <= 0
        ):
            raise ValueError("global_attempt_budget must be a positive integer")
        object.__setattr__(self, "slots", slots)

    @property
    def resolved_global_attempt_budget(self) -> int:
        if self.global_attempt_budget is not None:
            return self.global_attempt_budget
        # Preserve the existing targeted portfolio-backtracking allowance while
        # placing initial generation and later replenishment under one cap.
        return len(self.slots) * self.max_attempts_per_slot + 24


@dataclass(frozen=True)
class AttemptBudgetAllocation:
    """Deterministic evidence for one wave's attempt allocation."""

    wave_index: int
    level_id: str
    attempts_allocated: int
    reason: str
    remaining_budget_after: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "level_id", _identifier(self.level_id, "level_id"))
        object.__setattr__(self, "reason", _identifier(self.reason, "reason"))
        for field_name in (
            "wave_index",
            "attempts_allocated",
            "remaining_budget_after",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.attempts_allocated == 0:
            raise ValueError("attempts_allocated must be positive")

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "waveIndex": self.wave_index,
            "levelID": self.level_id,
            "attemptsAllocated": self.attempts_allocated,
            "reason": self.reason,
            "remainingBudgetAfter": self.remaining_budget_after,
        }


@dataclass(frozen=True)
class GlobalAttemptBudgetReport:
    """Campaign-wide cap, usage, and deterministic allocation rationale."""

    maximum_attempts: int
    attempts_used: int
    attempts_per_slot: tuple[tuple[str, int], ...]
    allocation_changes: tuple[AttemptBudgetAllocation, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("maximum_attempts", "attempts_used"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.maximum_attempts <= 0:
            raise ValueError("maximum_attempts must be positive")
        if self.attempts_used > self.maximum_attempts:
            raise ValueError("attempts_used cannot exceed maximum_attempts")
        per_slot = tuple(self.attempts_per_slot)
        if any(
            not isinstance(level_id, str)
            or not level_id.strip()
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
            for level_id, count in per_slot
        ):
            raise ValueError("attempts_per_slot must contain IDs and non-negative counts")
        if len({level_id for level_id, _ in per_slot}) != len(per_slot):
            raise ValueError("attempts_per_slot level IDs must be unique")
        if sum(count for _, count in per_slot) != self.attempts_used:
            raise ValueError("attempts_per_slot must sum to attempts_used")
        changes = tuple(self.allocation_changes)
        if any(not isinstance(item, AttemptBudgetAllocation) for item in changes):
            raise TypeError("allocation_changes must contain AttemptBudgetAllocation values")
        object.__setattr__(self, "attempts_per_slot", per_slot)
        object.__setattr__(self, "allocation_changes", changes)

    @property
    def remaining_attempts(self) -> int:
        return self.maximum_attempts - self.attempts_used

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "maximumAttempts": self.maximum_attempts,
            "attemptsUsed": self.attempts_used,
            "remainingAttempts": self.remaining_attempts,
            "attemptsPerSlot": dict(self.attempts_per_slot),
            "allocationChanges": [
                item.to_report_dict() for item in self.allocation_changes
            ],
        }


@dataclass(frozen=True)
class CandidatePoolAttempt:
    """Compact evidence retained for one V3 pipeline attempt."""

    candidate_id: str
    level_id: str
    difficulty: str
    seed: int
    attempt_index: int
    wave_index: int
    passed: bool
    terminal_stage: str
    code: str

    def __post_init__(self) -> None:
        for field_name in (
            "candidate_id",
            "level_id",
            "difficulty",
            "terminal_stage",
            "code",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifier(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "difficulty", self.difficulty.lower())
        for field_name in ("attempt_index", "wave_index"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ValueError("seed must be an integer")
        if not isinstance(self.passed, bool):
            raise ValueError("passed must be a Boolean")

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "candidateID": self.candidate_id,
            "levelID": self.level_id,
            "difficulty": self.difficulty,
            "seed": self.seed,
            "attemptIndex": self.attempt_index,
            "waveIndex": self.wave_index,
            "passed": self.passed,
            "terminalStage": self.terminal_stage,
            "code": self.code,
        }


@dataclass(frozen=True)
class CandidateSlotPool:
    """All accepted candidates retained for one campaign slot."""

    slot: CandidatePoolSlot
    target_count: int
    candidates: tuple[GeneratedLevel, ...]
    attempted_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.slot, CandidatePoolSlot):
            raise TypeError("slot must be a CandidatePoolSlot")
        if not isinstance(self.target_count, int) or self.target_count < 2:
            raise ValueError("target_count must be at least two")
        candidates = tuple(self.candidates)
        for candidate in candidates:
            if not isinstance(candidate, GeneratedLevel):
                raise TypeError("candidates must contain GeneratedLevel values")
            if candidate.level_id != self.slot.level_id:
                raise ValueError("candidate level ID must match its pool slot")
            if candidate.difficulty.lower() != self.slot.difficulty:
                raise ValueError("candidate difficulty must match its pool slot")
            if candidate.candidate_signature is None:
                raise ValueError("pooled candidates require complete signatures")
        if len(candidates) > self.target_count:
            raise ValueError("candidate pool cannot exceed its target count")
        if not isinstance(self.attempted_count, int) or self.attempted_count < len(candidates):
            raise ValueError("attempted_count cannot be smaller than accepted count")
        object.__setattr__(self, "candidates", candidates)

    @property
    def complete(self) -> bool:
        return len(self.candidates) == self.target_count

    @property
    def shortfall(self) -> int:
        return self.target_count - len(self.candidates)

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "levelID": self.slot.level_id,
            "difficulty": self.slot.difficulty,
            "targetCount": self.target_count,
            "acceptedCount": len(self.candidates),
            "attemptedCount": self.attempted_count,
            "shortfall": self.shortfall,
            "complete": self.complete,
            "candidateIDs": [
                f"{candidate.level_id}:{candidate.seed}" for candidate in self.candidates
            ],
        }


@dataclass(frozen=True)
class CampaignCandidatePoolResult:
    """Complete or bounded-incomplete pools for a whole campaign request."""

    pools: tuple[CandidateSlotPool, ...]
    attempts: tuple[CandidatePoolAttempt, ...]
    waves_completed: int
    accepted_pipeline_results: tuple[object, ...] = ()
    attempt_diagnostics: tuple[Mapping[str, Any], ...] = ()
    attempt_budget: GlobalAttemptBudgetReport | None = None

    def __post_init__(self) -> None:
        pools = tuple(self.pools)
        attempts = tuple(self.attempts)
        pipeline_results = tuple(self.accepted_pipeline_results)
        diagnostics = tuple(self.attempt_diagnostics)
        if not pools:
            raise ValueError("campaign candidate pools cannot be empty")
        if any(not isinstance(pool, CandidateSlotPool) for pool in pools):
            raise TypeError("pools must contain CandidateSlotPool values")
        if any(not isinstance(attempt, CandidatePoolAttempt) for attempt in attempts):
            raise TypeError("attempts must contain CandidatePoolAttempt values")
        if not isinstance(self.waves_completed, int) or self.waves_completed < 1:
            raise ValueError("waves_completed must be a positive integer")
        if any(not isinstance(item, Mapping) for item in diagnostics):
            raise TypeError("attempt_diagnostics must contain mapping values")
        if diagnostics and len(diagnostics) != len(attempts):
            raise ValueError("attempt_diagnostics must match the attempt count")
        if self.attempt_budget is not None:
            if not isinstance(self.attempt_budget, GlobalAttemptBudgetReport):
                raise TypeError("attempt_budget must be a GlobalAttemptBudgetReport")
            if self.attempt_budget.attempts_used != len(attempts):
                raise ValueError("attempt budget usage must match the attempt count")
        object.__setattr__(self, "pools", pools)
        object.__setattr__(self, "attempts", attempts)
        object.__setattr__(self, "accepted_pipeline_results", pipeline_results)
        object.__setattr__(
            self,
            "attempt_diagnostics",
            tuple(dict(item) for item in diagnostics),
        )

    @property
    def complete(self) -> bool:
        return all(pool.complete for pool in self.pools)

    @property
    def candidate_pools(self) -> dict[str, tuple[GeneratedLevel, ...]]:
        return {pool.slot.level_id: pool.candidates for pool in self.pools}

    @property
    def constrained_level_ids(self) -> tuple[str, ...]:
        return tuple(pool.slot.level_id for pool in self.pools if not pool.complete)

    def pipeline_result_for(self, candidate: GeneratedLevel) -> object:
        """Return the proof-bearing pipeline result for an accepted candidate."""

        matches = [
            result
            for result in self.accepted_pipeline_results
            if getattr(result, "candidate", None) is candidate
            or (
                getattr(getattr(result, "candidate", None), "level_id", None)
                == candidate.level_id
                and getattr(getattr(result, "candidate", None), "seed", None)
                == candidate.seed
            )
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one retained pipeline result for {candidate.level_id}:"
                f"{candidate.seed}, found {len(matches)}"
            )
        return matches[0]

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "complete": self.complete,
            "wavesCompleted": self.waves_completed,
            "constrainedLevelIDs": list(self.constrained_level_ids),
            "pools": [pool.to_report_dict() for pool in self.pools],
            "attempts": [attempt.to_report_dict() for attempt in self.attempts],
            "attemptDiagnosticCount": len(self.attempt_diagnostics),
            "attemptBudget": (
                self.attempt_budget.to_report_dict() if self.attempt_budget else None
            ),
        }
