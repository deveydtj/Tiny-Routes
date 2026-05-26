from __future__ import annotations

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.services.python_solution_simulator_service import PythonSolutionSimulatorService
from app.templates.four_way_intersection_template import FourWayIntersectionTemplate


def test_four_way_intersection_template_generates_valid_expert_level() -> None:
    preset = DifficultyService().get_preset("expert")
    generated = FourWayIntersectionTemplate().generate("level_099", 99, preset, RandomSource(4))

    central = next(node for node in generated.level_document.graph.nodes if node.id == "central_switch")
    assert len(central.outgoingEdgeIDs) == 4

    validation = GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True)
    assert not validation.has_errors, [message.message for message in validation.messages if message.severity == "error"]

    simulation = PythonSolutionSimulatorService().simulate(generated)
    assert simulation.passed is True
    assert simulation.reached_package is True
    assert simulation.reached_destination is True


def test_four_way_intersection_template_has_layout_variants() -> None:
    preset = DifficultyService().get_preset("expert")
    packages = {
        (
            next(node for node in generated.level_document.graph.nodes if node.id == "package").x,
            next(node for node in generated.level_document.graph.nodes if node.id == "package").y,
        )
        for generated in [
            FourWayIntersectionTemplate().generate("level_099", 99, preset, RandomSource(seed))
            for seed in range(8)
        ]
    }

    assert len(packages) > 1
