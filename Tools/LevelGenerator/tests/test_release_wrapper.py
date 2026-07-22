from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_all_checks.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("tiny_routes_run_all_checks", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_final_release_wrapper_wires_every_gate_and_writes_summary(
    tmp_path,
    monkeypatch,
) -> None:
    module = _load_module()
    calls: list[tuple[str, tuple[str, ...]]] = []

    def fake_run(name, command, cwd):
        calls.append((name, tuple(command)))
        if name == "python_suites":
            junit_dir = Path(command[command.index("--junit-dir") + 1])
            junit_dir.mkdir(parents=True, exist_ok=True)
            (junit_dir / "generator.xml").write_text(
                '<testsuite tests="12" failures="0" errors="0" skipped="1"/>',
                encoding="utf-8",
            )
        elif name == "production_content":
            output = Path(command[command.index("--json-output") + 1])
            output.write_text(
                json.dumps(
                    {
                        "passed": True,
                        "levelCount": 30,
                        "manifestSynchronized": True,
                        "nonSwiftGatesPassed": True,
                    }
                ),
                encoding="utf-8",
            )
        elif name == "generator_v3_stress":
            output_dir = Path(command[command.index("--output-dir") + 1])
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "stress_summary.json").write_text(
                json.dumps(
                    {
                        "campaignCount": 100,
                        "completeBatchCount": 100,
                        "requestedLevelCount": 3000,
                        "selectedLevelCount": 3000,
                        "parityErrorCount": 0,
                    }
                ),
                encoding="utf-8",
            )
        elif name == "transaction_tests":
            output = Path(command[command.index("--junitxml") + 1])
            output.write_text(
                '<testsuite tests="7" failures="0" errors="0" skipped="0"/>',
                encoding="utf-8",
            )
        return module.GateResult(name, tuple(command), 0)

    monkeypatch.setattr(module, "run", fake_run)
    monkeypatch.setattr(
        module,
        "_git_output",
        lambda repo_root, *args: "abc123" if args == ("rev-parse", "HEAD") else "",
    )

    exit_code = module.main(
        [
            "--swift-tests",
            "--production-content",
            "--generator-v3-stress",
            "--transaction-tests",
            "--reports-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    names = tuple(name for name, _ in calls)
    assert names == (
        "python_suites",
        "generator_smoke",
        "fixed_seed_regressions",
        "production_content",
        "generator_v3_stress",
        "transaction_tests",
        "swift_tests",
    )
    stress_command = dict(calls)["generator_v3_stress"]
    assert stress_command[stress_command.index("--campaign-count") + 1] == "100"
    assert stress_command[stress_command.index("--levels-per-campaign") + 1] == "30"
    assert stress_command[stress_command.index("--seed-range") + 1] == "1-100"
    assert "--require-complete-batches" in stress_command
    assert "--fail-on-one-tap" in stress_command
    assert "--fail-on-static-policy" in stress_command
    assert "--fail-on-parity-error" in stress_command

    summary = json.loads((tmp_path / "release_summary.json").read_text())
    assert summary["passed"] is True
    assert summary["releaseConfigurationComplete"] is True
    assert summary["commit"]["sha"] == "abc123"
    assert summary["qualityProfile"]["version"] == "1.0.0"
    assert summary["testTotals"] == {
        "tests": 19,
        "failures": 0,
        "errors": 0,
        "skipped": 1,
    }
    assert summary["campaignCompletion"]["selectedLevelCount"] == 3000
    assert summary["parity"]["swiftGatePassed"] is True
    assert summary["corpus"]["levelCount"] == 30
    assert (tmp_path / "release_summary.md").is_file()


def test_partial_release_invocation_is_not_a_final_release(
    tmp_path,
    monkeypatch,
) -> None:
    module = _load_module()
    monkeypatch.setattr(
        module,
        "run",
        lambda name, command, cwd: module.GateResult(name, tuple(command), 0),
    )
    monkeypatch.setattr(module, "_git_output", lambda repo_root, *args: "")

    exit_code = module.main(
        ["--production-content", "--reports-dir", str(tmp_path)]
    )

    summary = json.loads((tmp_path / "release_summary.json").read_text())
    assert exit_code == 1
    assert summary["passed"] is False
    assert summary["releaseConfigurationComplete"] is False
    assert any("Swift tests were not requested" in warning for warning in summary["knownNonBlockingWarnings"])
