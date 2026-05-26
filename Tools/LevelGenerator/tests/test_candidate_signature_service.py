from __future__ import annotations

from copy import deepcopy

from app.random_source import RandomSource
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.templates.package_gate_template import PackageGateTemplate
from app.templates.single_switch_template import SingleSwitchTemplate


def test_same_generated_level_gets_same_signature() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(10))
    service = CandidateSignatureService()

    assert service.signature_for(generated) == service.signature_for(generated)


def test_changing_edge_changes_topology_hash() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(10))
    changed = deepcopy(generated)
    changed.level_document.graph.edges[0].toNodeID = "package"
    service = CandidateSignatureService()

    assert service.signature_for(generated).topology_hash != service.signature_for(changed).topology_hash


def test_changing_node_positions_changes_layout_hash() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(10))
    changed = deepcopy(generated)
    changed.level_document.graph.nodes[0].x += 0.25
    service = CandidateSignatureService()

    assert service.signature_for(generated).layout_hash != service.signature_for(changed).layout_hash


def test_changing_solution_tap_order_changes_solution_hash() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = PackageGateTemplate().generate("level_012", 12, preset, RandomSource(10))
    changed = deepcopy(generated)
    changed.solution.actions[0].tapNodeID = "finish_switch"
    changed.solution.actions[1].tapNodeID = "approach_switch"
    service = CandidateSignatureService()

    assert service.signature_for(generated).solution_hash != service.signature_for(changed).solution_hash
