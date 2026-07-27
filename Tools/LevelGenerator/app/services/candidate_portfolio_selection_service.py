from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from .candidate_uniqueness_service import CandidateUniquenessService
from .existing_corpus_behavior_comparison_service import (
    ExistingCorpusBehaviorComparisonService,
)


@dataclass(frozen=True)
class PortfolioConstraints:
    """Hard campaign rules and deterministic optimizer bounds."""

    behavior_uniqueness_window: int = 5
    max_same_objective_count_streak: int = 2
    max_fatal_dominated_streak: int = 2
    adaptive_window_size: int = 5
    minimum_adaptive_families: int = 2
    expert_dependency_window_size: int = 3
    minimum_expert_dependency_structures: int = 2
    beam_width: int = 512

    def __post_init__(self) -> None:
        for field_name in (
            "behavior_uniqueness_window",
            "max_same_objective_count_streak",
            "max_fatal_dominated_streak",
            "adaptive_window_size",
            "minimum_adaptive_families",
            "expert_dependency_window_size",
            "minimum_expert_dependency_structures",
            "beam_width",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        if self.minimum_adaptive_families > self.adaptive_window_size:
            raise ValueError("minimum_adaptive_families cannot exceed adaptive_window_size")
        if self.minimum_expert_dependency_structures > self.expert_dependency_window_size:
            raise ValueError(
                "minimum_expert_dependency_structures cannot exceed "
                "expert_dependency_window_size"
            )


@dataclass(frozen=True)
class PortfolioSelection:
    candidate: object
    objective_score: float
    rationale: str
    components: dict[str, float]


@dataclass(frozen=True)
class CandidatePortfolioSelectionResult:
    selections: tuple[PortfolioSelection, ...]
    explored_states: int = 0
    constraint_rejections: tuple[tuple[str, int], ...] = ()

    @property
    def candidates(self) -> list[object]:
        return [selection.candidate for selection in self.selections]

    @property
    def objective_score(self) -> float:
        return round(sum(item.objective_score for item in self.selections), 6)


class PortfolioConstraintFailure(ValueError):
    """A complete campaign could not be formed under its hard constraints."""

    def __init__(
        self,
        message: str,
        *,
        constrained_level_ids: Sequence[str],
        reasons: Mapping[str, int] | None = None,
        explored_states: int = 0,
    ) -> None:
        super().__init__(message)
        self.constrained_level_ids = tuple(dict.fromkeys(constrained_level_ids))
        self.reasons = tuple(sorted((reasons or {}).items()))
        self.explored_states = explored_states


@dataclass(frozen=True)
class _PortfolioState:
    selections: tuple[PortfolioSelection, ...] = ()
    score: float = 0.0

    @property
    def signatures(self) -> tuple[object, ...]:
        return tuple(item.candidate.candidate_signature for item in self.selections)


class CandidatePortfolioSelectionService:
    """Optimize one candidate per slot under campaign-wide hard constraints.

    The bounded beam retains alternate prefixes, so an attractive early choice
    cannot make a later slot impossible as it could in the legacy greedy pass.
    Hard constraints are evaluated before scoring and are never relaxed.
    """

    _MEDIUM_PLUS = frozenset({"medium", "hard", "expert"})

    def __init__(
        self,
        uniqueness_service: CandidateUniquenessService | None = None,
        constraints: PortfolioConstraints | None = None,
        corpus_behavior_service: ExistingCorpusBehaviorComparisonService | None = None,
    ) -> None:
        self.uniqueness_service = uniqueness_service or CandidateUniquenessService()
        self.constraints = constraints or PortfolioConstraints()
        self.corpus_behavior_service = (
            corpus_behavior_service or ExistingCorpusBehaviorComparisonService()
        )

    def select(
        self,
        candidate_pools: Mapping[str, Sequence[object]],
        requested_levels: Sequence[tuple[str, str]],
        *,
        existing_signatures: Iterable[object] = (),
    ) -> CandidatePortfolioSelectionResult:
        if not requested_levels:
            raise ValueError("Portfolio selection requires at least one requested level.")
        level_ids = tuple(level_id for level_id, _ in requested_levels)
        if len(level_ids) != len(set(level_ids)):
            raise ValueError("Portfolio requested level IDs must be unique.")

        production_signatures = tuple(existing_signatures)
        states = (_PortfolioState(),)
        rejection_counts: Counter[str] = Counter()
        explored_states = 0

        for slot_index, (level_id, difficulty) in enumerate(requested_levels):
            eligible = tuple(
                candidate
                for candidate in candidate_pools.get(level_id, ())
                if getattr(candidate, "level_id", None) == level_id
                and str(getattr(candidate, "difficulty", "")).lower()
                == difficulty.lower()
                and getattr(candidate, "candidate_signature", None) is not None
            )
            if not eligible:
                raise PortfolioConstraintFailure(
                    f"Candidate pool has no {difficulty} candidate for {level_id}.",
                    constrained_level_ids=(level_id,),
                    reasons={"portfolio_slot_has_no_candidate": 1},
                    explored_states=explored_states,
                )

            next_states: list[_PortfolioState] = []
            for state in states:
                for candidate in eligible:
                    explored_states += 1
                    code = self._constraint_violation(
                        candidate,
                        state,
                        requested_levels,
                        slot_index,
                        production_signatures,
                    )
                    if code is not None:
                        rejection_counts[code] += 1
                        continue
                    selection = self._rank(
                        candidate,
                        state.signatures,
                        production_signatures,
                    )
                    next_states.append(
                        _PortfolioState(
                            selections=state.selections + (selection,),
                            score=state.score + selection.objective_score,
                        )
                    )

            if not next_states:
                reason_summary = ", ".join(
                    f"{code}={count}" for code, count in sorted(rejection_counts.items())
                ) or "no eligible portfolio state"
                raise PortfolioConstraintFailure(
                    f"Portfolio constraints could not fill {level_id}: {reason_summary}.",
                    constrained_level_ids=(level_id,),
                    reasons=rejection_counts,
                    explored_states=explored_states,
                )

            next_states.sort(key=self._state_key, reverse=True)
            states = tuple(next_states[: self.constraints.beam_width])

        winner = max(states, key=self._state_key)
        return CandidatePortfolioSelectionResult(
            winner.selections,
            explored_states=explored_states,
            constraint_rejections=tuple(sorted(rejection_counts.items())),
        )

    def _constraint_violation(
        self,
        candidate,
        state: _PortfolioState,
        requested_levels: Sequence[tuple[str, str]],
        slot_index: int,
        production_signatures: Sequence[object] = (),
    ) -> str | None:
        signature = candidate.candidate_signature
        corpus_result = self.corpus_behavior_service.check_candidate(
            signature,
            production_signatures,
        )
        if corpus_result.too_similar:
            return "portfolio_existing_corpus_behavior_duplicate"
        previous = state.signatures
        structural_behavior = signature.structural_behavior_signature
        if structural_behavior and any(
            structural_behavior == other.structural_behavior_signature
            for other in previous
        ):
            return "portfolio_structural_behavior_duplicate"
        if previous:
            previous_archetype = previous[-1].blueprint_archetype
            if (
                signature.blueprint_archetype
                and previous_archetype
                and signature.blueprint_archetype == previous_archetype
            ):
                return "portfolio_adjacent_blueprint_archetype"

        behavior_key = self._behavior_key(signature)
        if behavior_key is not None:
            for other in previous[-self.constraints.behavior_uniqueness_window :]:
                if self._behavior_key(other) == behavior_key:
                    return "portfolio_behavior_signature_window"

        if self._has_v3_evidence(signature) and signature.objective_count > 0:
            streak = self._matching_suffix_count(
                previous,
                lambda item: self._has_v3_evidence(item)
                and item.objective_count == signature.objective_count,
            )
            if streak >= self.constraints.max_same_objective_count_streak:
                return "portfolio_objective_count_streak"

        if self._has_v3_evidence(signature) and self._fatal_dominated(signature):
            streak = self._matching_suffix_count(
                previous,
                lambda item: self._has_v3_evidence(item)
                and self._fatal_dominated(item),
            )
            if streak >= self.constraints.max_fatal_dominated_streak:
                return "portfolio_fatal_outcome_streak"

        proposed = previous + (signature,)
        difficulty = requested_levels[slot_index][1].lower()
        if difficulty in self._MEDIUM_PLUS:
            window_size = self.constraints.adaptive_window_size
            if slot_index + 1 >= window_size:
                difficulties = tuple(
                    item[1].lower()
                    for item in requested_levels[slot_index + 1 - window_size : slot_index + 1]
                )
                window = proposed[-window_size:]
                if (
                    all(item in self._MEDIUM_PLUS for item in difficulties)
                    and all(self._has_v3_evidence(item) for item in window)
                ):
                    families = set().union(
                        *(self._adaptive_mechanic_families(item) for item in window)
                    )
                    if len(families) < self.constraints.minimum_adaptive_families:
                        return "portfolio_adaptive_family_window"

        expert_window = self.constraints.expert_dependency_window_size
        if difficulty == "expert" and slot_index + 1 >= expert_window:
            difficulties = tuple(
                item[1].lower()
                for item in requested_levels[slot_index + 1 - expert_window : slot_index + 1]
            )
            window = proposed[-expert_window:]
            if all(item == "expert" for item in difficulties) and all(
                self._has_v3_evidence(item) for item in window
            ):
                structures = {
                    item.dependency_dag_signature
                    for item in window
                    if item.dependency_dag_signature
                }
                if len(structures) < self.constraints.minimum_expert_dependency_structures:
                    return "portfolio_expert_dependency_structure_window"
        return None

    @staticmethod
    def _matching_suffix_count(signatures, predicate) -> int:
        count = 0
        for signature in reversed(signatures):
            if not predicate(signature):
                break
            count += 1
        return count

    @staticmethod
    def _has_v3_evidence(signature) -> bool:
        return bool(
            signature.blueprint_archetype
            and signature.objective_count
            and signature.dependency_dag_signature
        )

    @staticmethod
    def _behavior_key(signature) -> tuple[object, ...] | None:
        fields = (
            signature.dependency_dag_signature,
            signature.adaptive_decision_pattern,
            signature.state_transition_pattern,
            signature.static_policy_proof_signature,
            signature.agent_performance_profile,
            signature.revisit_pattern,
            signature.success_failure_distribution,
            signature.optimal_strategy_signature,
        )
        if not any(fields):
            return None
        return fields

    @staticmethod
    def _adaptive_mechanic_families(signature) -> frozenset[str]:
        families: set[str] = set()
        for transition in signature.state_transition_pattern:
            if len(transition) < 7:
                continue
            if transition[3]:
                families.add("objective_reveal")
            if transition[4]:
                families.add("route_opening")
            if transition[5]:
                families.add("route_closure")
            if transition[6]:
                families.add("one_use_route")
        if signature.revisit_pattern:
            families.add("stateful_revisit")
        for decision in signature.adaptive_decision_pattern:
            dependencies = decision[2] if len(decision) > 2 else ()
            families.update(f"dependency:{item}" for item in dependencies)
        return frozenset(families)

    @staticmethod
    def _fatal_dominated(signature) -> bool:
        distribution = (
            signature.success_failure_distribution
            or signature.failure_outcome_distribution
        )
        if not distribution:
            return False
        nonfatal_words = ("success", "recover", "rejoin", "safe", "slower", "higher_tap")
        fatal = 0
        nonfatal = 0
        for outcome, count in distribution:
            normalized = str(outcome).lower()
            if any(word in normalized for word in nonfatal_words):
                nonfatal += int(count)
            else:
                fatal += int(count)
        return fatal > nonfatal

    def _rank(self, candidate, selected_signatures, existing_signatures) -> PortfolioSelection:
        signature = candidate.candidate_signature
        quality = candidate.quality_score
        individual_quality = min(
            max(float(getattr(quality, "total_score", 0.0)) / 100.0, 0.0), 1.0
        )
        difficulty_fit = min(
            max(float(getattr(quality, "difficulty_fit", 0.0)), 0.0), 1.0
        )
        components = {
            "individualQuality": individual_quality,
            "difficultyFit": difficulty_fit,
            "mechanicProgression": self._mechanic_progression(signature, selected_signatures),
            "blueprintVariety": self._blueprint_variety(signature, selected_signatures),
            "objectiveCountVariety": self._objective_count_variety(signature, selected_signatures),
            "dependencyProgression": self._dependency_progression(signature, selected_signatures),
            "recoveryFailureBalance": self._recovery_balance(signature, selected_signatures),
            "decisionDiversity": self._decision_diversity(signature, selected_signatures),
            "visualDiversity": self._visual_diversity(signature, selected_signatures),
            "runtimePacing": self._runtime_pacing(signature, selected_signatures),
            "productionDistance": 1.0
            - self.corpus_behavior_service.maximum_similarity(
                signature, existing_signatures
            ),
        }
        # Kept as report evidence for callers that consumed the V2 component.
        components["adjacentVariety"] = self._adjacent_variety(
            signature, selected_signatures
        )
        weights = {
            "individualQuality": 0.18,
            "difficultyFit": 0.12,
            "mechanicProgression": 0.10,
            "blueprintVariety": 0.10,
            "objectiveCountVariety": 0.07,
            "dependencyProgression": 0.12,
            "recoveryFailureBalance": 0.08,
            "decisionDiversity": 0.08,
            "visualDiversity": 0.06,
            "runtimePacing": 0.04,
            "productionDistance": 0.05,
        }
        objective = sum(components[name] * weight for name, weight in weights.items())
        strongest = sorted(
            ((name, components[name]) for name in weights),
            key=lambda item: (-item[1], item[0]),
        )[:3]
        rationale = (
            f"Selected with portfolio objective {objective:.4f}; strongest factors: "
            + ", ".join(f"{name}={value:.3f}" for name, value in strongest)
            + ". Hard campaign constraints passed; alternatives were retained and "
            "ranked with deterministic signature and seed tie-breakers."
        )
        return PortfolioSelection(candidate, round(objective, 6), rationale, components)

    def _state_key(self, state: _PortfolioState) -> tuple:
        return (
            round(state.score, 6),
            tuple(self._selection_key(item) for item in state.selections),
        )

    def _selection_key(self, selection: PortfolioSelection) -> tuple:
        candidate = selection.candidate
        signature = candidate.candidate_signature
        return (
            selection.objective_score,
            selection.components["decisionDiversity"],
            selection.components["visualDiversity"],
            float(getattr(candidate.quality_score, "total_score", 0.0)),
            signature.topology_hash,
            signature.layout_hash,
            signature.solution_hash,
            -int(candidate.seed),
        )

    def _maximum_similarity(self, signature, comparison_signatures) -> float:
        return max(
            (
                self.uniqueness_service.similarity_score(signature, other)
                for other in comparison_signatures
            ),
            default=0.0,
        )

    def _visual_diversity(self, signature, selected_signatures) -> float:
        if not selected_signatures:
            return 1.0
        similarities = []
        for other in selected_signatures:
            same_silhouette = (
                signature.layout_silhouette == other.layout_silhouette
                or signature.layout_silhouette == other.mirrored_layout_silhouette
            )
            same_directions = (
                signature.road_direction_histogram == other.road_direction_histogram
            )
            similarities.append(
                (0.65 if same_silhouette else 0.0)
                + (0.35 if same_directions else 0.0)
            )
        return 1.0 - max(similarities, default=0.0)

    def _decision_diversity(self, signature, selected_signatures) -> float:
        if not selected_signatures:
            return 1.0
        similarities = []
        for other in selected_signatures:
            exact_dimensions = (
                signature.decision_dependency_pattern
                == other.decision_dependency_pattern,
                signature.switch_degree_sequence == other.switch_degree_sequence,
                signature.revisit_state_reversal_pattern
                == other.revisit_state_reversal_pattern,
                signature.failure_outcome_distribution
                == other.failure_outcome_distribution,
                signature.package_phase_pattern == other.package_phase_pattern,
                signature.solution_decision_timing_pattern
                == other.solution_decision_timing_pattern,
            )
            similarities.append(sum(exact_dimensions) / len(exact_dimensions))
        return 1.0 - max(similarities, default=0.0)

    def _mechanic_progression(self, signature, selected_signatures) -> float:
        if not selected_signatures:
            return 1.0
        used = {tag for other in selected_signatures for tag in other.mechanic_tags}
        tags = set(signature.mechanic_tags)
        return len(tags - used) / max(len(tags), 1) if tags else 0.5

    @staticmethod
    def _blueprint_variety(signature, selected_signatures) -> float:
        if not selected_signatures or not signature.blueprint_archetype:
            return 1.0
        recent = selected_signatures[-5:]
        matches = sum(
            item.blueprint_archetype == signature.blueprint_archetype for item in recent
        )
        return max(0.0, 1.0 - matches / len(recent))

    @staticmethod
    def _objective_count_variety(signature, selected_signatures) -> float:
        if not selected_signatures or signature.objective_count <= 0:
            return 1.0
        recent = selected_signatures[-3:]
        matches = sum(item.objective_count == signature.objective_count for item in recent)
        return max(0.0, 1.0 - matches / len(recent))

    @staticmethod
    def _dependency_progression(signature, selected_signatures) -> float:
        current = float(signature.decision_dependency_pattern[1]) + len(
            signature.adaptive_decision_pattern
        )
        if not selected_signatures:
            return 1.0
        previous = selected_signatures[-1]
        prior = float(previous.decision_dependency_pattern[1]) + len(
            previous.adaptive_decision_pattern
        )
        current_band = CandidatePortfolioSelectionService._difficulty_index(
            signature.difficulty
        )
        previous_band = CandidatePortfolioSelectionService._difficulty_index(
            previous.difficulty
        )
        if current_band >= previous_band and current < prior:
            return max(0.0, 1.0 - min(1.0, (prior - current) / max(prior, 1.0)))
        return min(1.0, 0.75 + max(0.0, current - prior) * 0.125)

    def _recovery_balance(self, signature, selected_signatures) -> float:
        punitive = 1.0 if self._fatal_dominated(signature) else 0.0
        if not selected_signatures:
            return 1.0 - punitive * 0.35
        previous_punitive = 1.0 if self._fatal_dominated(selected_signatures[-1]) else 0.0
        return 0.25 if punitive and previous_punitive else 1.0

    @staticmethod
    def _runtime_pacing(signature, selected_signatures) -> float:
        if not selected_signatures:
            return 1.0
        previous = selected_signatures[-1]
        tap_delta = abs(signature.required_tap_count - previous.required_tap_count)
        timing_count_delta = abs(
            len(signature.solution_decision_timing_pattern)
            - len(previous.solution_decision_timing_pattern)
        )
        return max(0.0, 1.0 - 0.15 * tap_delta - 0.10 * timing_count_delta)

    def _adjacent_variety(self, signature, selected_signatures) -> float:
        if not selected_signatures:
            return 1.0
        previous = selected_signatures[-1]
        differences = (
            signature.topology_class != previous.topology_class,
            signature.primary_mechanic_tag != previous.primary_mechanic_tag,
            signature.layout_orientation != previous.layout_orientation,
            signature.decision_dependency_pattern
            != previous.decision_dependency_pattern,
        )
        return sum(differences) / len(differences)

    @staticmethod
    def _difficulty_index(difficulty: str) -> int:
        bands = ("tutorial", "easy", "medium", "hard", "expert")
        normalized = str(difficulty).lower()
        return bands.index(normalized) if normalized in bands else -1
