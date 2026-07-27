from __future__ import annotations

from app.models.production_campaign import ProductionCampaignResult
from app.production_cli import main_production


class _Service:
    def __init__(self, result) -> None:
        self.result = result
        self.config = None
        self.call_count = 0

    def run(self, config):
        self.call_count += 1
        self.config = config
        return self.result


class _FailingService:
    def run(self, config):
        raise ValueError(
            "unknown production V3 quality profile: "
            f"{config.quality_profile_version}"
        )


def test_production_cli_builds_locked_v3_request_and_prints_one_summary(tmp_path, capsys) -> None:
    service = _Service(
        ProductionCampaignResult(
            status="completed",
            run_id="run-12345",
            seed=12345,
            requested_count=2,
            selected_count=2,
            report_path=tmp_path / "report.json",
        )
    )

    code = main_production(
        [
            "--start", "31",
            "--count", "2",
            "--difficulty", "progressive",
            "--seed", "12345",
            "--swift-tests",
            "--quality-profile", "1.0.0",
            "--candidate-workers", "3",
            "--global-attempt-budget", "40",
            "--output-levels", str(tmp_path / "levels"),
            "--output-solutions", str(tmp_path / "solutions"),
            "--production-manifest", str(tmp_path / "manifest.json"),
            "--staging-root", str(tmp_path / "staging"),
        ],
        service=service,
    )

    assert code == 0
    assert service.config.seed == 12345
    assert service.config.difficulty == "progressive"
    assert service.config.run_swift_tests is True
    assert service.config.quality_profile_version == "1.0.0"
    assert service.config.candidate_workers == 3
    assert service.config.global_attempt_budget == 40
    assert service.call_count == 1
    assert capsys.readouterr().out.count("\n") == 1


def test_production_cli_returns_failure_status(tmp_path, capsys) -> None:
    service = _Service(
        ProductionCampaignResult(
            status="failed_no_changes",
            run_id="run-1",
            seed=1,
            requested_count=1,
            failure_reason="proof failed",
        )
    )

    code = main_production(
        ["--start", "31", "--count", "1", "--difficulty", "hard"],
        service=service,
    )

    assert code == 1
    assert "status=failed_no_changes" in capsys.readouterr().out


def test_production_cli_reports_unknown_quality_profile_without_traceback(capsys) -> None:
    code = main_production(
        [
            "--start", "31",
            "--count", "1",
            "--difficulty", "hard",
            "--quality-profile", "9.9.9",
        ],
        service=_FailingService(),
    )

    assert code == 2
    assert "unknown production V3 quality profile: 9.9.9" in capsys.readouterr().err
