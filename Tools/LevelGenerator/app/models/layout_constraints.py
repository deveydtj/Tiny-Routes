from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class BoundingBox:
    min_x: float = -1.2
    max_x: float = 1.2
    min_y: float = -1.3
    max_y: float = 1.0


@dataclass(frozen=True)
class ReservedIconClearance:
    node_id: str
    horizontal_cells: int
    vertical_cells: int


@dataclass(frozen=True)
class LayoutConstraints:
    bounds: BoundingBox = BoundingBox()
    minimum_node_distance: float = 0.2
    grid_size: float = 0.05
    primary_lane_spacing: int = 1
    return_lane_spacing: int = 2


@dataclass(frozen=True)
class ConstraintViolation:
    code: str
    message: str
    node_id: str | None = None
    edge_id: str | None = None


class RepairOperationKind(str, Enum):
    MOVE_NODE = "move_node"
    MOVE_LANE = "move_lane"
    INSERT_BEND = "insert_bend"
    EXPAND_LAYER = "expand_layer"


@dataclass(frozen=True)
class RepairOperation:
    kind: RepairOperationKind
    target_id: str
    delta_column: int = 0
    delta_row: int = 0
    reason: str = ""
