from __future__ import annotations

import pytest

from app.services.road_shape_service import RoadShapeService


def test_road_shape_service_prefers_dominant_axis() -> None:
    service = RoadShapeService()

    assert service.pick_for_positions(0, 0, 2, 1) == "horizontalFirst"
    assert service.pick_for_positions(0, 0, 1, 2) == "verticalFirst"


def test_road_shape_service_allows_valid_override() -> None:
    assert RoadShapeService().pick_for_positions(0, 0, 2, 1, override="verticalFirst") == "verticalFirst"


def test_road_shape_service_rejects_invalid_override() -> None:
    with pytest.raises(ValueError):
        RoadShapeService().pick_for_positions(0, 0, 2, 1, override="diagonal")
