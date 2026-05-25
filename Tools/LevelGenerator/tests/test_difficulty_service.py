from __future__ import annotations

import pytest

from app.services.difficulty_service import DifficultyService


def test_all_difficulty_presets_are_available() -> None:
    service = DifficultyService()

    for name in ["tutorial", "easy", "medium", "hard"]:
        assert service.get_preset(name).name == name


def test_invalid_difficulty_is_rejected() -> None:
    with pytest.raises(ValueError):
        DifficultyService().get_preset("extreme")
