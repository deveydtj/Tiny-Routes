from __future__ import annotations

import json
from types import SimpleNamespace

from app.gui.gui_controller import GuiController
from app.models.generated_level import GeneratedLevel
from app.models.decision_profile import DecisionProfile
from app.models.generation_quality import GenerationQualityScore


class _Serializable:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def to_dict(self) -> dict:
        return self._payload


def test_prepare_candidate_for_editor_writes_level_solution_and_quality(tmp_path) -> None:
    level = _Serializable({"id": "level_012", "graph": {"nodes": [], "edges": []}})
    level.id = "level_012"
    level.graph = SimpleNamespace(nodes=[], edges=[])
    solution = _Serializable({"levelID": "level_012", "actions": []})
    solution.actions = []
    candidate = GeneratedLevel(
        level_document=level,
        solution=solution,
        template_name="single_switch",
        difficulty="medium",
        seed=42,
        decision_profile=DecisionProfile(
            package_phase_transition_count=1,
            state_dependent_route_change_count=1,
            roads_opened_after_package_count=1,
        ),
        quality_score=GenerationQualityScore(
            total_score=82.5,
            category_scores={"logicScore": 0.9},
            total=0.825,
            readability=0.8,
            uniqueness=1.0,
            difficulty_fit=0.75,
            route_interest=0.8,
            top_positive_factors=("dependent choices",),
            top_negative_factors=("tight spacing",),
        ),
    )

    handoff = GuiController().prepare_candidate_for_editor(
        candidate, draft_directory=str(tmp_path)
    )

    assert handoff.level_path.parent.name == "level_012-seed-42"
    assert json.loads(handoff.level_path.read_text())["id"] == "level_012"
    assert json.loads(handoff.solution_path.read_text())["levelID"] == "level_012"
    quality = json.loads(handoff.quality_path.read_text())
    assert quality["levelID"] == "level_012"
    assert quality["quality"]["totalScore"] == 82.5
    assert quality["quality"]["topPositiveFactors"] == ["dependent choices"]
    assert quality["decisionQuality"]["packagePhaseTransitionCount"] == 1
    assert quality["decisionQuality"]["stateDependentRouteChangeCount"] == 1
    assert quality["decisionQuality"]["roadsOpenedAfterPackageCount"] == 1


def test_prepare_candidate_for_editor_requires_draft_directory() -> None:
    candidate = SimpleNamespace(level_id="level_001")

    try:
        GuiController().prepare_candidate_for_editor(candidate, draft_directory="  ")
    except ValueError as exc:
        assert str(exc) == "Editor draft directory is required."
    else:
        raise AssertionError("Expected blank draft directory to fail")
