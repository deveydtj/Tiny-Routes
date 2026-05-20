from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


LIGHT_GRID_COLOR = "#f3f5f7"
LIGHT_ROAD_COLOR = "#37474f"

DARK_GRID_COLOR = "#e8e8e8"
DARK_ROAD_COLOR = "#546e7a"


def app_uses_dark_palette() -> bool:
    app = QApplication.instance()
    if app is None:
        return False
    window_color = app.palette().color(QPalette.ColorRole.Window)
    return window_color.lightness() < 128


def canvas_grid_color() -> QColor:
    return QColor(DARK_GRID_COLOR if app_uses_dark_palette() else LIGHT_GRID_COLOR)


def road_color() -> QColor:
    return QColor(DARK_ROAD_COLOR if app_uses_dark_palette() else LIGHT_ROAD_COLOR)
