"""Bounded deterministic backtracking over immutable composition states."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable

from ..models.composition_search import (
    CompositionRejectionCount,
    CompositionSearchChoice,
    CompositionSearchResult,
    CompositionSearchTraceEntry,
)
from ..models.composition_state import CompositionState
from .puzzle_composer_service import PuzzleCompositionError


class CompositionBacktrackingService:
    """Try motif, port, and blueprint alternatives in reproducible DFS order."""

    def search(
        self,
        initial_states: CompositionState | Iterable[CompositionState],
        expand: Callable[
            [CompositionState], Iterable[CompositionSearchChoice]
        ],
        *,
        composition_budget: int,
        is_complete: Callable[[CompositionState], bool] | None = None,
        prune: Callable[[CompositionState], Iterable[str]] | None = None,
    ) -> CompositionSearchResult:
        if not callable(expand):
            raise TypeError("expand must be callable")
        if is_complete is not None and not callable(is_complete):
            raise TypeError("is_complete must be callable")
        if prune is not None and not callable(prune):
            raise TypeError("prune must be callable")
        if (
            not isinstance(composition_budget, int)
            or isinstance(composition_budget, bool)
            or composition_budget <= 0
        ):
            raise ValueError("composition_budget must be a positive integer")

        states = self._initial_states(initial_states)
        complete = is_complete or (lambda state: state.is_complete)
        stack: list[tuple[str, object, object | None]] = []
        scheduled_signatures: set[str] = set()
        for state in reversed(states):
            stack.append(("state", state, None))
            scheduled_signatures.add(state.signature)

        visited_signatures: set[str] = set()
        rejection_counts: Counter[str] = Counter()
        trace: list[CompositionSearchTraceEntry] = []
        attempted_branch_count = 0
        expanded_state_count = 0
        budget_exhausted = False

        while stack:
            kind, first, second = stack.pop()
            if kind == "choice":
                parent = first
                choice = second
                assert isinstance(parent, CompositionState)
                assert isinstance(choice, CompositionSearchChoice)
                if attempted_branch_count >= composition_budget:
                    budget_exhausted = True
                    reason = "composition_search_budget_exhausted"
                    rejection_counts[reason] += 1
                    trace.append(
                        CompositionSearchTraceEntry(
                            parent.signature,
                            choice.choice_id,
                            "rejected",
                            reason,
                        )
                    )
                    break
                attempted_branch_count += 1
                try:
                    successor = choice.apply(parent)
                except PuzzleCompositionError as error:
                    reason = str(error) or "composition_branch_rejected"
                    rejection_counts[reason] += 1
                    trace.append(
                        CompositionSearchTraceEntry(
                            parent.signature,
                            choice.choice_id,
                            "rejected",
                            reason,
                        )
                    )
                    continue
                if not isinstance(successor, CompositionState):
                    reason = "composition_search_successor_invalid_type"
                    rejection_counts[reason] += 1
                    trace.append(
                        CompositionSearchTraceEntry(
                            parent.signature,
                            choice.choice_id,
                            "rejected",
                            reason,
                        )
                    )
                    continue
                issues = successor.validate()
                if issues:
                    reason = f"composition_search_successor_invalid:{issues[0]}"
                    rejection_counts[reason] += 1
                    trace.append(
                        CompositionSearchTraceEntry(
                            parent.signature,
                            choice.choice_id,
                            "rejected",
                            reason,
                        )
                    )
                    continue
                pruning_reasons = self._pruning_reasons(prune, successor)
                if pruning_reasons:
                    for reason in pruning_reasons:
                        rejection_counts[reason] += 1
                    trace.append(
                        CompositionSearchTraceEntry(
                            parent.signature,
                            choice.choice_id,
                            "pruned",
                            pruning_reasons[0],
                        )
                    )
                    continue
                signature = successor.signature
                if signature in visited_signatures or signature in scheduled_signatures:
                    reason = "composition_search_duplicate_state"
                    rejection_counts[reason] += 1
                    trace.append(
                        CompositionSearchTraceEntry(
                            parent.signature,
                            choice.choice_id,
                            "rejected",
                            reason,
                        )
                    )
                    continue
                trace.append(
                    CompositionSearchTraceEntry(
                        parent.signature,
                        choice.choice_id,
                        "accepted",
                    )
                )
                stack.append(("state", successor, None))
                scheduled_signatures.add(signature)
                continue

            state = first
            assert isinstance(state, CompositionState)
            scheduled_signatures.discard(state.signature)
            if state.signature in visited_signatures:
                continue
            pruning_reasons = self._pruning_reasons(prune, state)
            if pruning_reasons:
                for reason in pruning_reasons:
                    rejection_counts[reason] += 1
                trace.append(
                    CompositionSearchTraceEntry(
                        state.signature,
                        None,
                        "pruned",
                        pruning_reasons[0],
                    )
                )
                continue
            visited_signatures.add(state.signature)
            if complete(state):
                return self._result(
                    "completed",
                    state,
                    attempted_branch_count,
                    expanded_state_count,
                    visited_signatures,
                    rejection_counts,
                    trace,
                )

            expanded_state_count += 1
            try:
                choices = tuple(expand(state))
            except PuzzleCompositionError as error:
                reason = str(error) or "composition_search_expansion_rejected"
                rejection_counts[reason] += 1
                trace.append(
                    CompositionSearchTraceEntry(
                        state.signature,
                        None,
                        "dead_end",
                        reason,
                    )
                )
                continue
            if any(not isinstance(choice, CompositionSearchChoice) for choice in choices):
                raise TypeError("expand must return CompositionSearchChoice values")
            ordered = tuple(sorted(choices, key=lambda choice: choice.sort_key))
            choice_ids = tuple(choice.choice_id for choice in ordered)
            if len(choice_ids) != len(set(choice_ids)):
                raise ValueError("expand returned duplicate choice_id values")
            if not ordered:
                reason = "composition_search_dead_end"
                rejection_counts[reason] += 1
                trace.append(
                    CompositionSearchTraceEntry(
                        state.signature,
                        None,
                        "dead_end",
                        reason,
                    )
                )
                continue

            # Reversed push preserves the documented ascending retry order.
            for choice in reversed(ordered):
                stack.append(("choice", state, choice))

        return self._result(
            "budget_exhausted" if budget_exhausted else "failed",
            None,
            attempted_branch_count,
            expanded_state_count,
            visited_signatures,
            rejection_counts,
            trace,
        )

    @staticmethod
    def _initial_states(
        values: CompositionState | Iterable[CompositionState],
    ) -> tuple[CompositionState, ...]:
        states = (values,) if isinstance(values, CompositionState) else tuple(values)
        if not states:
            raise ValueError("initial_states must not be empty")
        for state in states:
            if not isinstance(state, CompositionState):
                raise TypeError("initial_states must contain CompositionState values")
            issues = state.validate()
            if issues:
                raise ValueError(f"initial composition state is invalid: {issues[0]}")
        ordered = tuple(
            sorted(states, key=lambda state: (state.blueprint_id, state.signature))
        )
        signatures = tuple(state.signature for state in ordered)
        if len(signatures) != len(set(signatures)):
            raise ValueError("initial_states must be unique")
        return ordered

    @staticmethod
    def _pruning_reasons(
        prune: Callable[[CompositionState], Iterable[str]] | None,
        state: CompositionState,
    ) -> tuple[str, ...]:
        if prune is None:
            return ()
        reasons = tuple(prune(state))
        if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
            raise TypeError("prune must return non-empty string reason codes")
        return tuple(sorted(set(reason.strip() for reason in reasons)))

    @staticmethod
    def _result(
        status: str,
        solution: CompositionState | None,
        attempted_branch_count: int,
        expanded_state_count: int,
        visited_signatures: set[str],
        rejection_counts: Counter[str],
        trace: list[CompositionSearchTraceEntry],
    ) -> CompositionSearchResult:
        return CompositionSearchResult(
            status=status,
            solution_state=solution,
            attempted_branch_count=attempted_branch_count,
            expanded_state_count=expanded_state_count,
            visited_state_count=len(visited_signatures),
            rejection_counts=tuple(
                CompositionRejectionCount(reason, count)
                for reason, count in sorted(rejection_counts.items())
            ),
            trace=tuple(trace),
        )


# Discoverable alias matching the broader architecture terminology.
CompositionSearchService = CompositionBacktrackingService
