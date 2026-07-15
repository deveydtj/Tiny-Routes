from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from app.services import (
    AutomatedCheckStatus,
    AutomatedChecksReport,
    PuzzleAnalysis,
)


class PuzzleAnalysisPanel(QWidget):
    analyze_requested = Signal()
    run_all_checks_requested = Signal()
    recommendation_activated = Signal(object)

    _METRICS = (
        ("decision_count", "Decision count"),
        ("unique_switches_used", "Unique switches used"),
        ("repeated_visits", "Repeated visits"),
        ("state_changes_on_revisit", "State changes on revisit"),
        ("independent_decision_ratio", "Independent-decision ratio"),
        ("equivalent_solutions", "Equivalent solutions"),
        ("failure_outcomes", "Failure outcomes"),
        ("activation_window_lengths", "Activation-window lengths"),
        ("decision_spacings", "Decision spacing"),
        ("estimated_difficulty", "Estimated difficulty"),
        ("legacy_front_load_possible", "Legacy front-load diagnostic"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(360)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(QLabel("Puzzle Analysis"))
        header.addStretch()
        self._analyze_button = QPushButton("Analyze")
        self._analyze_button.clicked.connect(
            lambda checked=False: self.analyze_requested.emit()
        )
        header.addWidget(self._analyze_button)
        outer.addLayout(header)

        imported_group = QGroupBox("Imported generator quality")
        imported_layout = QVBoxLayout(imported_group)
        self._imported_summary = QLabel("No generator quality data loaded.")
        self._imported_summary.setWordWrap(True)
        self._imported_factors = QListWidget()
        self._imported_factors.setMaximumHeight(110)
        imported_layout.addWidget(self._imported_summary)
        imported_layout.addWidget(self._imported_factors)
        outer.addWidget(imported_group)

        metrics_group = QGroupBox("Measured decision quality")
        metrics_layout = QGridLayout(metrics_group)
        self._metric_labels: dict[str, QLabel] = {}
        for row, (key, label) in enumerate(self._METRICS):
            metrics_layout.addWidget(QLabel(label), row, 0)
            value = QLabel("—")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setWordWrap(True)
            metrics_layout.addWidget(value, row, 1)
            self._metric_labels[key] = value
        metrics_layout.setColumnStretch(1, 1)
        outer.addWidget(metrics_group)

        recommendations_group = QGroupBox("Recommendations")
        recommendations_layout = QVBoxLayout(recommendations_group)
        self._recommendations = QListWidget()
        self._recommendations.setToolTip(
            "Double-click a recommendation to select its affected node."
        )
        self._recommendations.itemDoubleClicked.connect(
            self._on_recommendation_activated
        )
        recommendations_layout.addWidget(self._recommendations)
        outer.addWidget(recommendations_group)

        checks_group = QGroupBox("Automated checks")
        checks_layout = QVBoxLayout(checks_group)
        self._run_all_button = QPushButton("Run All Checks")
        self._run_all_button.setToolTip(
            "Validate, search, replay, diagnose front-loading, analyze quality, and run Swift parity tests."
        )
        self._run_all_button.clicked.connect(
            lambda checked=False: self.run_all_checks_requested.emit()
        )
        checks_layout.addWidget(self._run_all_button)
        self._checks = QListWidget()
        checks_layout.addWidget(self._checks)
        outer.addWidget(checks_group)
        outer.addStretch()

    def show_analysis(self, analysis: PuzzleAnalysis) -> None:
        values = {
            "decision_count": str(analysis.decision_count),
            "unique_switches_used": str(analysis.unique_switches_used),
            "repeated_visits": str(analysis.repeated_visits),
            "state_changes_on_revisit": str(analysis.state_changes_on_revisit),
            "independent_decision_ratio": f"{analysis.independent_decision_ratio:.0%}",
            "equivalent_solutions": str(analysis.equivalent_solutions),
            "failure_outcomes": self._format_failures(analysis.failure_outcomes),
            "activation_window_lengths": self._format_seconds(
                analysis.activation_window_lengths
            ),
            "decision_spacings": self._format_seconds(analysis.decision_spacings),
            "estimated_difficulty": analysis.estimated_difficulty,
            "legacy_front_load_possible": (
                "Possible" if analysis.legacy_front_load_possible else "Not possible"
            ),
        }
        for key, value in values.items():
            self._metric_labels[key].setText(value)

        self._recommendations.clear()
        if not analysis.recommendations:
            item = QListWidgetItem("No design recommendations.")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self._recommendations.addItem(item)
        else:
            for recommendation in analysis.recommendations:
                item = QListWidgetItem(recommendation.message)
                item.setData(Qt.ItemDataRole.UserRole, recommendation)
                item.setToolTip(
                    f"Open node {recommendation.related_node_id}"
                    if recommendation.related_node_id
                    else recommendation.message
                )
                self._recommendations.addItem(item)

    def show_checks(self, report: AutomatedChecksReport) -> None:
        self._checks.clear()
        icons = {
            AutomatedCheckStatus.PASSED: QStyle.StandardPixmap.SP_DialogApplyButton,
            AutomatedCheckStatus.FAILED: QStyle.StandardPixmap.SP_MessageBoxCritical,
            AutomatedCheckStatus.WARNING: QStyle.StandardPixmap.SP_MessageBoxWarning,
        }
        for check in report.checks:
            item = QListWidgetItem(f"{check.label}: {check.summary}")
            item.setIcon(self.style().standardIcon(icons[check.status]))
            item.setData(Qt.ItemDataRole.UserRole, check)
            self._checks.addItem(item)
        self.show_analysis(report.analysis)

    def clear(self) -> None:
        for label in self._metric_labels.values():
            label.setText("—")
        self._recommendations.clear()
        self._checks.clear()
        self.clear_imported_quality()

    def show_imported_quality(self, payload: dict) -> None:
        quality = payload.get("quality") or {}
        score = quality.get("totalScore")
        score_text = "unscored" if score is None else f"score {float(score):.2f}"
        details = [
            str(payload.get("difficulty") or "unknown difficulty"),
            str(payload.get("template") or "unknown template"),
            f"seed {payload.get('seed', 'unknown')}",
            score_text,
        ]
        self._imported_summary.setText(" · ".join(details))
        self._imported_factors.clear()
        for label, values in (
            ("Strength", quality.get("topPositiveFactors") or ()),
            ("Concern", quality.get("topNegativeFactors") or ()),
            ("Penalty", quality.get("penalties") or ()),
        ):
            for value in values:
                self._imported_factors.addItem(f"{label}: {value}")
        if self._imported_factors.count() == 0:
            self._imported_factors.addItem("No imported quality factors.")

    def clear_imported_quality(self) -> None:
        self._imported_summary.setText("No generator quality data loaded.")
        self._imported_factors.clear()

    def set_checks_running(self, running: bool) -> None:
        self._run_all_button.setEnabled(not running)
        self._run_all_button.setText("Running Checks…" if running else "Run All Checks")

    def _on_recommendation_activated(self, item: QListWidgetItem) -> None:
        recommendation = item.data(Qt.ItemDataRole.UserRole)
        if recommendation is not None:
            self.recommendation_activated.emit(recommendation)

    def _format_failures(self, outcomes: tuple[tuple[str, int], ...]) -> str:
        if not outcomes:
            return "None"
        return ", ".join(f"{label}: {count}" for label, count in outcomes)

    def _format_seconds(self, values: tuple[float, ...]) -> str:
        if not values:
            return "None"
        return ", ".join(f"{value:.2f}s" for value in values)
