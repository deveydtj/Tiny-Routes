from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from .paths import find_repo_root
from tiny_routes_core.models import (
    LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel,
    SolutionActionModel, SolutionModel,
)


def _import_level_editor_symbols() -> dict[str, Any]:
    """Import Level Editor symbols despite both tools using an `app` package name."""

    repo_root = find_repo_root()
    level_editor_root = repo_root / "Tools" / "LevelEditor"
    saved_modules: dict[str, ModuleType] = {
        name: module
        for name, module in list(sys.modules.items())
        if name == "app" or name.startswith("app.")
    }
    saved_path = list(sys.path)

    for name in list(saved_modules):
        sys.modules.pop(name, None)

    try:
        sys.path.insert(0, str(level_editor_root))
        models = importlib.import_module("app.models")
        level_document = importlib.import_module("app.models.level_document")
        repositories = importlib.import_module("app.repositories")
        services = importlib.import_module("app.services")
        level_validation = importlib.import_module("app.services.level_validation_service")
        solution_validation = importlib.import_module("app.services.solution_validation_service")

        symbols = {
            "LevelFileRepository": getattr(repositories, "LevelFileRepository"),
            "SolutionFileRepository": getattr(repositories, "SolutionFileRepository"),
            "LevelValidationService": getattr(level_validation, "LevelValidationService"),
            "SolutionValidationService": getattr(solution_validation, "SolutionValidationService"),
            "ValidationMessage": getattr(level_validation, "ValidationMessage"),
            "ValidationResult": getattr(level_validation, "ValidationResult"),
            "ValidationSeverity": getattr(level_validation, "ValidationSeverity"),
        }
    finally:
        for name in [name for name in list(sys.modules) if name == "app" or name.startswith("app.")]:
            sys.modules.pop(name, None)
        sys.modules.update(saved_modules)
        sys.path[:] = saved_path

    return symbols


_SYMBOLS = _import_level_editor_symbols()

LevelFileRepository = _SYMBOLS["LevelFileRepository"]
SolutionFileRepository = _SYMBOLS["SolutionFileRepository"]
LevelValidationService = _SYMBOLS["LevelValidationService"]
SolutionValidationService = _SYMBOLS["SolutionValidationService"]
ValidationMessage = _SYMBOLS["ValidationMessage"]
ValidationResult = _SYMBOLS["ValidationResult"]
ValidationSeverity = _SYMBOLS["ValidationSeverity"]

__all__ = [
    "LevelDocument", "RouteGraphModel", "RouteNodeModel", "RouteEdgeModel",
    "SolutionModel", "SolutionActionModel", *_SYMBOLS.keys(),
]
