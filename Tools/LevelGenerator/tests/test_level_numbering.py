from __future__ import annotations

import pytest

from app.level_numbering import format_level_id


def test_format_level_id() -> None:
    assert format_level_id(1) == "level_001"
    assert format_level_id(12) == "level_012"
    assert format_level_id(120) == "level_120"


@pytest.mark.parametrize("value", [0, -1, True, 1.2])
def test_format_level_id_rejects_invalid_values(value) -> None:
    with pytest.raises(ValueError):
        format_level_id(value)
