"""Root-only pytest support for collecting both Python tools together.

Each tool historically exposes its source as a top-level package named ``app``.
Independent test runs are unaffected; for a combined root run, swap that package
at tool boundaries so collection and lazy imports resolve against the right tool.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
TOOL_ROOTS = {
    "LevelGenerator": REPO_ROOT / "Tools" / "LevelGenerator",
    "LevelEditor": REPO_ROOT / "Tools" / "LevelEditor",
}
_active_tool: str | None = None


def _tool_for_path(path: Path) -> str | None:
    parts = path.resolve().parts
    for tool_name in TOOL_ROOTS:
        if tool_name in parts:
            return tool_name
    return None


def _activate_tool(tool_name: str | None) -> None:
    global _active_tool
    if tool_name is None or tool_name == _active_tool:
        return

    for module_name in tuple(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    tool_root = str(TOOL_ROOTS[tool_name])
    other_roots = {str(path) for name, path in TOOL_ROOTS.items() if name != tool_name}
    sys.path[:] = [entry for entry in sys.path if entry not in other_roots and entry != tool_root]
    sys.path.insert(0, tool_root)
    _active_tool = tool_name


def pytest_pycollect_makemodule(module_path: Path, parent: object) -> None:
    _activate_tool(_tool_for_path(module_path))
    return None


def pytest_runtest_setup(item: object) -> None:
    _activate_tool(_tool_for_path(Path(str(item.path))))
