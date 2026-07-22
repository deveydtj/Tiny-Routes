"""Campaign-wide V3 candidate-pool requests and report evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
        for field_name in ("max_attempts_per_slot", "wave_size"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        if self.max_attempts_per_slot < self.candidates_per_slot:
            raise ValueError(
                "max_attempts_per_slot cannot be smaller than candidates_per_slot"
            )
        if not isinstance(self.base_seed, int) or isinstance(self.base_seed, bool):
            raise ValueError("base_seed must be an integer")
        object.__setattr__(self, "slots", slots)


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

    def __post_init__(self) -> None:
        pools = tuple(self.pools)
        attempts = tuple(self.attempts)
        pipeline_results = tuple(self.accepted_pipeline_results)
        if not pools:
            raise ValueError("campaign candidate pools cannot be empty")
        if any(not isinstance(pool, CandidateSlotPool) for pool in pools):
            raise TypeError("pools must contain CandidateSlotPool values")
        if any(not isinstance(attempt, CandidatePoolAttempt) for attempt in attempts):
            raise TypeError("attempts must contain CandidatePoolAttempt values")
        if not isinstance(self.waves_completed, int) or self.waves_completed < 1:
            raise ValueError("waves_completed must be a positive integer")
        object.__setattr__(self, "pools", pools)
        object.__setattr__(self, "attempts", attempts)
        object.__setattr__(self, "accepted_pipeline_results", pipeline_results)

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
        }
