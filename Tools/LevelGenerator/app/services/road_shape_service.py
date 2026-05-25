from __future__ import annotations


class RoadShapeService:
    ALLOWED_VALUES = {"horizontalFirst", "verticalFirst"}

    def pick_for_positions(
        self,
        from_x: float,
        from_y: float,
        to_x: float,
        to_y: float,
        override: str | None = None,
    ) -> str:
        if override is not None:
            if override not in self.ALLOWED_VALUES:
                raise ValueError(f"Invalid roadShape: {override}")
            return override
        horizontal_delta = abs(to_x - from_x)
        vertical_delta = abs(to_y - from_y)
        return "horizontalFirst" if horizontal_delta >= vertical_delta else "verticalFirst"

    def is_allowed(self, road_shape: str | None) -> bool:
        return road_shape in self.ALLOWED_VALUES
