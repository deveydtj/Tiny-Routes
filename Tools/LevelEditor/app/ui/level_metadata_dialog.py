from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models import LevelDocument
from app.services import LevelIdentity, LevelIdentityService


@dataclass(frozen=True)
class LevelMetadataResult:
    identity: LevelIdentity
    level_name: str
    timeLimitSeconds: int
    parTaps: int


class LevelMetadataDialog(QDialog):
    def __init__(
        self,
        document: LevelDocument,
        *,
        suggested_level_number: int | None = None,
        title: str = "Edit Level Metadata",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)

        self._identity_service = LevelIdentityService()
        self._is_updating_name = False
        self._name_is_custom = False
        self._last_auto_name = ""

        initial_number = self._initial_level_number(document, suggested_level_number)
        initial_identity = self._identity_service.build_from_number(initial_number)
        self._last_auto_name = initial_identity.level_name
        self._name_is_custom = document.name not in {"New Level", initial_identity.level_name}

        outer = QVBoxLayout(self)
        form = QFormLayout()

        self._level_number_spinbox = QSpinBox()
        self._level_number_spinbox.setRange(1, 999)
        self._level_number_spinbox.setValue(initial_number)
        self._level_number_spinbox.valueChanged.connect(self._on_level_number_changed)
        form.addRow("Level Number:", self._level_number_spinbox)

        self._level_id_preview = QLabel(initial_identity.level_id)
        form.addRow("Level ID:", self._level_id_preview)

        self._level_name_edit = QLineEdit()
        self._level_name_edit.textChanged.connect(self._on_level_name_changed)
        self._set_name_text(
            document.name if self._name_is_custom else initial_identity.level_name
        )
        form.addRow("Level Name:", self._level_name_edit)

        self._time_limit_spinbox = QSpinBox()
        self._time_limit_spinbox.setRange(1, 9999)
        self._time_limit_spinbox.setValue(max(1, int(round(document.timeLimitSeconds))))
        form.addRow("Time Limit:", self._time_limit_spinbox)

        self._par_taps_spinbox = QSpinBox()
        self._par_taps_spinbox.setRange(0, 999)
        self._par_taps_spinbox.setValue(max(0, int(document.parTaps)))
        form.addRow("Par Taps:", self._par_taps_spinbox)

        outer.addLayout(form)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.rejected.connect(self.reject)
        apply_button = self._button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self.accept)
        outer.addWidget(self._button_box)

    def selected_identity(self) -> LevelIdentity:
        return self._identity_service.build_from_number(self._level_number_spinbox.value())

    def level_name(self) -> str:
        return self._level_name_edit.text().strip()

    def time_limit_seconds(self) -> int:
        return self._time_limit_spinbox.value()

    def par_taps(self) -> int:
        return self._par_taps_spinbox.value()

    def metadata_result(self) -> LevelMetadataResult:
        return LevelMetadataResult(
            identity=self.selected_identity(),
            level_name=self.level_name(),
            timeLimitSeconds=self.time_limit_seconds(),
            parTaps=self.par_taps(),
        )

    def _initial_level_number(
        self,
        document: LevelDocument,
        suggested_level_number: int | None,
    ) -> int:
        parsed_number = self._identity_service.try_parse_number_from_level_id(document.id)
        if parsed_number is not None:
            return parsed_number
        if suggested_level_number is not None:
            return suggested_level_number
        return 1

    def _on_level_number_changed(self, level_number: int) -> None:
        identity = self._identity_service.build_from_number(level_number)
        self._level_id_preview.setText(identity.level_id)
        if not self._name_is_custom:
            self._set_name_text(identity.level_name)
        self._last_auto_name = identity.level_name

    def _on_level_name_changed(self, text: str) -> None:
        if self._is_updating_name:
            return
        self._name_is_custom = text not in {"New Level", self._last_auto_name}

    def _set_name_text(self, text: str) -> None:
        self._is_updating_name = True
        try:
            self._level_name_edit.setText(text)
        finally:
            self._is_updating_name = False
