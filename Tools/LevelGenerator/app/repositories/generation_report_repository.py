from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..paths import find_repo_root
from ..services.preview_image_service import PreviewImageService


class GenerationReportRepository:
    def __init__(self) -> None:
        self.preview_image_service = PreviewImageService()

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
            "baseSeed": config.seed,
            "dryRun": config.dry_run,
            "overwrite": config.overwrite,
            "syncXcodeProject": config.sync_xcode_project,
            "compareAgainstExisting": config.compare_against_existing,
            "candidatePoolSize": config.candidate_pool_size,
            "acceptedLevels": [
                {
                    "levelID": level.level_id,
                    "template": level.template_name,
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
                    "previewPath": str(level.preview_path) if level.preview_path else None,
                    "status": "passed",
                    "notes": level.generation_notes,
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
            f"- Base seed: `{payload['baseSeed']}`",
            f"- Dry run: `{payload['dryRun']}`",
            f"- Compare existing levels: `{payload['compareAgainstExisting']}`",
            f"- Candidate pool size: `{payload['candidatePoolSize']}`",
            f"- Xcode project sync: `{payload['syncXcodeProject']}`",
            f"- Swift tests: `{payload['swiftTests']['summary']}`",
            "",
            "## Accepted Levels",
            "",
            "| Level | Template | Seed | Difficulty | Nodes | Edges | Switches | Par Taps | Time Limit | Quality | Preview | Signatures | Status |",
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
            lines.append(
                "| `{levelID}` | `{template}` | {seed} | {difficulty} | {nodes} | {edges} | {switches} | "
                "{parTaps} | {timeLimit} | {quality_summary} | {preview} | `{signature_summary}` | {status} |".format(
                    quality_summary=quality_summary,
                    preview=preview,
                    signature_summary=signature_summary,
                    **level,
                )
            )
        if not payload["acceptedLevels"]:
            lines.append("| _None_ |  |  |  |  |  |  |  |  |  |  |  | failed |")

        lines.extend(["", "## Rejections", ""])
        lines.append(f"- Rejected candidates: `{payload['rejectedCandidateCount']}`")
        for reason, count in sorted(payload["rejectionReasonCounts"].items()):
            lines.append(f"- `{reason}`: {count}")

        if payload["messages"]:
            lines.extend(["", "## Messages", ""])
            for message in payload["messages"]:
                lines.append(f"- {message}")

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
