from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .generated_level_validation_service import GeneratorValidationMessage, GeneratorValidationResult
from .state_snapshot_preview_service import StateSnapshotPreviewService


class CandidateRejectionService:
    VALIDATION_STAGE_ORDER = (
        "topology_validation",
        "unique_solution_validation",
        "shortcut_validation",
        "package_validation",
        "rejoin_validation",
        "revisit_validation",
        "layout_readability_validation",
        "road_shape_validation",
        "runtime_parity_validation",
        "quality_scoring",
        "candidate_selection",
    )

    LAYOUT_READABILITY_REJECTION_CODES = {
        "implicit_intersection_without_node",
        "switch_exit_overlap",
        "node_spacing_failure",
        "start_goal_separation_failure",
        "road_proximity_failure",
        "important_node_visibility_failure",
        "portrait_safety_failure",
    }
    ROAD_SHAPE_REJECTION_PREFIXES = (
        "ambiguous_switch_exit",
        "conflicting_direction_bucket",
        "insufficient_exit_separation",
        "same_switch_first_segments_overlap",
        "required_and_wrong_route_first_segments_overlap",
        "road_crossing_near_important_node",
        "implicit_intersection_without_graph_node",
        "road_crosses_through_unconnected_node",
        "unconnected_road_endpoint_touches_segment",
        "unconnected_parallel_road_overlap",
        "return_loop_false_shortcut",
        "invalid_road_shape",
        "zero_length_edge",
        "unreadable_road_geometry",
        "road_visually_circles_back_on_itself",
        "revisited_switch_corridor_too_tight",
        "return_path_too_close_to_destination_branch",
        "non_adjacent_roads_too_close",
    )
    PACKAGE_REJECTION_CODES = {
        "package_required_but_unreachable",
        "destination_reachable_before_package",
        "package_bypass_detected",
        "package_state_ambiguous",
        "impossible_road_availability_condition",
        "irrelevant_road_availability_condition",
    }
    UNIQUE_SOLUTION_REJECTION_CODES = {
        "multiple_solutions_found",
        "unique_solution_not_proven",
        "no_valid_solution_found",
    }

    def __init__(self, *, include_state_snapshot_previews: bool = False) -> None:
        self.reason_counts: Counter[str] = Counter()
        self.include_state_snapshot_previews = include_state_snapshot_previews
        self.state_snapshot_previews = StateSnapshotPreviewService()

    def can_save(self, validation_result: GeneratorValidationResult) -> bool:
        return not validation_result.has_errors

    def record_rejection(
        self,
        generated_level,
        validation_result: GeneratorValidationResult,
        debug_failures_dir: Path | None = None,
    ) -> str:
        first_error = self.preferred_rejection_message(validation_result)
        reason = first_error.code if first_error is not None else "unknown"
        self.reason_counts[reason] += 1
        detail = first_error.message if first_error is not None else "No validation detail available."
        message = (
            f"Rejected candidate {generated_level.level_id} seed={generated_level.seed} "
            f"template={generated_level.template_name} reason={reason} detail={detail}"
        )
        generated_level.rejection_messages.append(message)
        if debug_failures_dir is not None:
            self._save_debug_candidate(generated_level, validation_result, debug_failures_dir)
        return message

    @classmethod
    def validation_stage_for_code(cls, code: str | None) -> str:
        code = str(code or "unknown")
        if code.startswith("quality_") or code.startswith("strategic_quality_") or code in {
            "large_portrait_without_puzzle_need",
            "boring_topology_for_difficulty",
        } or code.startswith("route_interest_below_"):
            return "quality_scoring"
        if code in {
            "missing_required_swift_validation",
            "swift_runtime_parity_failed",
            "solution_sidecar_runtime_mismatch",
            "switch_tap_runtime_mismatch",
            "package_order_runtime_mismatch",
        }:
            return "runtime_parity_validation"
        if code in {
            "candidate_too_similar_to_batch",
            "candidate_too_similar_to_existing",
            "not_selected",
            "candidate_selection_filtered",
        }:
            return "candidate_selection"
        if code in cls.LAYOUT_READABILITY_REJECTION_CODES or code.startswith("layout_") or code.startswith("portrait_layout"):
            return "layout_readability_validation"
        if code.startswith(cls.ROAD_SHAPE_REJECTION_PREFIXES):
            return "road_shape_validation"
        if "shortcut" in code:
            return "shortcut_validation"
        if code in cls.PACKAGE_REJECTION_CODES or "package" in code or "bypass" in code:
            return "package_validation"
        if "wrong_branch" in code:
            return "package_validation"
        if "rejoin" in code:
            return "rejoin_validation"
        if "revisit" in code or "repeated_node" in code:
            return "revisit_validation"
        if code in cls.UNIQUE_SOLUTION_REJECTION_CODES or "solution" in code:
            return "unique_solution_validation"
        if "topology" in code or code.startswith("declared_loop_") or code.startswith("candidate_generation"):
            return "topology_validation"
        return "topology_validation"

    def preferred_rejection_message(self, validation_result: GeneratorValidationResult) -> GeneratorValidationMessage | None:
        errors = [message for message in validation_result.messages if message.severity == "error"]
        return next(
            (message for message in errors if message.code in self.LAYOUT_READABILITY_REJECTION_CODES),
            errors[0] if errors else None,
        )

    def record_custom_rejection(
        self,
        generated_level,
        reason: str,
        detail: str,
        debug_failures_dir: Path | None = None,
    ) -> str:
        self.reason_counts[reason] += 1
        message = (
            f"Rejected candidate {generated_level.level_id} seed={generated_level.seed} "
            f"template={generated_level.template_name} reason={reason} detail={detail}"
        )
        generated_level.rejection_messages.append(message)
        if debug_failures_dir is not None:
            self._save_debug_candidate(
                generated_level,
                GeneratorValidationResult(
                    messages=[
                        GeneratorValidationMessage(
                            severity="error",
                            code=reason,
                            message=detail,
                        )
                    ]
                ),
                debug_failures_dir,
            )
        return message

    def _save_debug_candidate(self, generated_level, validation_result: GeneratorValidationResult, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        stem = f"{generated_level.level_id}_{generated_level.template_name}_{generated_level.seed}"
        (directory / f"{stem}.level.json").write_text(
            json.dumps(generated_level.level_document.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (directory / f"{stem}.solution.json").write_text(
            json.dumps(generated_level.solution.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (directory / f"{stem}.rejection.json").write_text(
            json.dumps([message.__dict__ for message in validation_result.messages], indent=2) + "\n",
            encoding="utf-8",
        )
        if self.include_state_snapshot_previews:
            self.state_snapshot_previews.write_generated_level_previews(
                generated_level,
                directory / f"{stem}.state-previews",
            )
