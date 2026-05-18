"""Entry point for the Tiny Routes Level Editor.

Run this script from the repo root or from inside Tools/LevelEditor/:

    python Tools/LevelEditor/run_level_editor.py
"""

import sys
import os

# Ensure the Tools/LevelEditor directory is on the path so `app` is importable
# regardless of the working directory the script is launched from.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from app.main import main

if __name__ == "__main__":
    main()
