from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QKeyEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QGraphicsItem, QGraphicsView

from app.models import EditorTool

from .canvas_scene import LevelCanvasScene
from .piece_palette import NODE_ROLE_MIME_TYPE


class LevelCanvasView(QGraphicsView):
    FIT_VIEW_MARGIN = 80.0

    def __init__(self) -> None:
        super().__init__()
        self.setScene(LevelCanvasScene())
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing,
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.centerOn(0, 0)

    def reset_zoom(self) -> None:
        self.resetTransform()

    def set_editor_tool(self, tool: EditorTool) -> None:
        scene = self.scene()
        if isinstance(scene, LevelCanvasScene):
            scene.set_editor_tool(tool)
        cursor = {
            EditorTool.SELECT: Qt.CursorShape.ArrowCursor,
            EditorTool.PLACE_NODE: Qt.CursorShape.CrossCursor,
            EditorTool.CONNECT: Qt.CursorShape.CrossCursor,
            EditorTool.PLAYTEST: Qt.CursorShape.PointingHandCursor,
        }[tool]
        self.viewport().setCursor(cursor)

    def fit_level_to_view(self) -> None:
        scene = self.scene()
        if scene is None or not hasattr(scene, "level_items_bounding_rect"):
            self.reset_zoom()
            self.centerOn(0, 0)
            return

        level_rect = scene.level_items_bounding_rect()
        if level_rect is None or level_rect.isNull() or not level_rect.isValid():
            self.reset_zoom()
            self.centerOn(0, 0)
            return

        margin = self.FIT_VIEW_MARGIN
        self.reset_zoom()
        self.fitInView(
            level_rect.adjusted(-margin, -margin, margin, margin),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def center_on_selected_item(self) -> None:
        scene = self.scene()
        if scene is None:
            return
        selected_items: list[QGraphicsItem] = scene.selectedItems()
        if not selected_items:
            return
        self.centerOn(selected_items[0].sceneBoundingRect().center())

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

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(NODE_ROLE_MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(NODE_ROLE_MIME_TYPE):
            scene = self.scene()
            role = bytes(event.mimeData().data(NODE_ROLE_MIME_TYPE)).decode("utf-8")
            position = self.mapToScene(event.position().toPoint())
            if isinstance(scene, LevelCanvasScene):
                scene.update_drop_preview(role, position)
                if scene.drop_position_is_valid(position):
                    event.acceptProposedAction()
                else:
                    event.ignore()
            return
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        scene = self.scene()
        if isinstance(scene, LevelCanvasScene):
            scene.clear_drop_preview()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if event.mimeData().hasFormat(NODE_ROLE_MIME_TYPE):
            scene = self.scene()
            role = bytes(event.mimeData().data(NODE_ROLE_MIME_TYPE)).decode("utf-8")
            position = self.mapToScene(event.position().toPoint())
            if isinstance(scene, LevelCanvasScene) and scene.drop_node_at(role, position):
                event.acceptProposedAction()
            else:
                event.ignore()
            return
        super().dropEvent(event)
