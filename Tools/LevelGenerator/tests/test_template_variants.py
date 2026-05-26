from __future__ import annotations

from app.random_source import RandomSource
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.templates.multi_switch_chain_template import MultiSwitchChainTemplate
from app.templates.package_gate_template import PackageGateTemplate
from app.templates.return_loop_template import ReturnLoopTemplate
from app.templates.ring_route_template import RingRouteTemplate
from app.templates.single_switch_template import SingleSwitchTemplate


def test_requested_template_variant_names_are_registered() -> None:
    names = {
        spec.name
        for template in [
            SingleSwitchTemplate(),
            PackageGateTemplate(),
            MultiSwitchChainTemplate(),
            ReturnLoopTemplate(),
            RingRouteTemplate(),
        ]
        for spec in template.variant_specs
    }

    assert {
        "single_switch_upper_package",
        "single_switch_lower_package",
        "single_switch_short_dead_end",
        "package_gate_left_entry",
        "package_gate_right_entry",
        "package_gate_crossing_avoidance",
        "multi_switch_chain_zigzag",
        "multi_switch_chain_stair_step",
        "multi_switch_chain_split_dead_ends",
        "return_loop_upper",
        "return_loop_lower",
        "package_gate_double_choice",
        "ring_route_clockwise",
        "ring_route_counterclockwise",
        "ring_route_package_inside",
        "ring_route_package_outside",
        "multi_switch_chain_four_switch",
        "multi_switch_chain_double_gate",
    }.issubset(names)


def test_easy_medium_and_hard_variants_validate_and_vary_layout_hashes() -> None:
    validator = GeneratedLevelValidationService()
    signature_service = CandidateSignatureService()
    cases = [
        (SingleSwitchTemplate(), "easy", range(1, 8)),
        (PackageGateTemplate(), "medium", range(1, 10)),
        (MultiSwitchChainTemplate(), "hard", range(1, 10)),
        (RingRouteTemplate(), "hard", range(1, 10)),
    ]

    for template, difficulty, seeds in cases:
        preset = DifficultyService().get_preset(difficulty)
        hashes = set()
        for seed in seeds:
            generated = template.generate("level_012", 12, preset, RandomSource(seed))
            assert not validator.validate(generated, preset=preset, overwrite=True).has_errors
            hashes.add(signature_service.signature_for(generated).layout_hash)
        assert len(hashes) >= 2
