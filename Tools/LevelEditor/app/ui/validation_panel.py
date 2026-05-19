from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from app.services import ValidationResult, ValidationSeverity


class ValidationPanel(QWidget):
    validate_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(160)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        header_row = QHBoxLayout()
        header = QLabel("Validation")
        header.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        header_row.addWidget(header)
        header_row.addStretch()

        self._validate_button = QPushButton("Validate")
        self._validate_button.clicked.connect(
            lambda checked=False: self.validate_requested.emit()
        )
        header_row.addWidget(self._validate_button)
        outer.addLayout(header_row)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(separator)

        self._empty_label = QLabel("No validation messages")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._empty_label)

        self._message_list = QListWidget()
        self._message_list.setVisible(False)
        outer.addWidget(self._message_list)

    def show_result(self, result: ValidationResult) -> None:
        self._message_list.clear()

        if not result.messages:
            self.clear()
            return

        for message in result.messages:
            item = QListWidgetItem(message.message)
            item.setIcon(self._icon_for_severity(message.severity))
            self._message_list.addItem(item)

        self._empty_label.setVisible(False)
        self._message_list.setVisible(True)

    def clear(self) -> None:
        self._message_list.clear()
        self._empty_label.setVisible(True)
        self._message_list.setVisible(False)

    def _icon_for_severity(self, severity: ValidationSeverity):
        if severity is ValidationSeverity.ERROR:
            icon_kind = QStyle.StandardPixmap.SP_MessageBoxCritical
        elif severity is ValidationSeverity.WARNING:
            icon_kind = QStyle.StandardPixmap.SP_MessageBoxWarning
        else:
            icon_kind = QStyle.StandardPixmap.SP_MessageBoxInformation

        return self.style().standardIcon(icon_kind)
