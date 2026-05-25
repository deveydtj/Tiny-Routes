from __future__ import annotations

from pathlib import Path

from ..generation_config import GenerationConfig
from ..models.generation_result import GenerationResult, SwiftTestSummary
from ..services.level_generation_service import LevelGenerationService
from ..services.level_validation_runner_service import (
    ExistingLevelValidationConfig,
    ExistingLevelValidationResult,
    LevelValidationRunnerService,
    normalize_level_id,
)
from .gui_state import GuiGenerationState, parse_positive_int, to_generation_config


class GuiController:
    def __init__(
        self,
        generation_service=None,
        validation_service: LevelValidationRunnerService | None = None,
    ) -> None:
        self.generation_service = generation_service or LevelGenerationService()
        self.validation_service = validation_service or LevelValidationRunnerService()

    def generate_from_state(self, state: GuiGenerationState) -> GenerationResult:
        config = to_generation_config(state)
        return self.generation_service.generate(config)

    def validate_existing_levels(
        self,
        *,
        level_ids_text: str,
        difficulty: str | None,
        run_swift_tests: bool,
        levels_output_dir: str,
        solutions_output_dir: str,
        swift_timeout_seconds: str,
    ) -> ExistingLevelValidationResult:
        level_ids = parse_level_ids(level_ids_text)
        if not level_ids:
            raise ValueError("Enter at least one level ID to validate.")
        if not levels_output_dir.strip():
            raise ValueError("Levels output directory is required for validation.")
        if not solutions_output_dir.strip():
            raise ValueError("Solutions output directory is required for validation.")
        timeout = parse_positive_int(swift_timeout_seconds, "Swift timeout seconds")
        return self.validation_service.validate_existing_levels(
            ExistingLevelValidationConfig(
                level_ids=level_ids,
                difficulty=difficulty.strip() if difficulty and difficulty.strip() else None,
                run_swift_tests=run_swift_tests,
                levels_output_dir=Path(levels_output_dir).expanduser(),
                solutions_output_dir=Path(solutions_output_dir).expanduser(),
                swift_timeout_seconds=timeout,
            )
        )


def parse_level_ids(value: str) -> list[str]:
    parts = value.replace(",", " ").split()
    return [normalize_level_id(part) for part in parts]


def format_generation_result(result: GenerationResult) -> str:
    lines = [f"Status: {'Passed' if result.passed else 'Failed'}", ""]

    if result.accepted:
        lines.append("Accepted levels:")
        for level in result.accepted:
            lines.append(
                "  {level_id}: template={template} seed={seed} nodes={nodes} edges={edges} "
                "switches={switches} taps={taps}".format(
                    level_id=level.level_id,
                    template=level.template_name,
                    seed=level.seed,
                    nodes=level.node_count,
                    edges=level.edge_count,
                    switches=level.switch_count,
                    taps=level.required_tap_count,
                )
            )
            for note in level.generation_notes:
                lines.append(f"    note: {note}")
    else:
        lines.append("Accepted levels: none")

    lines.extend(["", f"Rejected candidates: {result.rejected_candidate_count}"])
    if result.rejection_reason_counts:
        lines.append("Rejection reasons:")
        for reason, count in sorted(result.rejection_reason_counts.items()):
            lines.append(f"  {reason}: {count}")

    _append_path_section(lines, "Written level files", result.written_level_paths)
    _append_path_section(lines, "Written solution files", result.written_solution_paths)

    if result.report_path or result.json_report_path:
        lines.extend(["", "Reports:"])
        if result.report_path:
            lines.append(f"  Markdown: {result.report_path}")
        if result.json_report_path:
            lines.append(f"  JSON: {result.json_report_path}")

    lines.extend(["", _format_swift_summary(result.swift_test_summary)])

    if result.messages:
        lines.extend(["", "Messages:"])
        for message in result.messages:
            lines.append(f"  {message}")

    return "\n".join(lines)


def format_validation_result(result: ExistingLevelValidationResult) -> str:
    lines = [f"Validation Status: {'Passed' if result.passed else 'Failed'}", ""]
    if result.validated_level_ids:
        lines.append("Validated levels:")
        for level_id in result.validated_level_ids:
            lines.append(f"  {level_id}")
    else:
        lines.append("Validated levels: none")

    lines.extend(["", _format_swift_summary(result.swift_summary)])

    if result.failures:
        lines.extend(["", "Failures:"])
        for failure in result.failures:
            lines.append(f"  {failure}")

    return "\n".join(lines)


def _append_path_section(lines: list[str], title: str, paths: list[Path]) -> None:
    if not paths:
        return
    lines.extend(["", f"{title}:"])
    for path in paths:
        lines.append(f"  {path}")


def _format_swift_summary(summary: SwiftTestSummary) -> str:
    if summary.passed is None:
        return "Swift: Not run"
    status = "Passed" if summary.passed else "Failed"
    return f"Swift: {status} ({summary.summary})"
