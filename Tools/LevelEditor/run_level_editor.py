from __future__ import annotations

import os
import sys
from pathlib import Path


def _prefer_local_venv() -> None:
    script_dir = Path(__file__).resolve().parent
    venv_python = script_dir / ".venv" / "bin" / "python"

    if not venv_python.exists():
        return

    current_python = Path(sys.executable).resolve()
    if current_python == venv_python.resolve():
        return

    os.execv(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]])


_prefer_local_venv()

try:
    from app.main import main
except ModuleNotFoundError as exc:
    if exc.name == "PySide6":
        script_dir = Path(__file__).resolve().parent
        venv_python = script_dir / ".venv" / "bin" / "python"
        install_target = str(venv_python) if venv_python.exists() else sys.executable
        print(
            "Missing dependency: PySide6.\n"
            f"Install LevelEditor requirements with:\n  {install_target} -m pip install -r {script_dir / 'requirements.txt'}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    raise


if __name__ == "__main__":
    raise SystemExit(main())
