import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.services import TestRunnerResult, TestRunnerService


def test_test_runner_result_can_represent_success() -> None:
    result = TestRunnerResult(
        command=["xcodebuild", "test"],
        exit_code=0,
        stdout="ok",
        stderr="",
        passed=True,
        summary="Passed",
    )

    assert result.passed is True
    assert result.exit_code == 0


def test_run_tests_reports_success(tmp_path: Path) -> None:
    service = TestRunnerService(tmp_path)
    completed = subprocess.CompletedProcess(
        args=service.build_command(),
        returncode=0,
        stdout="Test Suite passed",
        stderr="",
    )

    with patch("app.services.test_runner_service.subprocess.run", return_value=completed) as run:
        result = service.run_tests()

    run.assert_called_once()
    assert run.call_args.kwargs["cwd"] == tmp_path
    assert run.call_args.kwargs["capture_output"] is True
    assert run.call_args.kwargs["text"] is True
    assert result.command == service.build_command()
    assert result.exit_code == 0
    assert result.stdout == "Test Suite passed"
    assert result.stderr == ""
    assert result.passed is True
    assert result.summary == "Swift solvability tests passed."


def test_run_tests_reports_failure(tmp_path: Path) -> None:
    service = TestRunnerService(tmp_path)
    completed = subprocess.CompletedProcess(
        args=service.build_command(),
        returncode=65,
        stdout="Testing failed",
        stderr="simulator unavailable",
    )

    with patch("app.services.test_runner_service.subprocess.run", return_value=completed):
        result = service.run_tests()

    assert result.exit_code == 65
    assert result.stdout == "Testing failed"
    assert result.stderr == "simulator unavailable"
    assert result.passed is False
    assert "exit code 65" in result.summary


def test_run_tests_reports_missing_xcodebuild(tmp_path: Path) -> None:
    service = TestRunnerService(tmp_path)

    with patch("app.services.test_runner_service.subprocess.run", side_effect=FileNotFoundError("xcodebuild")):
        result = service.run_tests()

    assert result.exit_code == 127
    assert result.stdout == ""
    assert "xcodebuild" in result.stderr
    assert result.passed is False
    assert "xcodebuild was not found" in result.summary


def test_run_tests_reports_timeout(tmp_path: Path) -> None:
    service = TestRunnerService(tmp_path, timeout_seconds=3)
    timeout = subprocess.TimeoutExpired(
        cmd=service.build_command(),
        timeout=3,
        output=b"partial stdout",
        stderr=b"partial stderr",
    )

    with patch("app.services.test_runner_service.subprocess.run", side_effect=timeout):
        result = service.run_tests()

    assert result.exit_code == 124
    assert result.stdout == "partial stdout"
    assert result.stderr == "partial stderr"
    assert result.passed is False
    assert "timed out after 3 seconds" in result.summary
