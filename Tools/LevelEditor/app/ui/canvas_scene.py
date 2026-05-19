from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene


class LevelCanvasScene(QGraphicsScene):
    def __init__(self) -> None:
        super().__init__()
        self.setSceneRect(QRectF(-2000, -2000, 4000, 4000))
        placeholder = self.addSimpleText("Open a level to begin")
        placeholder.setBrush(QColor("#666666"))
        placeholder.setPos(-70, -10)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawBackground(painter, rect)

        grid_size = 50
        grid_color = QColor("#e8e8e8")
        painter.setPen(QPen(grid_color))

        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        x = left
        while x < int(rect.right()):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            x += grid_size

        y = top
        while y < int(rect.bottom()):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            y += grid_size
