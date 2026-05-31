from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..paths import find_repo_root
from ..services.preview_image_service import PreviewImageService
from ..services.route_timing_service import RouteTimingService
from ..services.switch_visual_clarity_service import SwitchVisualClarityService


class GenerationReportRepository:
    def __init__(self) -> None:
        self.preview_image_service = PreviewImageService()
        self.route_timing = RouteTimingService()
        self.switch_visual_clarity = SwitchVisualClarityService()

    def write_markdown(self, path: Path, config, result) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_previews(path.parent, result)
        path.write_text(self._markdown(config, result), encoding="utf-8")
        return path

    def write_json(self, path: Path, config, result) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_previews(path.parent, result)
        path.write_text(json.dumps(self._payload(config, result), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def _payload(self, config, result) -> dict[str, Any]:
        repo_root = find_repo_root()
        return {
            "generationTimestamp": datetime.now(timezone.utc).isoformat(),
            "commandArguments": config.command_arguments or [],
            "repoRoot": str(repo_root),
            "levelsOutputDir": str(config.levels_output_dir),
            "solutionsOutputDir": str(config.solutions_output_dir),
            "difficulty": config.difficulty,
            "template": config.template_name,
            "generationMode": config.generation_mode,
            "recipePoolSize": config.recipe_pool_size,
            "layoutsPerRecipe": config.layouts_per_recipe,
            "roadShapesPerLayout": config.road_shapes_per_layout,
            "baseSeed": config.seed,
            "dryRun": config.dry_run,
            "overwrite": config.overwrite,
            "syncXcodeProject": config.sync_xcode_project,
            "compareAgainstExisting": config.compare_against_existing,
            "candidatePoolSize": config.candidate_pool_size,
            "passed": getattr(result, "passed", True),
            "acceptedLevels": [
                {
                    "levelID": level.level_id,
                    "template": level.template_name,
                    "recipeFamily": level.recipe_family,
                    "recipeVariant": level.recipe_variant,
                    "abstractGraphSignature": level.abstract_graph_signature,
                    "abstractGraphSignatureShort": (
                        level.abstract_graph_signature[:12] if level.abstract_graph_signature else None
                    ),
                    "selectedLayoutVariant": level.selected_layout_variant,
                    "selectedRoadShapeStrategy": level.selected_road_shape_strategy,
                    "seed": level.seed,
                    "difficulty": level.difficulty,
                    "nodes": level.node_count,
                    "edges": level.edge_count,
                    "switches": level.switch_count,
                    "parTaps": level.level_document.parTaps,
                    "timeLimit": level.level_document.timeLimitSeconds,
                    "requiredTaps": level.required_tap_count,
                    "signature": self._signature_payload(level),
                    "quality": self._quality_payload(level),
                    "simulation": self._simulation_payload(level),
                    "switchPreview": self._switch_preview_payload(level),
                    "previewPath": str(level.preview_path) if level.preview_path else None,
                    "status": "passed",
                    "notes": level.generation_notes,
                    "warnings": list(getattr(level, "warning_messages", [])),
                }
                for level in result.accepted
            ],
            "rejectedCandidateCount": result.rejected_candidate_count,
            "rejectionReasonCounts": result.rejection_reason_counts,
            "writtenLevelPaths": [str(path) for path in result.written_level_paths],
            "writtenSolutionPaths": [str(path) for path in result.written_solution_paths],
            "swiftTests": {
                "run": result.swift_test_summary.passed is not None,
                "command": result.swift_test_summary.command,
                "exitCode": result.swift_test_summary.exit_code,
                "passed": result.swift_test_summary.passed,
                "summary": result.swift_test_summary.summary,
            },
            "messages": list(result.messages),
            "recommendations": self._recommendations(config, result),
            "xcodegenNote": (
                "project.yml includes resource directories. Production generation syncs TinyRoutes.xcodeproj "
                "with `xcodegen generate` before Swift tests unless `--no-xcodegen` is used."
            ),
        }

    def _markdown(self, config, result) -> str:
        payload = self._payload(config, result)
        lines = [
            "# Tiny Routes Generation Report",
            "",
            f"- Generated: `{payload['generationTimestamp']}`",
            f"- Repo root: `{payload['repoRoot']}`",
            f"- Difficulty: `{payload['difficulty']}`",
            f"- Template mode: `{payload['template']}`",
            f"- Generation mode: `{payload['generationMode']}`",
            f"- Base seed: `{payload['baseSeed']}`",
            f"- Dry run: `{payload['dryRun']}`",
            f"- Compare existing levels: `{payload['compareAgainstExisting']}`",
            f"- Candidate pool size: `{payload['candidatePoolSize']}`",
            f"- Recipe pool size: `{payload['recipePoolSize']}`",
            f"- Layouts per recipe: `{payload['layoutsPerRecipe']}`",
            f"- Road shapes per layout: `{payload['roadShapesPerLayout']}`",
            f"- Xcode project sync: `{payload['syncXcodeProject']}`",
            f"- Swift tests: `{payload['swiftTests']['summary']}`",
            "",
            "## Accepted Levels",
            "",
            "| Level | Source | Seed | Difficulty | Nodes | Edges | Switches | Par Taps | Time Limit | Quality | Preview | Signatures | Status |",
            "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|",
        ]
        for level in payload["acceptedLevels"]:
            signature = level["signature"]
            signature_summary = ""
            if signature:
                signature_summary = (
                    f"T:{signature['topologyHashShort']} "
                    f"L:{signature['layoutHashShort']} "
                    f"S:{signature['solutionHashShort']}"
                )
            quality_summary = level["quality"]["total"] if level["quality"] else ""
            preview = f"[SVG]({level['previewPath']})" if level["previewPath"] else ""
            source = level["template"]
            if level["recipeFamily"]:
                source = f"{level['recipeFamily']} / {level['recipeVariant']}"
            lines.append(
                "| `{levelID}` | `{source}` | {seed} | {difficulty} | {nodes} | {edges} | {switches} | "
                "{parTaps} | {timeLimit} | {quality_summary} | {preview} | `{signature_summary}` | {status} |".format(
                    source=source,
                    quality_summary=quality_summary,
                    preview=preview,
                    signature_summary=signature_summary,
                    **level,
                )
            )
        if not payload["acceptedLevels"]:
            lines.append("| _None_ |  |  |  |  |  |  |  |  |  |  |  | failed |")

        if payload["acceptedLevels"]:
            lines.extend(["", "## Level Details", ""])
            for level in payload["acceptedLevels"]:
                lines.append(f"### `{level['levelID']}`")
                if level["recipeFamily"]:
                    lines.append(
                        f"- Recipe: `{level['recipeFamily']}` variant `{level['recipeVariant']}`; "
                        f"abstract signature `{level['abstractGraphSignatureShort']}`."
                    )
                    lines.append(
                        f"- Layout: `{level['selectedLayoutVariant']}`; "
                        f"road shapes: `{level['selectedRoadShapeStrategy']}`."
                    )
                for switch in level["switchPreview"]:
                    transition_summary = ", ".join(
                        (
                            f"tap {transition['tapSequence']} @ {transition['timeSeconds']:.2f}s"
                            f" -> `{transition['targetEdgeID']}` ({transition['postTapArrowDirection']})"
                        )
                        for transition in switch["tapTransitions"]
                    ) or "no scripted taps"
                    lines.append(
                        f"- Switch `{switch['switchID']}` starts on `{switch['initialActiveEdgeID']}` "
                        f"({switch['initialArrowDirection']}); {transition_summary}."
                    )
                for warning in level["warnings"]:
                    lines.append(f"- Warning: {warning}")
                if not level["switchPreview"] and not level["warnings"]:
                    lines.append("- No switch-specific review notes.")

        lines.extend(["", "## Rejections", ""])
        lines.append(f"- Rejected candidates: `{payload['rejectedCandidateCount']}`")
        for reason, count in sorted(payload["rejectionReasonCounts"].items()):
            lines.append(f"- `{reason}`: {count}")

        if payload["messages"]:
            lines.extend(["", "## Messages", ""])
            for message in payload["messages"]:
                lines.append(f"- {message}")

        if payload["recommendations"]:
            lines.extend(["", "## Recommendations", ""])
            for recommendation in payload["recommendations"]:
                lines.append(f"- {recommendation}")

        lines.extend(
            [
                "",
                "## Swift Test Summary",
                "",
                f"- Command: `{ ' '.join(payload['swiftTests']['command']) if payload['swiftTests']['command'] else 'not run' }`",
                f"- Result: `{payload['swiftTests']['summary']}`",
                "",
                "## Next Steps",
                "",
                "- Open generated levels in the Level Editor.",
                "- Run Python validation and Swift solvability before committing production levels.",
                "- `xcodegen generate` runs automatically for default production output; rerun it manually if resources were deleted outside the generator.",
                "",
            ]
        )
        return "\n".join(lines)

    def _write_previews(self, report_dir: Path, result) -> None:
        if not result.accepted:
            return
        preview_dir = report_dir / "previews"
        for level in result.accepted:
            if level.preview_path is None:
                self.preview_image_service.write_preview(level, preview_dir)

    def _signature_payload(self, level) -> dict[str, Any] | None:
        signature = getattr(level, "candidate_signature", None)
        if signature is None:
            return None
        return {
            "levelID": signature.level_id,
            "template": signature.template_name,
            "difficulty": signature.difficulty,
            "nodeCount": signature.node_count,
            "edgeCount": signature.edge_count,
            "switchCount": signature.switch_count,
            "requiredTapCount": signature.required_tap_count,
            "deadEndCount": signature.dead_end_count,
            "maxOutgoingEdgeCount": signature.max_outgoing_edge_count,
            "hasFourWaySwitch": signature.has_four_way_switch,
            "centralSwitchRevisitCount": signature.central_switch_revisit_count,
            "topologyHash": signature.topology_hash,
            "topologyHashShort": signature.topology_hash[:8],
            "layoutHash": signature.layout_hash,
            "layoutHashShort": signature.layout_hash[:8],
            "solutionHash": signature.solution_hash,
            "solutionHashShort": signature.solution_hash[:8],
            "normalizedPositions": list(signature.normalized_positions),
        }

    def _quality_payload(self, level) -> dict[str, Any] | None:
        quality = getattr(level, "quality_score", None)
        if quality is None:
            return None
        return {
            "total": quality.total,
            "readability": quality.readability,
            "uniqueness": quality.uniqueness,
            "difficultyFit": quality.difficulty_fit,
            "routeInterest": quality.route_interest,
            "penalties": list(quality.penalties),
            "details": quality.details,
        }

    def _simulation_payload(self, level) -> dict[str, Any] | None:
        simulation = getattr(level, "simulation_result", None)
        if simulation is None:
            return None
        return {
            "passed": simulation.passed,
            "outcome": simulation.outcome,
            "failureReason": simulation.failure_reason,
            "elapsedTimeSeconds": simulation.elapsed_time_seconds,
            "tapCount": simulation.tap_count,
            "reachedPackage": simulation.reached_package,
            "reachedDestination": simulation.reached_destination,
        }

    def _switch_preview_payload(self, level) -> list[dict[str, Any]]:
        level_document = level.level_document
        node_by_id = {node.id: node for node in level_document.graph.nodes}
        edge_by_id = {edge.id: edge for edge in level_document.graph.edges}
        visual_reports_by_switch_id = {
            report.switch_id: report
            for report in self.switch_visual_clarity.report_for_level(level_document)
        }
        direction_by_edge_id = {
            direction.edge_id: direction
            for report in visual_reports_by_switch_id.values()
            for direction in report.directions
        }
        actions_by_node_id: dict[str, list[Any]] = {}
        for action in sorted(level.solution.actions, key=lambda action: float(action.timeSeconds)):
            actions_by_node_id.setdefault(action.tapNodeID, []).append(action)

        switch_previews: list[dict[str, Any]] = []
        for node in level_document.graph.nodes:
            valid_edges = [
                edge_by_id[edge_id]
                for edge_id in node.outgoingEdgeIDs
                if edge_id in edge_by_id and edge_by_id[edge_id].fromNodeID == node.id
            ]
            if len(valid_edges) < 2:
                continue

            active_index = 0
            initial_edge = valid_edges[active_index]
            visual_report = visual_reports_by_switch_id.get(node.id)
            switch_preview = {
                "switchID": node.id,
                "initialActiveEdgeID": initial_edge.id,
                "initialTargetNodeID": initial_edge.toNodeID,
                "initialArrowDirection": self._edge_direction_label(initial_edge, direction_by_edge_id, node_by_id),
                "visualDirectionBuckets": [
                    {
                        "edgeID": direction.edge_id,
                        "targetNodeID": direction.target_node_id,
                        "bucket": direction.bucket,
                        "angle": direction.angle,
                        "ambiguous": direction.is_ambiguous,
                        "ambiguousReason": direction.ambiguous_reason,
                    }
                    for direction in (visual_report.directions if visual_report is not None else [])
                ],
                "tapTransitions": [],
            }

            for tap_index, action in enumerate(actions_by_node_id.get(node.id, []), start=1):
                active_index = (active_index + 1) % len(valid_edges)
                target_edge = valid_edges[active_index]
                switch_preview["tapTransitions"].append(
                    {
                        "tapSequence": tap_index,
                        "timeSeconds": float(action.timeSeconds),
                        "targetEdgeID": target_edge.id,
                        "targetNodeID": target_edge.toNodeID,
                        "postTapArrowDirection": self._edge_direction_label(
                            target_edge,
                            direction_by_edge_id,
                            node_by_id,
                        ),
                    }
                )

            switch_previews.append(switch_preview)
        return switch_previews

    def _edge_direction_label(self, edge, direction_by_edge_id, node_by_id) -> str:
        direction = direction_by_edge_id.get(edge.id)
        if direction is not None and direction.bucket is not None:
            return direction.bucket
        from_node = node_by_id.get(edge.fromNodeID)
        to_node = node_by_id.get(edge.toNodeID)
        if from_node is None or to_node is None:
            return "east"
        angle = self.route_timing.direction_angle(
            (from_node.x, from_node.y),
            (to_node.x, to_node.y),
            edge.roadShape,
        )
        return self.route_timing.direction_label(angle)

    def _recommendations(self, config, result) -> list[str]:
        if getattr(result, "passed", True):
            return []
        rejection_counts = dict(getattr(result, "rejection_reason_counts", {}))
        if not rejection_counts:
            return []

        most_common_reason = max(rejection_counts.items(), key=lambda item: item[1])[0]
        recommendations: list[str] = [f"Most common rejection: `{most_common_reason}`."]
        if most_common_reason == "candidate_too_similar_to_batch":
            recommendations.extend(
                [
                    "Increase `--candidate-pool-size`.",
                    "Enable more hard templates with `--swift-tests`.",
                    "Use `--difficulty auto` instead of hard-only.",
                    "Generate fewer levels per batch.",
                    "Add a new hard template variant.",
                ]
            )
        elif most_common_reason == "solution_tap_not_before_switch_arrival":
            recommendations.extend(
                [
                    "Increase timed-tap lead time or route the switch earlier in the path.",
                    "Review switch preview metadata for dead-end-first defaults.",
                    "Run with `--swift-tests` before writing production files.",
                ]
            )
        return recommendations
