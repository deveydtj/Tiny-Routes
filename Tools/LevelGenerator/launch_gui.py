#!/usr/bin/env python3
from __future__ import annotations

import sys


def main() -> int:
    try:
        from app.gui.gui_app import run_gui
    except ModuleNotFoundError as exc:
        if exc.name == "_tkinter":
            print(
                "Tkinter is not available in this Python interpreter. Use Python 3.10+ with Tkinter enabled.",
                file=sys.stderr,
            )
            return 1
        raise
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
