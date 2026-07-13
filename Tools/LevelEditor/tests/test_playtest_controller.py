import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from app.controllers import PlaytestController
from app.models import EditorTool
from app.repositories import LevelFileRepository, SolutionFileRepository
from app.services import RuntimeSolutionService
from app.ui import LevelCanvasScene


@pytest.fixture
def qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def level():
    path = Path(__file__).parent / "fixtures" / "valid_level.json"
    return LevelFileRepository().load_level(path)


def test_playtest_lifecycle_isolated_from_authored_document(qapplication, level) -> None:
    controller = PlaytestController()
    original_edge_order = list(level.graph.nodes[0].outgoingEdgeIDs)

    controller.start(level)
    controller.pause()
    controller.advance_by(0.25)

    assert controller.state.running is True
    assert controller.state.paused is True
    assert controller.state.elapsed_time == pytest.approx(0.25)
    assert level.graph.nodes[0].outgoingEdgeIDs == original_edge_order

    controller.reset()
    assert controller.state.elapsed_time == 0.0
    assert controller.state.accepted_taps == ()

    controller.stop()
    assert controller.state.running is False


def test_canvas_renders_and_clears_playtest_overlays(qapplication, level) -> None:
    controller = PlaytestController()
    scene = LevelCanvasScene()
    scene.display_level(level)
    scene.set_editor_tool(EditorTool.PLAYTEST)
    controller.state_changed.connect(scene.update_playtest_overlay)

    controller.start(level)
    controller.pause()

    assert scene._playtest_dot_item is not None
    assert scene._playtest_dot_item.isVisible()
    assert all(not item.flags() & item.GraphicsItemFlag.ItemIsMovable for item in scene._node_items_by_id.values())

    controller.stop()
    assert scene._playtest_dot_item is None


def test_completed_playtest_builds_replayable_solution(qapplication, level) -> None:
    controller = PlaytestController()
    controller.start(level)
    controller.pause()
    controller.advance_by(10.0)

    solution = controller.recorded_solution()

    assert solution is not None
    assert solution.levelID == level.id
    assert solution.expectedOutcome == "completed"
    assert solution.requiresWithinTimeLimit is True
    assert solution.maxTaps == len(solution.actions) == 0
    assert solution.isPlaceholder is False


def test_incomplete_playtest_cannot_replace_solution(qapplication, level) -> None:
    controller = PlaytestController()
    controller.start(level)
    controller.pause()

    assert controller.recorded_solution() is None


def test_timeline_scrubbing_is_deterministic_and_preserves_solution(qapplication, level) -> None:
    solution_path = Path(__file__).parent / "fixtures" / "valid_solution.json"
    solution = SolutionFileRepository().load_solution(solution_path)
    original_actions = [(action.timeSeconds, action.tapNodeID) for action in solution.actions]
    controller = PlaytestController()
    controller.load_replay(level, solution)

    controller.scrub_to(0.35)
    first = controller.state
    controller.scrub_to(0.8)
    controller.scrub_to(0.35)
    second = controller.state

    assert first.current_node_id == second.current_node_id
    assert first.current_edge_id == second.current_edge_id
    assert first.edge_progress == pytest.approx(second.edge_progress)
    assert first.switch_active_edge_ids == second.switch_active_edge_ids
    assert [(action.timeSeconds, action.tapNodeID) for action in solution.actions] == original_actions


def test_runtime_solution_service_returns_only_verified_solution(level) -> None:
    service = RuntimeSolutionService()

    solution = service.find_verified(level)

    assert solution is not None
    assert service.replay(level, solution).passed is True
