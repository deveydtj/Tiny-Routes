from __future__ import annotations

from collections.abc import Mapping


class NodeArrangementService:
    """Calculate deterministic alignment and distribution transforms."""

    ALIGN_OPERATIONS = {
        "left",
        "right",
        "top",
        "bottom",
        "horizontal_centers",
        "vertical_centers",
    }
    DISTRIBUTE_OPERATIONS = {"horizontal", "vertical"}

    def arrange(
        self,
        positions: Mapping[str, tuple[float, float]],
        operation: str,
    ) -> dict[str, tuple[float, float]]:
        result = dict(positions)
        if operation in self.ALIGN_OPERATIONS:
            if len(result) < 2:
                return result
            return self._align(result, operation)
        if operation in self.DISTRIBUTE_OPERATIONS:
            if len(result) < 3:
                return result
            return self._distribute(result, operation)
        raise ValueError(f"Unknown arrangement operation: {operation}")

    @staticmethod
    def nudge(
        positions: Mapping[str, tuple[float, float]],
        dx: float,
        dy: float,
    ) -> dict[str, tuple[float, float]]:
        return {
            node_id: (x + dx, y + dy)
            for node_id, (x, y) in positions.items()
        }

    def _align(
        self,
        positions: dict[str, tuple[float, float]],
        operation: str,
    ) -> dict[str, tuple[float, float]]:
        xs = [position[0] for position in positions.values()]
        ys = [position[1] for position in positions.values()]
        if operation == "left":
            target, axis = min(xs), "x"
        elif operation == "right":
            target, axis = max(xs), "x"
        elif operation == "bottom":
            target, axis = min(ys), "y"
        elif operation == "top":
            target, axis = max(ys), "y"
        elif operation == "horizontal_centers":
            target, axis = sum(xs) / len(xs), "x"
        else:
            target, axis = sum(ys) / len(ys), "y"
        return {
            node_id: ((target, y) if axis == "x" else (x, target))
            for node_id, (x, y) in positions.items()
        }

    @staticmethod
    def _distribute(
        positions: dict[str, tuple[float, float]],
        operation: str,
    ) -> dict[str, tuple[float, float]]:
        axis_index = 0 if operation == "horizontal" else 1
        ordered = sorted(
            positions.items(),
            key=lambda item: (item[1][axis_index], item[0]),
        )
        start = ordered[0][1][axis_index]
        end = ordered[-1][1][axis_index]
        spacing = (end - start) / (len(ordered) - 1)
        result = dict(positions)
        for index, (node_id, (x, y)) in enumerate(ordered):
            coordinate = start + spacing * index
            result[node_id] = (coordinate, y) if axis_index == 0 else (x, coordinate)
        return result
