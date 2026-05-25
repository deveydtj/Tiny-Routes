from __future__ import annotations

from app.random_source import RandomSource
from app.services.candidate_rejection_service import CandidateRejectionService
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratorValidationMessage, GeneratorValidationResult
from app.templates.single_switch_template import SingleSwitchTemplate


def test_candidate_rejection_counts_first_error() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(10))
    service = CandidateRejectionService()
    validation = GeneratorValidationResult(
        messages=[GeneratorValidationMessage(severity="error", code="duplicate_edge_id", message="duplicate")]
    )

    message = service.record_rejection(generated, validation)

    assert "duplicate_edge_id" in message
    assert service.reason_counts["duplicate_edge_id"] == 1
