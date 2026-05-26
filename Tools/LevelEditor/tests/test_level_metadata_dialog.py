import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:
    pytest.skip(f"PySide6 unavailable in this environment: {exc}", allow_module_level=True)

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.services import create_default_level_document
from app.ui import LevelMetadataDialog


@pytest.fixture
def qapplication() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dialog_previews_level_021_for_number_21(qapplication: QApplication) -> None:
    document = create_default_level_document()
    dialog = LevelMetadataDialog(document, suggested_level_number=21)
    try:
        assert dialog.selected_identity().level_id == "level_021"
        assert dialog._level_id_preview.text() == "level_021"
    finally:
        dialog.close()


def test_dialog_previews_level_021_name_by_default(qapplication: QApplication) -> None:
    document = create_default_level_document()
    dialog = LevelMetadataDialog(document, suggested_level_number=21)
    try:
        assert dialog.level_name() == "Level 021"
    finally:
        dialog.close()


def test_changing_number_updates_id_preview(qapplication: QApplication) -> None:
    document = create_default_level_document()
    dialog = LevelMetadataDialog(document, suggested_level_number=21)
    try:
        dialog._level_number_spinbox.setValue(22)
        assert dialog._level_id_preview.text() == "level_022"
        assert dialog.level_name() == "Level 022"
    finally:
        dialog.close()


def test_custom_name_is_preserved_when_number_changes(qapplication: QApplication) -> None:
    document = create_default_level_document()
    dialog = LevelMetadataDialog(document, suggested_level_number=21)
    try:
        dialog._level_name_edit.setText("Downtown Switchback")
        dialog._level_number_spinbox.setValue(22)
        assert dialog.level_name() == "Downtown Switchback"
    finally:
        dialog.close()


def test_time_limit_field_returns_positive_number(qapplication: QApplication) -> None:
    document = create_default_level_document()
    dialog = LevelMetadataDialog(document, suggested_level_number=21)
    try:
        assert dialog.time_limit_seconds() > 0
        assert dialog.metadata_result().timeLimitSeconds > 0
    finally:
        dialog.close()


def test_par_taps_field_returns_non_negative_integer(qapplication: QApplication) -> None:
    document = create_default_level_document()
    dialog = LevelMetadataDialog(document, suggested_level_number=21)
    try:
        assert isinstance(dialog.par_taps(), int)
        assert dialog.metadata_result().parTaps >= 0
    finally:
        dialog.close()
