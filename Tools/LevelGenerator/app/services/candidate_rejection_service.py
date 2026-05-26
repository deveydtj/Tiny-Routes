from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .generated_level_validation_service import GeneratorValidationMessage, GeneratorValidationResult


class CandidateRejectionService:
    def __init__(self) -> None:
        self.reason_counts: Counter[str] = Counter()

    def can_save(self, validation_result: GeneratorValidationResult) -> bool:
        return not validation_result.has_errors

    def record_rejection(
        self,
        generated_level,
        validation_result: GeneratorValidationResult,
        debug_failures_dir: Path | None = None,
    ) -> str:
        first_error = next((message for message in validation_result.messages if message.severity == "error"), None)
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
