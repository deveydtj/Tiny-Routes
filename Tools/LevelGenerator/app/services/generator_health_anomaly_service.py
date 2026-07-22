"""Baseline-aware anomaly thresholds for generator CI and stress runs."""

from __future__ import annotations

import json
from pathlib import Path

from ..models.generator_health import (
    GeneratorHealthAnomaly,
    GeneratorHealthAnomalyReport,
    GeneratorHealthReport,
    GeneratorHealthSlice,
    GeneratorHealthThresholds,
)


class GeneratorHealthAnomalyError(RuntimeError):
    """Raised when a CI/stress health gate contains one or more anomalies."""

    def __init__(self, report: GeneratorHealthAnomalyReport) -> None:
        self.report = report
        codes = ", ".join(report.rejection_codes)
        super().__init__(f"generator_health_anomaly: {codes}")


class GeneratorHealthAnomalyService:
    """Compare one health snapshot with its locked baseline and limits."""

    def __init__(
        self,
        thresholds: GeneratorHealthThresholds | None = None,
    ) -> None:
        self.thresholds = thresholds or GeneratorHealthThresholds()

    def assess(
        self,
        current: GeneratorHealthReport,
        *,
        baseline: GeneratorHealthReport | None = None,
    ) -> GeneratorHealthAnomalyReport:
        if not isinstance(current, GeneratorHealthReport):
            raise TypeError("current must be a GeneratorHealthReport")
        if baseline is not None and not isinstance(baseline, GeneratorHealthReport):
            raise TypeError("baseline must be a GeneratorHealthReport or None")

        anomalies: list[GeneratorHealthAnomaly] = []
        self._assess_run_completion(current, baseline, anomalies)
        self._assess_static_policy_output(current.overall, anomalies)
        self._assess_slice(
            current.overall,
            baseline.overall if baseline else None,
            anomalies,
        )

        baseline_difficulties = (
            {item.key: item for item in baseline.by_difficulty}
            if baseline is not None
            else {}
        )
        for cohort in current.by_difficulty:
            reference = baseline_difficulties.get(cohort.key)
            self._assess_static_policy_output(cohort, anomalies)
            self._assess_slice(cohort, reference, anomalies)
            if reference is not None:
                self._assess_decision_drift(cohort, reference, anomalies)

        self._assess_duplicate_rate(current, baseline, anomalies)
        return GeneratorHealthAnomalyReport(
            current_root_seed=current.root_seed,
            baseline_root_seed=baseline.root_seed if baseline else None,
            thresholds=self.thresholds,
            anomalies=tuple(
                sorted(
                    set(anomalies),
                    key=lambda item: (
                        item.code,
                        item.cohort,
                        item.metric,
                        item.actual,
                        item.required,
                        float("-inf") if item.baseline is None else item.baseline,
                    ),
                )
            ),
        )

    def require_healthy(
        self,
        current: GeneratorHealthReport,
        *,
        baseline: GeneratorHealthReport | None = None,
    ) -> GeneratorHealthAnomalyReport:
        report = self.assess(current, baseline=baseline)
        if not report.passed:
            raise GeneratorHealthAnomalyError(report)
        return report

    def write(self, report: GeneratorHealthAnomalyReport, path: Path) -> Path:
        if not isinstance(report, GeneratorHealthAnomalyReport):
            raise TypeError("report must be a GeneratorHealthAnomalyReport")
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output

    def _assess_run_completion(
        self,
        current: GeneratorHealthReport,
        baseline: GeneratorHealthReport | None,
        anomalies: list[GeneratorHealthAnomaly],
    ) -> None:
        if not self.thresholds.require_completed_run or current.run_completed:
            return
        code = (
            "full_run_completion_dropped"
            if baseline is not None and baseline.run_completed
            else "full_run_incomplete"
        )
        anomalies.append(
            GeneratorHealthAnomaly(
                code=code,
                cohort="all",
                metric="run_completed",
                actual=0.0,
                baseline=(1.0 if baseline and baseline.run_completed else 0.0)
                if baseline is not None
                else None,
                required="complete full requested run",
            )
        )

    @staticmethod
    def _assess_static_policy_output(
        cohort: GeneratorHealthSlice,
        anomalies: list[GeneratorHealthAnomaly],
    ) -> None:
        count = cohort.static_policy_solvable_output_count
        if count:
            anomalies.append(
                GeneratorHealthAnomaly(
                    code="static_policy_solvable_output",
                    cohort=cohort.key,
                    metric="static_policy_solvable_output_count",
                    actual=float(count),
                    required="exactly zero accepted static-policy-solvable outputs",
                )
            )

    def _assess_slice(
        self,
        current: GeneratorHealthSlice,
        baseline: GeneratorHealthSlice | None,
        anomalies: list[GeneratorHealthAnomaly],
    ) -> None:
        if current.attempt_count < self.thresholds.minimum_attempt_count:
            return

        minimum_yield = self.thresholds.minimum_candidate_yield
        baseline_yield = None
        if baseline is not None:
            baseline_yield = baseline.candidate_yield
            minimum_yield = max(
                minimum_yield,
                baseline_yield - self.thresholds.maximum_candidate_yield_drop,
            )
        if current.candidate_yield < minimum_yield:
            anomalies.append(
                GeneratorHealthAnomaly(
                    code="candidate_yield_below_baseline",
                    cohort=current.key,
                    metric="candidate_yield",
                    actual=current.candidate_yield,
                    baseline=baseline_yield,
                    required=f"at least {round(minimum_yield, 9)}",
                )
            )

        current_code, current_share = self._dominant_rejection(current)
        if current_code is None:
            return
        baseline_share = (
            self._rejection_share(baseline, current_code)
            if baseline is not None
            else 0.0
        )
        if (
            current_share > self.thresholds.maximum_dominant_rejection_share
            and current_share - baseline_share
            > self.thresholds.maximum_dominant_rejection_share_increase
        ):
            anomalies.append(
                GeneratorHealthAnomaly(
                    code="rejection_code_dominance",
                    cohort=current.key,
                    metric=f"rejection_share:{current_code}",
                    actual=current_share,
                    baseline=baseline_share if baseline is not None else None,
                    required=(
                        "share at or below "
                        f"{self.thresholds.maximum_dominant_rejection_share} or "
                        "baseline increase at or below "
                        f"{self.thresholds.maximum_dominant_rejection_share_increase}"
                    ),
                )
            )

    def _assess_decision_drift(
        self,
        current: GeneratorHealthSlice,
        baseline: GeneratorHealthSlice,
        anomalies: list[GeneratorHealthAnomaly],
    ) -> None:
        if current.attempt_count < self.thresholds.minimum_attempt_count:
            return
        current_metrics = dict(current.mean_decision_metrics)
        baseline_metrics = dict(baseline.mean_decision_metrics)
        for metric in sorted(current_metrics.keys() & baseline_metrics.keys()):
            current_value = current_metrics[metric]
            baseline_value = baseline_metrics[metric]
            drift = abs(current_value - baseline_value) / max(abs(baseline_value), 1.0)
            if drift > self.thresholds.maximum_decision_metric_drift:
                anomalies.append(
                    GeneratorHealthAnomaly(
                        code="difficulty_metric_drift",
                        cohort=current.key,
                        metric=metric,
                        actual=drift,
                        baseline=baseline_value,
                        required=(
                            "relative drift at or below "
                            f"{self.thresholds.maximum_decision_metric_drift}; "
                            f"current value {round(current_value, 9)}"
                        ),
                    )
                )

    def _assess_duplicate_rate(
        self,
        current: GeneratorHealthReport,
        baseline: GeneratorHealthReport | None,
        anomalies: list[GeneratorHealthAnomaly],
    ) -> None:
        if current.portfolio_diversity.selected_count < 2:
            return
        duplicate_rate = 1.0 - current.portfolio_diversity.behavior_ratio
        baseline_rate = (
            1.0 - baseline.portfolio_diversity.behavior_ratio
            if baseline is not None and baseline.portfolio_diversity.selected_count >= 2
            else 0.0
        )
        if (
            duplicate_rate > self.thresholds.maximum_behavior_duplicate_rate
            and duplicate_rate - baseline_rate
            > self.thresholds.maximum_behavior_duplicate_rate_increase
        ):
            anomalies.append(
                GeneratorHealthAnomaly(
                    code="behavior_duplicate_rate_rise",
                    cohort="portfolio",
                    metric="behavior_duplicate_rate",
                    actual=duplicate_rate,
                    baseline=baseline_rate if baseline is not None else None,
                    required=(
                        "rate at or below "
                        f"{self.thresholds.maximum_behavior_duplicate_rate} or "
                        "baseline increase at or below "
                        f"{self.thresholds.maximum_behavior_duplicate_rate_increase}"
                    ),
                )
            )

    @staticmethod
    def _dominant_rejection(cohort: GeneratorHealthSlice) -> tuple[str | None, float]:
        if not cohort.dominant_rejections:
            return None, 0.0
        code, _ = cohort.dominant_rejections[0]
        return code, GeneratorHealthAnomalyService._rejection_share(cohort, code)

    @staticmethod
    def _rejection_share(cohort: GeneratorHealthSlice, code: str) -> float:
        rejected_count = cohort.attempt_count - cohort.accepted_candidate_count
        if rejected_count <= 0:
            return 0.0
        count = next(
            (
                count
                for rejection_code, count in cohort.dominant_rejections
                if rejection_code == code
            ),
            0,
        )
        return round(count / rejected_count, 9)

    assess_health = assess
    assert_healthy = require_healthy
