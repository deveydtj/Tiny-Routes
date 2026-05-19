from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QGraphicsView

from .canvas_scene import LevelCanvasScene


class LevelCanvasView(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()
        self.setScene(LevelCanvasScene())
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing,
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.centerOn(0, 0)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        scene = self.scene()
        if scene is not None:
            scene.keyPressEvent(event)
            if event.isAccepted():
                return
        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(zoom_factor, zoom_factor)
            event.accept()
            return

        super().wheelEvent(event)
