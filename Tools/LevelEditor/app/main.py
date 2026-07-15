import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.main_window import LevelEditorMainWindow


def _parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tiny Routes Level Editor")
    parser.add_argument("--level", type=Path, help="Level JSON to open at startup")
    parser.add_argument("--solution", type=Path, help="Solution sidecar to open with --level")
    parser.add_argument("--quality", type=Path, help="Generated-candidate quality JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = _parse_arguments(argv)
    app = QApplication.instance() or QApplication([sys.argv[0]])

    main_window = LevelEditorMainWindow()
    if arguments.level is not None:
        main_window.open_level_bundle(
            arguments.level,
            solution_path=arguments.solution,
            quality_path=arguments.quality,
        )
    main_window.show()

    return app.exec()
