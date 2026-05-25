from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..paths import find_repo_root


class GenerationReportRepository:
    def write_markdown(self, path: Path, config, result) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._markdown(config, result), encoding="utf-8")
        return path

    def write_json(self, path: Path, config, result) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
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
            f"- Xcode project sync: `{payload['syncXcodeProject']}`",
            f"- Swift tests: `{payload['swiftTests']['summary']}`",
            "",
            "## Accepted Levels",
            "",
            "| Level | Template | Seed | Difficulty | Nodes | Edges | Switches | Par Taps | Time Limit | Status |",
            "|---|---|---:|---|---:|---:|---:|---:|---:|---|",
        ]
        for level in payload["acceptedLevels"]:
            lines.append(
                "| `{levelID}` | `{template}` | {seed} | {difficulty} | {nodes} | {edges} | {switches} | "
                "{parTaps} | {timeLimit} | {status} |".format(**level)
            )
        if not payload["acceptedLevels"]:
            lines.append("| _None_ |  |  |  |  |  |  |  |  | failed |")

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
