from __future__ import annotations

from app.random_source import RandomSource
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.generation_quality_service import GenerationQualityService
from app.templates.package_gate_template import PackageGateTemplate
from app.templates.single_switch_template import SingleSwitchTemplate


def test_generation_quality_service_scores_valid_candidate() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = PackageGateTemplate().generate("level_012", 12, preset, RandomSource(3))
    generated.candidate_signature = CandidateSignatureService().signature_for(generated)

    score = GenerationQualityService().score(generated, preset)

    assert 0 < score.total <= 1
    assert score.difficulty_fit == 1
    assert "switchCount" in score.details


def test_generation_quality_penalizes_similar_candidates() -> None:
    preset = DifficultyService().get_preset("easy")
    first = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))
    second = SingleSwitchTemplate().generate("level_013", 13, preset, RandomSource(2))
    signature_service = CandidateSignatureService()
    first.candidate_signature = signature_service.signature_for(first)
    second.candidate_signature = signature_service.signature_for(second)

    score = GenerationQualityService().score(second, preset, [first.candidate_signature])

    assert score.uniqueness < 0.2
    assert "similar_to_existing_candidate" in score.penalties
