from __future__ import annotations

import subprocess
from unittest.mock import patch

from app.services.swift_test_service import SwiftTestService


def test_swift_test_command_is_targeted(tmp_path) -> None:
    command = SwiftTestService(tmp_path).build_command()

    assert "-only-testing:TinyRoutesTests/LevelSolvabilityTests" in command
    assert "-only-testing:TinyRoutesTests/LevelSimulationHarnessTests" in command
    assert "-only-testing:TinyRoutesTests/LevelSolutionScriptTests" in command
    assert "-only-testing:TinyRoutesTests/RouteEngineTests" in command
    assert "-only-testing:TinyRoutesTests/SwitchNodeViewTests" in command


def test_swift_test_service_reports_missing_xcodebuild(tmp_path) -> None:
    service = SwiftTestService(tmp_path)

    with patch("app.services.swift_test_service.shutil.which", return_value=None):
        result = service.run()

    assert result.exit_code == 127
    assert result.passed is False


def test_swift_test_service_captures_success(tmp_path) -> None:
    service = SwiftTestService(tmp_path)
    completed = subprocess.CompletedProcess(args=service.build_command(), returncode=0, stdout="ok", stderr="")

    with patch("app.services.swift_test_service.shutil.which", return_value="/usr/bin/xcodebuild"), patch(
        "app.services.swift_test_service.subprocess.run",
        return_value=completed,
    ):
        result = service.run()

    assert result.passed is True
    assert result.exit_code == 0
