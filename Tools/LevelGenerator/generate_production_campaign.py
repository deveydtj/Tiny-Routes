#!/usr/bin/env python3
from __future__ import annotations

import sys

from app.production_cli import main_production


if __name__ == "__main__":
    sys.exit(main_production())
