"""Deterministic SVG previews for every player-visible route state."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from typing import Iterable, Sequence

from ..models.layout_state import LayoutStateSnapshot
from ..models.state_snapshot_preview import (
    StateSnapshotPreviewArtifact,
    StateSnapshotPreviewResult,
)


class StateSnapshotPreviewService:
    """Render objective states and strategy overlays without altering candidates."""

    width = 540
    height = 720
    margin = 54

    def snapshots_for(
        self,
        level,
        *,
        optimal_route: Sequence[str] = (),
    ) -> tuple[LayoutStateSnapshot, ...]:
        objectives = tuple(sorted(
            level.effective_objectives,
            key=lambda item: (item.sequenceIndex, item.id),
        ))
        edge_by_pair = {
            (edge.fromNodeID, edge.toNodeID): edge
            for edge in level.graph.edges
        }
        route_edges = [
            edge_by_pair[pair]
            for pair in zip(optimal_route, optimal_route[1:])
            if pair in edge_by_pair
        ]
        snapshots: list[LayoutStateSnapshot] = []
        for state_index in range(max(1, len(objectives) + 1)):
            completed_objectives = objectives[:state_index]
            completed_ids = tuple(item.id for item in completed_objectives)
            active = objectives[state_index] if state_index < len(objectives) else None
            active_index = active.sequenceIndex if active is not None else None
            visible_ids = tuple(
                objective.id
                for objective in objectives
                if objective.sequenceIndex < state_index
                or objective is active
                or objective.revealPolicy == "always"
            )
            usage_counts = self._usage_counts_at_state(
                route_edges,
                optimal_route,
                completed_objectives,
            )
            available: list[str] = []
            locked: list[str] = []
            consumed: list[str] = []
            for edge in level.graph.edges:
                rule = level.effective_edge_availability_rule(edge)
                usage_count = usage_counts.get(edge.id, 0)
                if rule.allows(set(completed_ids), active_index, usage_count=usage_count):
                    available.append(edge.id)
                elif rule.usageLimit is not None and usage_count >= rule.usageLimit:
                    consumed.append(edge.id)
                else:
                    locked.append(edge.id)
            available_set = set(available)
            active_switches = tuple(
                node.id
                for node in sorted(level.graph.nodes, key=lambda item: item.id)
                if sum(edge_id in available_set for edge_id in node.outgoingEdgeIDs) >= 2
            )
            snapshots.append(LayoutStateSnapshot(
                state_index=state_index,
                completed_objective_ids=completed_ids,
                active_objective_id=active.id if active is not None else None,
                visible_objective_ids=visible_ids,
                available_edge_ids=tuple(available),
                locked_edge_ids=tuple(locked),
                consumed_edge_ids=tuple(consumed),
                active_switch_node_ids=active_switches,
            ))
        return tuple(snapshots)

    def write_generated_level_previews(
        self,
        generated_level,
        output_dir: Path,
        *,
        optimal_route: Sequence[str] | None = None,
        alternate_routes: Iterable[Sequence[str]] = (),
    ) -> StateSnapshotPreviewResult:
        level = generated_level.level_document
        resolved_optimal = tuple(
            optimal_route
            or self._solution_route(generated_level)
            or self._exact_optimal_route(generated_level)
        )
        resolved_alternates = tuple(
            tuple(route)
            for route in (
                tuple(alternate_routes)
                or self._exact_alternate_routes(generated_level)
            )
            if route
        )
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_id = self._safe_name(level.id)
        artifacts: list[StateSnapshotPreviewArtifact] = []
        snapshots = self.snapshots_for(level, optimal_route=resolved_optimal)
        objective_by_id = {objective.id: objective for objective in level.effective_objectives}

        for snapshot in snapshots:
            if snapshot.state_index == 0:
                suffix = "initial"
                kind = "initial_state"
            else:
                completed_id = snapshot.completed_objective_ids[-1]
                suffix = f"after-{self._safe_name(completed_id)}"
                kind = "objective_completion_state"
            path = output_dir / f"{safe_id}.state-{snapshot.state_index:02d}-{suffix}.svg"
            title = (
                "Initial state"
                if snapshot.state_index == 0
                else f"After {objective_by_id[snapshot.completed_objective_ids[-1]].id}"
            )
            path.write_text(
                self._state_svg(level, snapshot, title),
                encoding="utf-8",
            )
            artifacts.append(StateSnapshotPreviewArtifact(
                kind,
                path,
                snapshot.state_index,
                snapshot.active_objective_id,
            ))

        final_path = output_dir / f"{safe_id}.final-route.svg"
        final_path.write_text(
            self._route_overlay_svg(
                level,
                resolved_optimal,
                (),
                "Final optimal route",
            ),
            encoding="utf-8",
        )
        artifacts.append(StateSnapshotPreviewArtifact("final_route_overlay", final_path))

        if resolved_alternates:
            comparison_path = output_dir / f"{safe_id}.optimal-vs-alternate.svg"
            comparison_path.write_text(
                self._route_overlay_svg(
                    level,
                    resolved_optimal,
                    resolved_alternates,
                    "Optimal versus alternate routes",
                ),
                encoding="utf-8",
            )
            artifacts.append(StateSnapshotPreviewArtifact(
                "optimal_alternate_overlay",
                comparison_path,
            ))

        result = StateSnapshotPreviewResult(level.id, tuple(artifacts))
        generated_level.state_preview_paths = result.paths
        return result

    def _state_svg(self, level, snapshot: LayoutStateSnapshot, title: str) -> str:
        available = set(snapshot.available_edge_ids)
        locked = set(snapshot.locked_edge_ids)
        consumed = set(snapshot.consumed_edge_ids)
        objective_by_node = {
            objective.nodeID: objective
            for objective in level.effective_objectives
            if objective.id in snapshot.visible_objective_ids
        }
        completed = set(snapshot.completed_objective_ids)
        lines = self._svg_header(level.id, title)
        for edge in level.graph.edges:
            if edge.id in available:
                color, dash, opacity = "#52606d", "", "1"
            elif edge.id in consumed:
                color, dash, opacity = "#a0aec0", "2 8", "0.55"
            elif edge.id in locked:
                color, dash, opacity = "#94a3b8", "8 6", "0.7"
            else:
                color, dash, opacity = "#cbd5e1", "4 8", "0.4"
            lines.append(self._edge_svg(level, edge, color, dash=dash, opacity=opacity))
            if edge.id in locked:
                x, y = self._edge_midpoint(level, edge)
                lines.extend((
                    f'<rect x="{x - 6:.1f}" y="{y - 5:.1f}" width="12" height="10" rx="2" fill="#475569"/>',
                    f'<path d="M {x - 4:.1f} {y - 5:.1f} a 4 4 0 0 1 8 0" fill="none" stroke="#475569" stroke-width="2"/>',
                ))
        for node in level.graph.nodes:
            x, y = self._point_map(level)[node.id]
            fill = "#94a3b8"
            if node.id == level.startNodeID:
                fill = "#22c55e"
            if node.id in snapshot.active_switch_node_ids:
                lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="14" fill="none" stroke="#2563eb" stroke-width="3"/>')
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{fill}" stroke="#0f172a"/>')
            objective = objective_by_node.get(node.id)
            if objective is not None:
                status = (
                    "completed" if objective.id in completed
                    else "active" if objective.id == snapshot.active_objective_id
                    else "future"
                )
                marker_color = {
                    "completed": "#16a34a",
                    "active": "#f59e0b",
                    "future": "#a855f7",
                }[status]
                lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="17" fill="none" stroke="{marker_color}" stroke-width="4"/>')
                lines.append(f'<text x="{x + 18:.1f}" y="{y - 14:.1f}" font-family="Arial" font-size="12" fill="#0f172a">{escape(objective.id)} ({status})</text>')
        lines.append(self._legend(snapshot))
        lines.append("</svg>")
        return "\n".join(lines) + "\n"

    def _route_overlay_svg(
        self,
        level,
        optimal_route: Sequence[str],
        alternate_routes: Sequence[Sequence[str]],
        title: str,
    ) -> str:
        optimal_pairs = set(zip(optimal_route, optimal_route[1:]))
        alternate_pairs = {
            pair
            for route in alternate_routes
            for pair in zip(route, route[1:])
        }
        lines = self._svg_header(level.id, title)
        for edge in level.graph.edges:
            pair = (edge.fromNodeID, edge.toNodeID)
            if pair in optimal_pairs and pair in alternate_pairs:
                color, width, dash = "#0891b2", 7, ""
            elif pair in optimal_pairs:
                color, width, dash = "#16a34a", 7, ""
            elif pair in alternate_pairs:
                color, width, dash = "#9333ea", 6, "10 6"
            else:
                color, width, dash = "#cbd5e1", 3, ""
            lines.append(self._edge_svg(level, edge, color, width=width, dash=dash))
        for node in level.graph.nodes:
            x, y = self._point_map(level)[node.id]
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#f8fafc" stroke="#0f172a"/>')
        lines.append('<g transform="translate(24,680)" font-family="Arial" font-size="12" fill="#0f172a"><text>Optimal</text><line x1="58" y1="-4" x2="105" y2="-4" stroke="#16a34a" stroke-width="6"/><text x="125">Alternate</text><line x1="190" y1="-4" x2="237" y2="-4" stroke="#9333ea" stroke-width="6" stroke-dasharray="10 6"/></g>')
        lines.append("</svg>")
        return "\n".join(lines) + "\n"

    def _edge_svg(self, level, edge, color: str, *, width: int = 4, dash: str = "", opacity: str = "1") -> str:
        points = self._edge_points(level, edge)
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        return f'<polyline points="{point_text}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" opacity="{opacity}"{dash_attribute}/>'

    def _edge_points(self, level, edge) -> tuple[tuple[float, float], ...]:
        points = self._point_map(level)
        start, end = points[edge.fromNodeID], points[edge.toNodeID]
        shape = edge.roadShape or "horizontalFirst"
        bend = (end[0], start[1]) if shape == "horizontalFirst" else (start[0], end[1])
        if bend in {start, end}:
            return start, end
        return start, bend, end

    def _edge_midpoint(self, level, edge) -> tuple[float, float]:
        points = self._edge_points(level, edge)
        if len(points) == 2:
            return ((points[0][0] + points[1][0]) / 2, (points[0][1] + points[1][1]) / 2)
        return points[1]

    def _point_map(self, level) -> dict[str, tuple[float, float]]:
        nodes = level.graph.nodes
        xs = [node.x for node in nodes] or [0.0]
        ys = [node.y for node in nodes] or [0.0]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1e-9)
        span_y = max(max_y - min_y, 1e-9)
        return {
            node.id: (
                self.margin + ((node.x - min_x) / span_x * (self.width - (2 * self.margin))),
                self.height - (
                    self.margin + ((node.y - min_y) / span_y * (self.height - (2 * self.margin)))
                ),
            )
            for node in nodes
        }

    def _svg_header(self, level_id: str, title: str) -> list[str]:
        return [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">',
            '<rect width="100%" height="100%" fill="#f8fafc"/>',
            f'<text x="20" y="26" font-family="Arial" font-size="15" font-weight="bold" fill="#0f172a">{escape(level_id)}</text>',
            f'<text x="20" y="47" font-family="Arial" font-size="13" fill="#334155">{escape(title)}</text>',
        ]

    @staticmethod
    def _legend(snapshot: LayoutStateSnapshot) -> str:
        active = escape(snapshot.active_objective_id or "complete")
        return f'<text x="20" y="698" font-family="Arial" font-size="12" fill="#334155">Active objective: {active} · solid=open · dashed=locked · dotted=consumed</text>'

    @staticmethod
    def _solution_route(generated_level) -> tuple[str, ...]:
        metadata = getattr(generated_level.solution, "_extra", {}).get("metadata", {})
        route = metadata.get("solutionRoute") or ()
        if route:
            return tuple(str(node_id) for node_id in route)
        abstract = getattr(generated_level, "abstract_solution_metadata", None)
        return tuple(getattr(abstract, "required_path", ()) or ())

    @classmethod
    def _exact_optimal_route(cls, generated_level) -> tuple[str, ...]:
        search = getattr(generated_level, "strategy_search_result", None)
        trace = getattr(search, "canonical_optimal_strategy", None)
        if trace is None:
            proof = getattr(generated_level, "unique_optimal_proof", None)
            strategy_class = getattr(proof, "optimal_strategy_class", None)
            trace = getattr(strategy_class, "canonical_trace", None)
        return cls._trace_route(trace)

    @classmethod
    def _exact_alternate_routes(cls, generated_level) -> tuple[tuple[str, ...], ...]:
        report = getattr(generated_level, "alternate_success_report", None)
        traces = [
            getattr(getattr(item, "strategy_class", None), "canonical_trace", None)
            for item in getattr(report, "classifications", ())
        ]
        if not traces:
            search = getattr(generated_level, "strategy_search_result", None)
            canonical = getattr(search, "canonical_optimal_strategy", None)
            traces = [
                trace
                for trace in getattr(search, "all_successful_strategies", ())
                if trace is not canonical
            ]
        return tuple(route for trace in traces if (route := cls._trace_route(trace)))

    @staticmethod
    def _trace_route(trace) -> tuple[str, ...]:
        if trace is None:
            return ()
        route: list[str] = []
        for action in getattr(trace, "actions", ()):
            visited = tuple(getattr(action, "visited_node_ids", ()) or ())
            if not visited:
                continue
            if route and route[-1] == visited[0]:
                route.extend(visited[1:])
            else:
                route.extend(visited)
        return tuple(route)

    @staticmethod
    def _usage_counts_at_state(route_edges, route, completed_objectives) -> dict[str, int]:
        if not route_edges or not completed_objectives:
            return {}
        final_node = completed_objectives[-1].nodeID
        try:
            boundary = max(index for index, node_id in enumerate(route) if node_id == final_node)
        except ValueError:
            return {}
        counts: dict[str, int] = {}
        for edge in route_edges[:boundary]:
            counts[edge.id] = counts.get(edge.id, 0) + 1
        return counts

    @staticmethod
    def _safe_name(value: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-.")
        return normalized or "candidate"
