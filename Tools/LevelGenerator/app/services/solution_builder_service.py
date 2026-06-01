from __future__ import annotations

from collections import Counter
from typing import Any

from ..level_editor_imports import SolutionActionModel, SolutionModel
from ..models.difficulty_preset import DifficultyPreset
from .route_timing_service import RouteTimingService


class SolutionBuilderService:
    validation_version = "solution_sidecar_v1"

    def __init__(self) -> None:
        self.route_timing = RouteTimingService()

    def build_no_tap_solution(
        self,
        level_id: str,
        description: str | None = None,
        solution_route: list[str] | None = None,
    ) -> SolutionModel:
        return SolutionModel(
            levelID=level_id,
            description=description or "No taps required. The default route moves from start to package to destination.",
            expectedOutcome="completed",
            maxTaps=0,
            requiresWithinTimeLimit=True,
            actions=[],
            isPlaceholder=None,
            _extra={
                "metadata": {
                    "validationVersion": self.validation_version,
                    "solutionRoute": list(solution_route or []),
                    "requiredTapOrder": [],
                }
            },
        )

    def build_tap_solution(
        self,
        level_id: str,
        tap_node_ids: list[str],
        preset: DifficultyPreset,
        description: str,
        times: list[float] | None = None,
        action_metadata: list[dict[str, Any]] | None = None,
        solution_route: list[str] | None = None,
    ) -> SolutionModel:
        action_pairs = self._resolve_action_pairs(tap_node_ids, preset, times)
        metadata_by_node_time = self._metadata_by_node_time(action_pairs, action_metadata)
        actions = [
            SolutionActionModel(
                timeSeconds=round(time_seconds, 2),
                tapNodeID=node_id,
                _extra=metadata_by_node_time.get((node_id, round(time_seconds, 2)), {}),
            )
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
            _extra={
                "metadata": {
                    "validationVersion": self.validation_version,
                    "solutionRoute": list(solution_route or []),
                    "requiredTapOrder": [node_id for _, node_id in action_pairs],
                }
            },
        )

    def build_route_timed_tap_solution(
        self,
        level_id: str,
        tap_node_ids: list[str],
        route_node_ids: list[str],
        positions: dict[str, tuple[float, float]],
        preset: DifficultyPreset,
        description: str,
        lead_time_seconds: float = 0.35,
        route_edge_shapes: dict[tuple[str, str], str | None] | None = None,
        route_edge_ids_by_pair: dict[tuple[str, str], str] | None = None,
        outgoing_edge_ids_by_node: dict[str, list[str]] | None = None,
    ) -> SolutionModel:
        times, arrival_times_by_action = self._times_before_route_arrivals(
            tap_node_ids,
            route_node_ids,
            positions,
            preset,
            lead_time_seconds,
            route_edge_shapes,
        )
        action_metadata = self._route_action_metadata(
            tap_node_ids,
            route_node_ids,
            times,
            arrival_times_by_action,
            route_edge_ids_by_pair or {},
            outgoing_edge_ids_by_node or {},
        )
        return self.build_tap_solution(
            level_id,
            tap_node_ids,
            preset,
            description,
            times=times,
            action_metadata=action_metadata,
            solution_route=route_node_ids,
        )

    def apply_generation_metadata(
        self,
        solution: SolutionModel | None,
        *,
        template_name: str,
        seed: int,
        recipe_family: str | None = None,
        recipe_variant: str | None = None,
        solution_route: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        if solution is None:
            return
        metadata = dict(solution._extra.get("metadata", {}))
        metadata.setdefault("validationVersion", self.validation_version)
        metadata["template"] = template_name
        metadata["generatedSeed"] = seed
        if recipe_family is not None:
            metadata["recipeFamily"] = recipe_family
        if recipe_variant is not None:
            metadata["recipeVariant"] = recipe_variant
        if solution_route and not metadata.get("solutionRoute"):
            metadata["solutionRoute"] = list(solution_route)
        metadata.setdefault("requiredTapOrder", [action.tapNodeID for action in solution.actions])
        solution._extra["metadata"] = metadata

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

    def _metadata_by_node_time(
        self,
        action_pairs: list[tuple[float, str]],
        action_metadata: list[dict[str, Any]] | None,
    ) -> dict[tuple[str, float], dict[str, Any]]:
        if action_metadata is None:
            return {
                (node_id, round(time_seconds, 2)): {
                    "reason": f"Rotate switch '{node_id}' so the delivery follows the intended route.",
                }
                for time_seconds, node_id in action_pairs
            }
        if len(action_metadata) != len(action_pairs):
            raise ValueError("action_metadata must have the same length as tap_node_ids")
        return {
            (node_id, round(time_seconds, 2)): dict(metadata)
            for (time_seconds, node_id), metadata in zip(action_pairs, action_metadata)
        }

    def _times_before_route_arrivals(
        self,
        tap_node_ids: list[str],
        route_node_ids: list[str],
        positions: dict[str, tuple[float, float]],
        preset: DifficultyPreset,
        lead_time_seconds: float,
        route_edge_shapes: dict[tuple[str, str], str | None] | None,
    ) -> tuple[list[float], list[float]]:
        arrival_times = self._route_arrival_times(route_node_ids, positions, route_edge_shapes)
        times: list[float] = []
        action_arrival_times: list[float] = []
        search_start = 0
        previous_time: float | None = None
        for tap_node_id in tap_node_ids:
            route_index = self._find_next_route_index(route_node_ids, tap_node_id, search_start)
            if route_index is None:
                raise ValueError(f"tap node {tap_node_id} is not on the expected route")
            raw_time = max(0.1, arrival_times[route_index] - lead_time_seconds)
            if previous_time is not None and raw_time - previous_time < preset.min_tap_spacing_seconds:
                raw_time = previous_time + preset.min_tap_spacing_seconds
            times.append(raw_time)
            action_arrival_times.append(arrival_times[route_index])
            previous_time = raw_time
            search_start = route_index + 1
        return times, action_arrival_times

    def _route_action_metadata(
        self,
        tap_node_ids: list[str],
        route_node_ids: list[str],
        times: list[float],
        arrival_times_by_action: list[float],
        route_edge_ids_by_pair: dict[tuple[str, str], str],
        outgoing_edge_ids_by_node: dict[str, list[str]],
    ) -> list[dict[str, Any]]:
        active_edge_by_node = {
            node_id: edge_ids[0]
            for node_id, edge_ids in outgoing_edge_ids_by_node.items()
            if edge_ids
        }
        route_search_start = 0
        metadata: list[dict[str, Any]] = []
        for tap_node_id, time_seconds, arrival_time in zip(tap_node_ids, times, arrival_times_by_action):
            route_index = self._find_next_route_index(route_node_ids, tap_node_id, route_search_start)
            next_route_node_id = (
                route_node_ids[route_index + 1]
                if route_index is not None and route_index + 1 < len(route_node_ids)
                else None
            )
            expected_edge_id = (
                route_edge_ids_by_pair.get((tap_node_id, next_route_node_id))
                if next_route_node_id is not None
                else None
            )
            outgoing_edge_ids = outgoing_edge_ids_by_node.get(tap_node_id, [])
            before_edge_id = active_edge_by_node.get(tap_node_id)
            after_edge_id = self._next_edge_id(before_edge_id, outgoing_edge_ids)
            if after_edge_id is not None:
                active_edge_by_node[tap_node_id] = after_edge_id
            metadata.append(
                {
                    "reason": self._tap_reason(tap_node_id, next_route_node_id),
                    "expectedEdgeAfterTap": expected_edge_id or after_edge_id,
                    "expectedRouteNodeAfterTap": next_route_node_id,
                    "reactionWindowSeconds": round(arrival_time - time_seconds, 2),
                    "switchStateBeforeTap": before_edge_id,
                    "switchStateAfterTap": after_edge_id,
                }
            )
            route_search_start = (route_index + 1) if route_index is not None else route_search_start
        return metadata

    def _next_edge_id(self, before_edge_id: str | None, outgoing_edge_ids: list[str]) -> str | None:
        if not outgoing_edge_ids:
            return None
        if before_edge_id in outgoing_edge_ids:
            return outgoing_edge_ids[(outgoing_edge_ids.index(before_edge_id) + 1) % len(outgoing_edge_ids)]
        return outgoing_edge_ids[0]

    def _tap_reason(self, tap_node_id: str, next_route_node_id: str | None) -> str:
        if next_route_node_id is None:
            return f"Rotate switch '{tap_node_id}' before the delivery reaches it."
        return f"Rotate switch '{tap_node_id}' toward '{next_route_node_id}' before arrival."

    def _route_arrival_times(
        self,
        route_node_ids: list[str],
        positions: dict[str, tuple[float, float]],
        route_edge_shapes: dict[tuple[str, str], str | None] | None,
    ) -> list[float]:
        return self.route_timing.route_arrival_times(route_node_ids, positions, edges_by_route_pair=route_edge_shapes)

    def _find_next_route_index(
        self,
        route_node_ids: list[str],
        tap_node_id: str,
        search_start: int,
    ) -> int | None:
        for index in range(search_start, len(route_node_ids)):
            if route_node_ids[index] == tap_node_id:
                return index
        return None
