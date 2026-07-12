from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

from ..models.candidate_signature import CandidateSignature


class CandidateSignatureService:
    def signature_for(self, generated_level) -> CandidateSignature:
        level = generated_level.level_document
        solution = generated_level.solution
        normalized_edges = self._normalized_edges(level)
        normalized_positions = self._normalized_positions(level)
        tap_node_ids = [action.tapNodeID for action in sorted(solution.actions, key=lambda action: action.timeSeconds)]
        edges_by_id = {edge.id: edge for edge in level.graph.edges}
        outgoing_edge_counts = [
            sum(
                1
                for edge_id in node.outgoingEdgeIDs
                if edge_id in edges_by_id and edges_by_id[edge_id].fromNodeID == node.id
            )
            for node in level.graph.nodes
        ]
        max_outgoing_edge_count = max(outgoing_edge_counts, default=0)
        central_switch_revisit_count = max(
            (tap_node_ids.count(node.id) for node in level.graph.nodes if len(node.outgoingEdgeIDs) > 1),
            default=0,
        )
        dead_end_count = sum(
            1
            for node in level.graph.nodes
            if not node.outgoingEdgeIDs and node.id != level.destinationNodeID
        )
        topology_payload = {
            "start": level.startNodeID,
            "package": level.packageNodeID,
            "destination": level.destinationNodeID,
            "edges": normalized_edges,
            "maxOutgoingEdgeCount": max_outgoing_edge_count,
            "hasFourWaySwitch": max_outgoing_edge_count == 4,
        }
        layout_payload = {
            "positions": normalized_positions,
        }
        solution_payload = {
            "tapNodeIDs": tap_node_ids,
            "centralSwitchRevisitCount": central_switch_revisit_count,
        }
        profile = getattr(generated_level, "decision_profile", None)
        switch_degree_sequence = tuple(sorted((count for count in outgoing_edge_counts if count > 1), reverse=True))
        failure_distribution = self._failure_distribution(profile)
        silhouette, mirrored_silhouette = self._layout_silhouettes(normalized_positions)
        action_times = tuple(float(action.timeSeconds) for action in sorted(solution.actions, key=lambda action: action.timeSeconds))
        return CandidateSignature(
            level_id=generated_level.level_id,
            template_name=generated_level.template_name,
            difficulty=generated_level.difficulty,
            node_count=len(level.graph.nodes),
            edge_count=len(level.graph.edges),
            switch_count=sum(1 for node in level.graph.nodes if len(node.outgoingEdgeIDs) > 1),
            required_tap_count=len(solution.actions),
            dead_end_count=dead_end_count,
            topology_hash=self._hash_payload(topology_payload),
            layout_hash=self._hash_payload(layout_payload),
            solution_hash=self._hash_payload(solution_payload),
            normalized_positions=normalized_positions,
            max_outgoing_edge_count=max_outgoing_edge_count,
            has_four_way_switch=max_outgoing_edge_count == 4,
            central_switch_revisit_count=central_switch_revisit_count,
            mechanic_tags=tuple(getattr(generated_level, "mechanic_tags", ()) or ()),
            primary_mechanic_tag=getattr(generated_level, "primary_mechanic_tag", "") or "",
            topology_class=getattr(generated_level, "topology_class", "") or "",
            required_path_length=self._required_path_length(generated_level),
            layout_orientation=self._layout_orientation(generated_level),
            layout_size_profile=self._layout_size_profile(generated_level),
            decision_dependency_pattern=(
                int(getattr(profile, "required_decision_count", len(solution.actions))),
                int(getattr(profile, "ordered_dependency_count", 0)),
                float(getattr(profile, "independent_decision_ratio", 0.0)),
            ),
            switch_degree_sequence=switch_degree_sequence,
            revisit_state_reversal_pattern=(
                int(getattr(profile, "route_revisit_count", 0)),
                int(getattr(profile, "repeated_switch_decision_count", central_switch_revisit_count)),
                int(getattr(profile, "switch_state_change_on_revisit_count", 0)),
            ),
            failure_outcome_distribution=failure_distribution,
            package_phase_pattern=(
                int(getattr(profile, "package_phase_decisions_before", 0)),
                int(getattr(profile, "package_phase_decisions_after", 0)),
            ),
            layout_silhouette=silhouette,
            mirrored_layout_silhouette=mirrored_silhouette,
            road_direction_histogram=self._road_direction_histogram(level),
            solution_decision_timing_pattern=self._timing_pattern(action_times),
        )

    def _failure_distribution(self, profile) -> tuple[tuple[str, int], ...]:
        if profile is None:
            return ()
        counts = Counter(getattr(profile, "failure_outcome_types", ()) or ())
        dead_ends = int(getattr(profile, "dead_end_choice_count", 0))
        early_destination = int(getattr(profile, "destination_before_package_choice_count", 0))
        if dead_ends:
            counts["dead_end"] = dead_ends
        if early_destination:
            counts["destination_before_package"] = early_destination
        known = sum(counts.values())
        remainder = max(0, int(getattr(profile, "failure_route_count", known)) - known)
        if remainder:
            counts["other"] += remainder
        return tuple(sorted(counts.items()))

    def _layout_silhouettes(self, positions):
        visual = tuple(sorted((x, y) for _, x, y in positions))
        mirrored = tuple(sorted((round(1.0 - x, 4), y) for x, y in visual))
        return visual, min(visual, mirrored)

    def _road_direction_histogram(self, level_document) -> tuple[tuple[str, int], ...]:
        positions = {node.id: (float(node.x), float(node.y)) for node in level_document.graph.nodes}
        counts: Counter[str] = Counter()
        for edge in level_document.graph.edges:
            if edge.fromNodeID not in positions or edge.toNodeID not in positions:
                continue
            x1, y1 = positions[edge.fromNodeID]
            x2, y2 = positions[edge.toNodeID]
            dx, dy = x2 - x1, y2 - y1
            if abs(dx) >= abs(dy):
                counts["right" if dx >= 0 else "left"] += 1
            else:
                counts["down" if dy >= 0 else "up"] += 1
        return tuple(sorted(counts.items()))

    def _timing_pattern(self, times: tuple[float, ...]) -> tuple[float, ...]:
        if not times:
            return ()
        origin = times[0]
        relative = tuple(time - origin for time in times)
        scale = relative[-1]
        if scale <= 0:
            return tuple(0.0 for _ in relative)
        return tuple(round(value / scale, 4) for value in relative)

    def _normalized_edges(self, level_document) -> tuple[tuple[str, str], ...]:
        return tuple(
            sorted(
                (edge.fromNodeID, edge.toNodeID)
                for edge in level_document.graph.edges
            )
        )

    def _normalized_positions(self, level_document) -> tuple[tuple[str, float, float], ...]:
        raw_positions = {node.id: (float(node.x), float(node.y)) for node in level_document.graph.nodes}
        if not raw_positions:
            return ()

        xs = [position[0] for position in raw_positions.values()]
        ys = [position[1] for position in raw_positions.values()]
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        width = max_x - min_x
        height = max_y - min_y

        normalized: list[tuple[str, float, float]] = []
        for node_id, (x, y) in raw_positions.items():
            normalized_x = 0.5 if width == 0 else (x - min_x) / width
            normalized_y = 0.5 if height == 0 else (y - min_y) / height
            normalized.append((node_id, round(normalized_x, 4), round(normalized_y, 4)))
        return tuple(sorted(normalized))

    def _hash_payload(self, payload: Any) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _required_path_length(self, generated_level) -> int | None:
        metadata = getattr(generated_level, "abstract_solution_metadata", None)
        if metadata is not None and getattr(metadata, "required_path", None):
            return max(len(metadata.required_path) - 1, 0)

        solution_metadata = dict(getattr(generated_level.solution, "_extra", {}).get("metadata", {}))
        route = solution_metadata.get("solutionRoute") or []
        if route:
            return max(len(route) - 1, 0)
        return None

    def _layout_orientation(self, generated_level) -> str:
        metadata = getattr(generated_level, "layout_metadata", None) or {}
        explicit = metadata.get("orientation")
        if explicit:
            return str(explicit).strip().lower() or "unknown"

        strategy = str(metadata.get("strategy", "")).lower()
        if "vertical" in strategy:
            return "vertical"
        if "horizontal" in strategy:
            return "horizontal"

        variant = str(getattr(generated_level, "selected_layout_variant", "") or metadata.get("variant", "")).lower()
        if variant == "tall":
            return "vertical"
        if variant == "wide":
            return "horizontal"
        return "unknown"

    def _layout_size_profile(self, generated_level) -> str:
        metadata = getattr(generated_level, "layout_metadata", None) or {}
        profile = str(metadata.get("layoutSizeProfile", "")).strip().lower()
        return profile or "standard_portrait"
