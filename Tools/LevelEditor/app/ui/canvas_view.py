from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import QGraphicsItem, QGraphicsView

from app.models import EditorTool

from .canvas_scene import LevelCanvasScene
from .piece_palette import NODE_ROLE_MIME_TYPE


class LevelCanvasView(QGraphicsView):
    FIT_VIEW_MARGIN = 80.0
    FIT_SELECTION_MARGIN = 40.0

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
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self._editor_tool = EditorTool.SELECT
        self._space_pressed = False
        self._is_panning = False
        self._pan_last_position = QPoint()

    def reset_zoom(self) -> None:
        self.resetTransform()

    def capture_viewport(self) -> tuple[QTransform, QPointF]:
        """Capture zoom and center so scene redraws do not move the designer."""
        return (
            QTransform(self.transform()),
            self.mapToScene(self.viewport().rect().center()),
        )

    def restore_viewport(self, state: tuple[QTransform, QPointF]) -> None:
        transform, center = state
        self.setTransform(transform)
        self.centerOn(center)

    def set_editor_tool(self, tool: EditorTool) -> None:
        self._editor_tool = tool
        scene = self.scene()
        if isinstance(scene, LevelCanvasScene):
            scene.set_editor_tool(tool)
        cursor = {
            EditorTool.SELECT: Qt.CursorShape.ArrowCursor,
            EditorTool.PLACE_NODE: Qt.CursorShape.CrossCursor,
            EditorTool.CONNECT: Qt.CursorShape.CrossCursor,
            EditorTool.PLAYTEST: Qt.CursorShape.PointingHandCursor,
        }[tool]
        if not self._is_panning and not self._space_pressed:
            self.viewport().setCursor(cursor)
        self.setDragMode(
            QGraphicsView.DragMode.RubberBandDrag
            if tool is EditorTool.SELECT
            else QGraphicsView.DragMode.NoDrag
        )

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

    def zoom_to_selection(self) -> None:
        scene = self.scene()
        if scene is None:
            return
        selected_items: list[QGraphicsItem] = scene.selectedItems()
        if not selected_items:
            return

        selected_rect = selected_items[0].sceneBoundingRect()
        for item in selected_items[1:]:
            selected_rect = selected_rect.united(item.sceneBoundingRect())
        if selected_rect.isNull() or not selected_rect.isValid():
            return

        margin = self.FIT_SELECTION_MARGIN
        self.reset_zoom()
        self.fitInView(
            selected_rect.adjusted(-margin, -margin, margin, margin),
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
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pressed = True
            if not self._is_panning:
                self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        scene = self.scene()
        if scene is not None:
            scene.keyPressEvent(event)
            if event.isAccepted():
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pressed = False
            if not self._is_panning:
                self._restore_tool_cursor()
            event.accept()
            return
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        wants_middle_pan = event.button() == Qt.MouseButton.MiddleButton
        wants_space_pan = (
            self._space_pressed and event.button() == Qt.MouseButton.LeftButton
        )
        if wants_middle_pan or wants_space_pan:
            self._is_panning = True
            self._pan_last_position = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_panning:
            position = event.position().toPoint()
            delta = position - self._pan_last_position
            self._pan_last_position = position
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._is_panning and event.button() in {
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.LeftButton,
        }:
            self._is_panning = False
            if self._space_pressed:
                self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self._restore_tool_cursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(zoom_factor, zoom_factor)
            event.accept()
            return

        super().wheelEvent(event)

    def _restore_tool_cursor(self) -> None:
        cursor = {
            EditorTool.SELECT: Qt.CursorShape.ArrowCursor,
            EditorTool.PLACE_NODE: Qt.CursorShape.CrossCursor,
            EditorTool.CONNECT: Qt.CursorShape.CrossCursor,
            EditorTool.PLAYTEST: Qt.CursorShape.PointingHandCursor,
        }[self._editor_tool]
        self.viewport().setCursor(cursor)

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
