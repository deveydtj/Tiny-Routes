"""Translate repeated V3 rejection evidence into safe blueprint retry changes."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import Any

from ..models.search_planning import (
    BlueprintPlanningConstraints,
    RejectionFeedbackAdjustment,
    RejectionFeedbackEvent,
    RejectionFeedbackPlan,
)
from .puzzle_blueprint_service import PuzzleBlueprintService
from .v3_candidate_pipeline_coordinator import V3CandidatePipelineResult


class RejectionFeedbackPlannerService:
    """Apply deterministic retry feedback only after a stable cause repeats."""

    def __init__(
        self,
        *,
        repetition_threshold: int = 3,
        supported_archetypes: tuple[str, ...] | None = None,
    ) -> None:
        if (
            not isinstance(repetition_threshold, int)
            or isinstance(repetition_threshold, bool)
            or repetition_threshold <= 1
        ):
            raise ValueError("repetition_threshold must be greater than one")
        self.repetition_threshold = repetition_threshold
        archetypes = supported_archetypes or PuzzleBlueprintService.supported_archetypes
        normalized = tuple(str(value).strip().lower() for value in archetypes)
        if not normalized or any(not value for value in normalized):
            raise ValueError("supported_archetypes cannot be empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("supported_archetypes must be unique")
        self.supported_archetypes = normalized

    def plan(
        self,
        events: tuple[RejectionFeedbackEvent, ...],
        *,
        current: BlueprintPlanningConstraints | None = None,
        previous_adjustments: tuple[RejectionFeedbackAdjustment, ...] = (),
    ) -> RejectionFeedbackPlan:
        history = tuple(events)
        if any(not isinstance(item, RejectionFeedbackEvent) for item in history):
            raise TypeError("events must contain RejectionFeedbackEvent values")
        constraints = current or BlueprintPlanningConstraints()
        if not isinstance(constraints, BlueprintPlanningConstraints):
            raise TypeError("current must be BlueprintPlanningConstraints")
        prior = tuple(previous_adjustments)
        if any(not isinstance(item, RejectionFeedbackAdjustment) for item in prior):
            raise TypeError("previous_adjustments contains an invalid value")

        counts = Counter(item.code for item in history)
        adjustments: list[RejectionFeedbackAdjustment] = []
        already_recorded = {item.record_key for item in prior}
        first_index = {code: next(i for i, event in enumerate(history) if event.code == code) for code in counts}
        repeated_codes = sorted(
            (code for code, count in counts.items() if count >= self.repetition_threshold),
            key=lambda code: (-counts[code], first_index[code], code),
        )

        for code in repeated_codes:
            count = counts[code]
            milestone = (count // self.repetition_threshold) * self.repetition_threshold
            matching = tuple(item for item in history if item.code == code)
            action = self._action_for(code, matching[-1].stage)
            key = (action, code, milestone)
            if key in already_recorded:
                continue
            constraints, adjustment = self._apply(
                constraints,
                action=action,
                code=code,
                occurrence_count=milestone,
                events=matching,
            )
            if adjustment is not None:
                adjustments.append(adjustment)
                already_recorded.add(adjustment.record_key)

        return RejectionFeedbackPlan(
            constraints=constraints,
            rejection_counts=tuple(sorted(counts.items())),
            adjustments=tuple(adjustments),
        )

    def plan_pipeline_results(
        self,
        results: tuple[V3CandidatePipelineResult, ...],
        *,
        current: BlueprintPlanningConstraints | None = None,
        previous_adjustments: tuple[RejectionFeedbackAdjustment, ...] = (),
    ) -> RejectionFeedbackPlan:
        attempts = tuple(results)
        if any(not isinstance(item, V3CandidatePipelineResult) for item in attempts):
            raise TypeError("results must contain V3CandidatePipelineResult values")
        events = tuple(
            self.event_from_pipeline_result(item) for item in attempts if not item.passed
        )
        return self.plan(
            events,
            current=current,
            previous_adjustments=previous_adjustments,
        )

    @staticmethod
    def event_from_pipeline_result(
        result: V3CandidatePipelineResult,
    ) -> RejectionFeedbackEvent:
        if not isinstance(result, V3CandidatePipelineResult):
            raise TypeError("result must be a V3CandidatePipelineResult")
        if result.passed:
            raise ValueError("accepted pipeline results are not rejection feedback")
        blueprint_result = result.stage_results[0]
        blueprint = getattr(blueprint_result, "blueprint", None)
        archetype = getattr(blueprint, "archetype", None)
        combination = RejectionFeedbackPlannerService._motif_combination(result)
        return RejectionFeedbackEvent(
            code=result.code,
            stage=result.terminal_stage,
            archetype=archetype,
            motif_combination=combination,
        )

    # Alias matching the task's blueprint-planning terminology.
    adjust_blueprint_plan = plan

    @staticmethod
    def _motif_combination(result: V3CandidatePipelineResult) -> tuple[str, ...]:
        keys = ("motifCombination", "motifIDs", "motifIds", "motifs")
        for stage in reversed(result.stage_results):
            for container in (stage.report_fields, stage.metrics):
                for key in keys:
                    value = container.get(key)
                    if isinstance(value, (list, tuple)) and value:
                        return tuple(str(item) for item in value)
        blueprint = getattr(result.stage_results[0], "blueprint", None)
        mechanics = getattr(blueprint, "required_mechanic_categories", ())
        return tuple(str(item) for item in mechanics)

    @staticmethod
    def _action_for(code: str, stage: str) -> str:
        value = code.lower()
        if any(token in value for token in ("timing", "jitter", "rapid_multi_tap")):
            return "adjust_outgoing_edge_order"
        if any(
            token in value
            for token in ("state_space", "search_limit", "budget_exhausted")
        ):
            return "reduce_state_space"
        if stage == "layout" or value.startswith(
            (
                "layout_",
                "portrait_",
                "road_shape_",
                "objective_marker_",
                "stateful_hub_",
                "node_spacing_",
            )
        ):
            return "request_larger_layout"
        if stage == "composition" or any(
            token in value for token in ("motif", "typed_port", "composition_")
        ):
            return "avoid_motif_combination"
        return "select_different_archetype"

    def _apply(
        self,
        constraints: BlueprintPlanningConstraints,
        *,
        action: str,
        code: str,
        occurrence_count: int,
        events: tuple[RejectionFeedbackEvent, ...],
    ) -> tuple[BlueprintPlanningConstraints, RejectionFeedbackAdjustment | None]:
        if action == "avoid_motif_combination":
            combination = next(
                (event.motif_combination for event in reversed(events) if event.motif_combination),
                (),
            )
            if not combination:
                return self._apply(
                    constraints,
                    action="select_different_archetype",
                    code=code,
                    occurrence_count=occurrence_count,
                    events=events,
                )
            if combination in constraints.avoided_motif_combinations:
                return self._apply(
                    constraints,
                    action="select_different_archetype",
                    code=code,
                    occurrence_count=occurrence_count,
                    events=events,
                )
            before: Any = [list(value) for value in constraints.avoided_motif_combinations]
            combinations = constraints.avoided_motif_combinations + (combination,)
            updated = replace(constraints, avoided_motif_combinations=combinations)
            after: Any = [list(value) for value in updated.avoided_motif_combinations]
            details = "Avoid the repeatedly failing motif combination on subsequent blueprints."
        elif action == "request_larger_layout":
            profiles = ("standard", "large", "extra_large")
            index = profiles.index(constraints.layout_profile)
            if index == len(profiles) - 1:
                return constraints, None
            before = constraints.layout_profile
            updated = replace(constraints, layout_profile=profiles[index + 1])
            after = updated.layout_profile
            details = "Request a larger phase-aware layout profile."
        elif action == "select_different_archetype":
            event_archetype = next(
                (event.archetype for event in reversed(events) if event.archetype),
                None,
            )
            current_archetype = constraints.requested_archetype or event_archetype
            before = current_archetype
            after = self._next_archetype(current_archetype)
            if after == current_archetype:
                return constraints, None
            updated = replace(constraints, requested_archetype=after)
            details = "Select a different production archetype for the retry."
        elif action == "reduce_state_space":
            before = constraints.state_space_scale_percent
            after = max(50, before - 15)
            if after == before:
                return constraints, None
            updated = replace(constraints, state_space_scale_percent=after)
            details = (
                "Reduce optional state-space branching while preserving all decision targets."
            )
        elif action == "adjust_outgoing_edge_order":
            before = constraints.outgoing_edge_order_variant
            after = before + 1
            updated = replace(constraints, outgoing_edge_order_variant=after)
            details = "Try the next deterministic outgoing-edge order for timing."
        else:  # pragma: no cover - guarded by _action_for and the model
            raise ValueError(f"unknown feedback action: {action}")

        return updated, RejectionFeedbackAdjustment(
            action=action,
            trigger_code=code,
            occurrence_count=occurrence_count,
            before_value=before,
            after_value=after,
            details=details,
        )

    def _next_archetype(self, current: str | None) -> str:
        if current not in self.supported_archetypes:
            return self.supported_archetypes[0]
        index = self.supported_archetypes.index(current)
        return self.supported_archetypes[(index + 1) % len(self.supported_archetypes)]
