from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow


class LevelEditorMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Tiny Routes Level Editor")
        self.resize(1024, 768)

        placeholder_label = QLabel("Level Editor")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(placeholder_label)
