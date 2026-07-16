from __future__ import annotations

import json

from app.level_editor_imports import LevelDocument, Solution
from app.models.generated_level import GeneratedLevel
from app.paths import get_default_levels_directory, get_default_solutions_directory
from app.services.python_solution_simulator_service import PythonSolutionSimulatorService


def _load(level_id: str) -> tuple[dict, LevelDocument, Solution]:
    level_payload = json.loads(
        (get_default_levels_directory() / f"{level_id}.json").read_text(encoding="utf-8")
    )
    solution_payload = json.loads(
        (get_default_solutions_directory() / f"{level_id}.solution.json").read_text(encoding="utf-8")
    )
    return (
        level_payload,
        LevelDocument.from_dict(level_payload),
        Solution.from_dict(solution_payload),
    )


def test_first_three_levels_form_an_intentional_live_routing_tutorial() -> None:
    expected_actions = (0, 1, 2)
    expected_switches = (0, 1, 2)
    simulator = PythonSolutionSimulatorService()

    for index, (action_count, switch_count) in enumerate(
        zip(expected_actions, expected_switches), start=1
    ):
        level_id = f"level_{index:03d}"
        payload, level, solution = _load(level_id)
        switches = sum(
            len(node.outgoingEdgeIDs) >= 2
            for node in level.graph.nodes
        )

        assert payload["id"] == level_id
        assert payload["name"] == f"Level {index:03d}"
        assert payload["schemaVersion"] == 2
        assert payload["rules"]["switchInteractionMode"] == "liveLookahead"
        assert payload["rules"]["switchLookaheadSeconds"] >= 2.0
        assert payload["tutorialMessage"].strip()
        assert switches == switch_count
        assert len(solution.actions) == action_count
        assert solution.levelID == level_id
        assert simulator.simulate(
            GeneratedLevel(level, solution, "tutorial_migration", "tutorial", index)
        ).passed


def test_nonzero_tutorial_taps_are_not_accepted_at_time_zero() -> None:
    simulator = PythonSolutionSimulatorService()
    for level_id in ("level_002", "level_003"):
        _, level, solution = _load(level_id)
        for action in solution.actions:
            action.timeSeconds = 0.0

        result = simulator.simulate(
            GeneratedLevel(level, solution, "tutorial_migration", "tutorial", 0)
        )

        assert not result.passed
        assert result.failure_reason in {"tap_before_activation_window", "tap_cooldown_active"}
