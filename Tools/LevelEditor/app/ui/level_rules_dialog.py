from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QVBoxLayout,
)

from tiny_routes_core.models import LevelRules, SwitchInteractionMode


@dataclass(frozen=True)
class LevelRulesResult:
    rules: LevelRules
    schema_version: int


class LevelRulesDialog(QDialog):
    """Advanced, range-checked gameplay rule editor."""

    def __init__(self, rules: LevelRules, schema_version: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Level Rules")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.schema_label = QLabel(str(schema_version))
        form.addRow("Schema Version:", self.schema_label)
        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("switchInteractionModeCombo")
        self.mode_combo.addItem("Live Look-ahead", SwitchInteractionMode.LIVE_LOOKAHEAD)
        if rules.switch_interaction_mode is SwitchInteractionMode.LEGACY_GLOBAL:
            legacy_index = self.mode_combo.count()
            self.mode_combo.addItem(
                "Legacy Global (archive only)", SwitchInteractionMode.LEGACY_GLOBAL
            )
            legacy_item = self.mode_combo.model().item(legacy_index)
            legacy_item.setEnabled(False)
            legacy_item.setToolTip(
                "Archived levels can be opened and replayed, but new content cannot select legacy mode."
            )
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(rules.switch_interaction_mode)))
        form.addRow("Switch Interaction:", self.mode_combo)
        self.lookahead_spin = self._seconds_spin("switchLookaheadSpin", rules.switch_lookahead_seconds)
        self.cooldown_spin = self._seconds_spin("switchCooldownSpin", rules.switch_tap_cooldown_seconds)
        form.addRow("Look-ahead Seconds:", self.lookahead_spin)
        form.addRow("Tap Cooldown Seconds:", self.cooldown_spin)
        layout.addLayout(form)
        self.warning_label = QLabel()
        self.warning_label.setObjectName("legacyModeWarning")
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color: #b45309;")
        layout.addWidget(self.warning_label)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.mode_combo.currentIndexChanged.connect(self._update_warning)
        self._update_warning()

    @staticmethod
    def _seconds_spin(name: str, value) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setObjectName(name)
        spin.setRange(0.0, 60.0)
        spin.setDecimals(3)
        spin.setSingleStep(0.05)
        spin.setSuffix(" s")
        spin.setValue(float(value) if isinstance(value, (int, float)) else 0.0)
        return spin

    def _update_warning(self) -> None:
        legacy = (
            SwitchInteractionMode(self.mode_combo.currentData())
            is SwitchInteractionMode.LEGACY_GLOBAL
        )
        self.warning_label.setText(
            "Legacy mode is retained only for archived-file decoding and replay. "
            "Choose Live Look-ahead to migrate this level."
            if legacy else ""
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(not legacy)

    def result_value(self) -> LevelRulesResult:
        current = SwitchInteractionMode(self.mode_combo.currentData())
        rules = LevelRules(current, self.lookahead_spin.value(), self.cooldown_spin.value())
        return LevelRulesResult(rules, max(2, int(self.schema_label.text())))
