import sys

from PySide6.QtWidgets import QApplication

from app.main_window import LevelEditorMainWindow


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)

    main_window = LevelEditorMainWindow()
    main_window.show()

    return app.exec()
