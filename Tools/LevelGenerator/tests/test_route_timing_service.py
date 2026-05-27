from __future__ import annotations

import math

import pytest

from app.services.route_timing_service import RouteTimingService
from .late_tap_chain_fixture import (
    late_tap_chain_positions,
    late_tap_chain_route,
    late_tap_chain_route_edge_shapes,
)


def test_route_timing_service_returns_straight_horizontal_length() -> None:
    service = RouteTimingService()

    assert service.edge_length((0.0, 0.0), (2.0, 0.0), None) == pytest.approx(2.0)


def test_route_timing_service_returns_straight_vertical_length() -> None:
    service = RouteTimingService()

    assert service.edge_length((0.0, 0.0), (0.0, 1.5), None) == pytest.approx(1.5)


def test_route_timing_service_matches_horizontal_first_formula() -> None:
    service = RouteTimingService()
    length = service.edge_length((0.0, 0.0), (1.0, 0.6), "horizontalFirst")
    expected = (1.0 - 0.18) + ((math.pi / 2) * 0.18) + (0.6 - 0.18)

    assert length == pytest.approx(expected)
    assert length < 1.6


def test_route_timing_service_matches_vertical_first_formula() -> None:
    service = RouteTimingService()
    length = service.edge_length((0.0, 0.0), (1.0, 0.6), "verticalFirst")
    expected = (0.6 - 0.18) + ((math.pi / 2) * 0.18) + (1.0 - 0.18)

    assert length == pytest.approx(expected)
    assert length < 1.6


def test_route_timing_service_clamps_turn_radius_to_half_smallest_delta() -> None:
    service = RouteTimingService()
    length = service.edge_length((0.0, 0.0), (0.2, 0.5), "horizontalFirst")
    expected = (0.2 - 0.1) + ((math.pi / 2) * 0.1) + (0.5 - 0.1)

    assert length == pytest.approx(expected)
    assert length < 0.7


def test_route_timing_service_reports_shorter_arrivals_for_level28_style_chain() -> None:
    service = RouteTimingService()

    arrival_times = service.route_arrival_times(
        late_tap_chain_route(),
        late_tap_chain_positions(),
        edges_by_route_pair=late_tap_chain_route_edge_shapes(),
    )

    expected_edge_length = (0.6 - 0.18) + ((math.pi / 2) * 0.18) + (0.6 - 0.18)
    assert arrival_times == pytest.approx(
        [
            0.0,
            expected_edge_length,
            expected_edge_length * 2,
            expected_edge_length * 3,
            expected_edge_length * 4,
            expected_edge_length * 5,
            expected_edge_length * 6,
        ]
    )
    assert arrival_times[3] < 3.6
