from __future__ import annotations

from app.models.production_campaign import ProductionCampaignResult
from app.production_cli import main_production


class _Service:
    def __init__(self, result) -> None:
        self.result = result
        self.config = None

    def run(self, config):
        self.config = config
        return self.result


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
            "--difficulty", "auto",
            "--seed", "12345",
            "--swift-tests",
            "--output-levels", str(tmp_path / "levels"),
            "--output-solutions", str(tmp_path / "solutions"),
            "--production-manifest", str(tmp_path / "manifest.json"),
            "--staging-root", str(tmp_path / "staging"),
        ],
        service=service,
    )

    assert code == 0
    assert service.config.seed == 12345
    assert service.config.run_swift_tests is True
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
