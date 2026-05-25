from __future__ import annotations

from collections import Counter

from ..level_editor_imports import SolutionActionModel, SolutionModel
from ..models.difficulty_preset import DifficultyPreset


class SolutionBuilderService:
    def build_no_tap_solution(self, level_id: str, description: str | None = None) -> SolutionModel:
        return SolutionModel(
            levelID=level_id,
            description=description or "No taps required. The default route moves from start to package to destination.",
            expectedOutcome="completed",
            maxTaps=0,
            requiresWithinTimeLimit=True,
            actions=[],
            isPlaceholder=None,
        )

    def build_tap_solution(
        self,
        level_id: str,
        tap_node_ids: list[str],
        preset: DifficultyPreset,
        description: str,
        times: list[float] | None = None,
    ) -> SolutionModel:
        action_pairs = self._resolve_action_pairs(tap_node_ids, preset, times)
        actions = [
            SolutionActionModel(timeSeconds=round(time_seconds, 2), tapNodeID=node_id)
            for time_seconds, node_id in action_pairs
        ]
        return SolutionModel(
            levelID=level_id,
            description=description,
            expectedOutcome="completed",
            maxTaps=len(actions),
            requiresWithinTimeLimit=True,
            actions=actions,
            isPlaceholder=None,
        )

    def _resolve_action_pairs(
        self,
        tap_node_ids: list[str],
        preset: DifficultyPreset,
        times: list[float] | None,
    ) -> list[tuple[float, str]]:
        if times is None:
            first_time = max(0.4, preset.min_tap_spacing_seconds)
            return [
                (round(first_time + (index * preset.min_tap_spacing_seconds), 2), node_id)
                for index, node_id in enumerate(tap_node_ids)
            ]
        if len(times) != len(tap_node_ids):
            raise ValueError("times must have the same length as tap_node_ids")
        action_pairs = sorted((float(time), node_id) for time, node_id in zip(times, tap_node_ids))
        previous: float | None = None
        tolerance = 1e-9
        for time, _ in action_pairs:
            if previous is not None and time - previous < preset.min_tap_spacing_seconds - tolerance:
                raise ValueError("solution action times are closer than the minimum tap spacing")
            previous = time

        repeated_counts = Counter(tap_node_ids)
        if any(count > 1 for count in repeated_counts.values()):
            for node_id, count in repeated_counts.items():
                if count <= 1:
                    continue
                node_times = [time for time, tap_node_id in action_pairs if tap_node_id == node_id]
                previous_node_time: float | None = None
                for time in node_times:
                    if previous_node_time is not None and time - previous_node_time < preset.min_tap_spacing_seconds - tolerance:
                        raise ValueError("repeated switch taps are closer than the minimum tap spacing")
                    previous_node_time = time
        return action_pairs
