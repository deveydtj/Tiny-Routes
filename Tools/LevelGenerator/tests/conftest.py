from __future__ import annotations

import sys
from pathlib import Path

LEVEL_GENERATOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_GENERATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_GENERATOR_ROOT))
