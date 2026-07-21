"""Production gates for rapid input bursts and post-state-change readability."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from tiny_routes_core.models import LevelDocument

from ..models.puzzle_experience_target import PuzzleExperienceTarget
from ..models.runtime_solution_search import RuntimeDecisionTimingDiagnostic
from ..models.runtime_timing_accessibility import (
    RapidMultiTapEncounter,
    RuntimeTimingAccessibilityReport,
    StateChangeVisibilityEvidence,
)


class RuntimeTimingAccessibilityService:
    """Apply fail-closed timing rules to an already verified runtime schedule."""

    tolerance = 1e-9

    def evaluate(
        self,
        level: LevelDocument,
        diagnostics: Iterable[RuntimeDecisionTimingDiagnostic],
        replay_result,
        target: PuzzleExperienceTarget,
    ) -> RuntimeTimingAccessibilityReport:
        diagnostics = tuple(diagnostics)
        rapid = self._rapid_multi_tap_evidence(diagnostics, target)
        visibility = self._state_change_visibility_evidence(
            level,
            diagnostics,
            replay_result,
            target,
        )
        reasons: list[str] = []
        if (
            len(rapid) > target.rapid_multi_tap_encounter_cap
            or any(
                not item.within_per_encounter_limit
                or not item.preserves_safety_margin
                for item in rapid
            )
        ):
            reasons.append("required_tap_burst_exceeds_target")
        if any(not item.passed for item in visibility):
            reasons.append("state_change_not_visible_before_decision")
        return RuntimeTimingAccessibilityReport(
            difficulty=target.difficulty,
            passed=not reasons,
            rapid_multi_tap_encounter_cap=target.rapid_multi_tap_encounter_cap,
            maximum_taps_per_burst=target.maximum_taps_per_rapid_burst,
            minimum_state_change_visibility_seconds=(
                target.minimum_state_change_visibility_seconds
            ),
            rapid_multi_tap_encounters=rapid,
            state_change_visibility=visibility,
            rejection_reasons=tuple(reasons),
        )

    def _rapid_multi_tap_evidence(
        self,
        diagnostics: tuple[RuntimeDecisionTimingDiagnostic, ...],
        target: PuzzleExperienceTarget,
    ) -> tuple[RapidMultiTapEncounter, ...]:
        evidence: list[RapidMultiTapEncounter] = []
        for diagnostic in diagnostics:
            if diagnostic.rotation_count <= 1:
                continue
            tap_times = tuple(float(value) for value in diagnostic.chosen_tap_seconds)
            open_time = diagnostic.window_open_seconds
            close_time = diagnostic.window_close_seconds
            complete_schedule = len(tap_times) == diagnostic.rotation_count
            if complete_schedule and open_time is not None and close_time is not None:
                opening_margin = tap_times[0] - float(open_time)
                closing_margin = float(close_time) - tap_times[-1]
                burst_duration = tap_times[-1] - tap_times[0]
            else:
                opening_margin = 0.0
                closing_margin = 0.0
                burst_duration = 0.0
            required_margin = float(diagnostic.safety_margin_seconds)
            preserves_margin = (
                complete_schedule
                and open_time is not None
                and close_time is not None
                and opening_margin + self.tolerance >= required_margin
                and closing_margin + self.tolerance >= required_margin
            )
            evidence.append(
                RapidMultiTapEncounter(
                    node_id=diagnostic.node_id,
                    visit_index=diagnostic.visit_index,
                    required_tap_count=diagnostic.rotation_count,
                    tap_times_seconds=tap_times,
                    burst_duration_seconds=round(max(0.0, burst_duration), 9),
                    opening_safety_margin_seconds=round(max(0.0, opening_margin), 9),
                    closing_safety_margin_seconds=round(max(0.0, closing_margin), 9),
                    required_safety_margin_seconds=round(required_margin, 9),
                    within_per_encounter_limit=(
                        diagnostic.rotation_count
                        <= target.maximum_taps_per_rapid_burst
                    ),
                    preserves_safety_margin=preserves_margin,
                )
            )
        return tuple(evidence)

    def _state_change_visibility_evidence(
        self,
        level: LevelDocument,
        diagnostics: tuple[RuntimeDecisionTimingDiagnostic, ...],
        replay_result,
        target: PuzzleExperienceTarget,
    ) -> tuple[StateChangeVisibilityEvidence, ...]:
        required_decisions = tuple(
            diagnostic
            for diagnostic in diagnostics
            if diagnostic.rotation_count > 0
            and diagnostic.window_open_seconds is not None
        )
        if not required_decisions or replay_result is None:
            return ()

        evidence: list[StateChangeVisibilityEvidence] = []
        objective_events_by_time: dict[float, list[object]] = defaultdict(list)
        for event in getattr(replay_result, "events", ()):
            if event.kind == "objective_completed":
                objective_events_by_time[round(float(event.time_seconds), 9)].append(event)

        for change_time, events in sorted(objective_events_by_time.items()):
            completed_ids = tuple(
                event.objective_id
                for event in sorted(
                    events,
                    key=lambda item: (
                        item.objective_index if item.objective_index is not None else -1,
                        item.objective_id or "",
                    ),
                )
                if event.objective_id is not None
            )
            next_decision = self._next_decision(
                required_decisions,
                change_time,
                required_completed_ids=completed_ids,
            )
            if next_decision is None:
                continue
            opened, closed = self._objective_availability_changes(level, events)
            evidence.append(
                self._visibility_item(
                    change_time,
                    next_decision,
                    target,
                    completed_objective_ids=completed_ids,
                    opened_edge_ids=opened,
                    closed_edge_ids=closed,
                )
            )

        prior_consumed: set[str] = set()
        begin_events_by_edge: dict[str, list[float]] = defaultdict(list)
        for event in getattr(replay_result, "events", ()):
            if event.kind == "begin_edge" and event.edge_id is not None:
                begin_events_by_edge[event.edge_id].append(float(event.time_seconds))
        for diagnostic in diagnostics:
            current_consumed = set(diagnostic.consumed_edge_ids)
            newly_consumed = tuple(sorted(current_consumed - prior_consumed))
            prior_consumed.update(current_consumed)
            for edge_id in newly_consumed:
                change_times = [
                    time
                    for time in begin_events_by_edge.get(edge_id, ())
                    if diagnostic.window_open_seconds is not None
                    and time <= float(diagnostic.window_open_seconds) + self.tolerance
                ]
                if not change_times:
                    continue
                change_time = max(change_times)
                next_decision = self._next_decision(required_decisions, change_time)
                if next_decision is None:
                    continue
                evidence.append(
                    self._visibility_item(
                        change_time,
                        next_decision,
                        target,
                        consumed_edge_ids=(edge_id,),
                    )
                )

        unique: dict[tuple[object, ...], StateChangeVisibilityEvidence] = {}
        for item in evidence:
            key = (
                item.state_change_time_seconds,
                item.next_decision_node_id,
                item.next_decision_visit_index,
                item.completed_objective_ids,
                item.opened_edge_ids,
                item.closed_edge_ids,
                item.consumed_edge_ids,
            )
            unique[key] = item
        return tuple(
            unique[key]
            for key in sorted(
                unique,
                key=lambda value: (
                    float(value[0]),
                    str(value[1]),
                    int(value[2]),
                    value[3:],
                ),
            )
        )

    def _visibility_item(
        self,
        change_time: float,
        decision: RuntimeDecisionTimingDiagnostic,
        target: PuzzleExperienceTarget,
        *,
        completed_objective_ids: tuple[str, ...] = (),
        opened_edge_ids: tuple[str, ...] = (),
        closed_edge_ids: tuple[str, ...] = (),
        consumed_edge_ids: tuple[str, ...] = (),
    ) -> StateChangeVisibilityEvidence:
        assert decision.window_open_seconds is not None
        visibility = float(decision.window_open_seconds) - float(change_time)
        required = target.minimum_state_change_visibility_seconds
        return StateChangeVisibilityEvidence(
            state_change_time_seconds=round(float(change_time), 9),
            next_window_open_seconds=round(float(decision.window_open_seconds), 9),
            visibility_seconds=round(max(0.0, visibility), 9),
            required_visibility_seconds=round(required, 9),
            next_decision_node_id=decision.node_id,
            next_decision_visit_index=decision.visit_index,
            completed_objective_ids=completed_objective_ids,
            opened_edge_ids=opened_edge_ids,
            closed_edge_ids=closed_edge_ids,
            consumed_edge_ids=consumed_edge_ids,
            active_objective_id=decision.active_objective_id,
            passed=visibility + self.tolerance >= required,
        )

    def _next_decision(
        self,
        decisions: tuple[RuntimeDecisionTimingDiagnostic, ...],
        change_time: float,
        *,
        required_completed_ids: tuple[str, ...] = (),
    ) -> RuntimeDecisionTimingDiagnostic | None:
        required = set(required_completed_ids)
        return next(
            (
                decision
                for decision in decisions
                if decision.window_open_seconds is not None
                and float(decision.window_open_seconds) + self.tolerance >= change_time
                and required <= set(decision.completed_objective_ids)
            ),
            None,
        )

    @staticmethod
    def _objective_availability_changes(
        level: LevelDocument,
        events: list[object],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        indices = sorted(
            event.objective_index
            for event in events
            if event.objective_index is not None
        )
        if not indices:
            return (), ()
        objectives = sorted(
            level.effective_objectives,
            key=lambda objective: objective.sequenceIndex,
        )
        before_index = indices[0]
        after_index = indices[-1] + 1
        before_completed = {
            objective.id for objective in objectives if objective.sequenceIndex < before_index
        }
        after_completed = {
            objective.id for objective in objectives if objective.sequenceIndex < after_index
        }
        opened: list[str] = []
        closed: list[str] = []
        for edge in level.graph.edges:
            rule = level.effective_edge_availability_rule(edge)
            before = rule.allows(before_completed, before_index, usage_count=0)
            after = rule.allows(after_completed, after_index, usage_count=0)
            if after and not before:
                opened.append(edge.id)
            elif before and not after:
                closed.append(edge.id)
        return tuple(sorted(opened)), tuple(sorted(closed))


RuntimeTimingQualityService = RuntimeTimingAccessibilityService
