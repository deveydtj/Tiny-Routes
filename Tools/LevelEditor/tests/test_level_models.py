import json
import pytest
import sys
from pathlib import Path

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.models import LevelDocument, RouteNodeModel, RouteEdgeModel, EmbeddedSolution


# ---------------------------------------------------------------------------
# Minimal fixture level that covers the common shape (no optional fields)
# ---------------------------------------------------------------------------

FIXTURE_LEVEL_SIMPLE: dict = {
    "id": "level_001",
    "name": "First Pickup",
    "graph": {
        "nodes": [
            {"id": "start", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["e_start_package"]},
            {"id": "package", "x": 1.5, "y": 0.0, "outgoingEdgeIDs": ["e_package_destination"]},
            {"id": "destination", "x": 3.0, "y": 0.0, "outgoingEdgeIDs": []},
        ],
        "edges": [
            {"id": "e_start_package", "fromNodeID": "start", "toNodeID": "package"},
            {"id": "e_package_destination", "fromNodeID": "package", "toNodeID": "destination"},
        ],
    },
    "startNodeID": "start",
    "packageNodeID": "package",
    "destinationNodeID": "destination",
    "timeLimitSeconds": 30,
    "parTaps": 0,
}

# Fixture with optional roadShape on edges and an embedded solution
FIXTURE_LEVEL_WITH_OPTIONALS: dict = {
    "id": "level_002",
    "name": "First Choice",
    "graph": {
        "nodes": [
            {"id": "start", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["e_start_approach"]},
            {"id": "approach", "x": 1.0, "y": 0.0, "outgoingEdgeIDs": ["e_approach_choice"]},
            {"id": "choice", "x": 2.0, "y": 0.0, "outgoingEdgeIDs": ["e_choice_bypass", "e_choice_package"]},
            {"id": "package", "x": 3.0, "y": 0.9, "outgoingEdgeIDs": ["e_package_destination"]},
            {"id": "bypass", "x": 3.0, "y": -0.9, "outgoingEdgeIDs": []},
            {"id": "destination", "x": 3.0, "y": 1.8, "outgoingEdgeIDs": []},
        ],
        "edges": [
            {"id": "e_start_approach", "fromNodeID": "start", "toNodeID": "approach"},
            {"id": "e_approach_choice", "fromNodeID": "approach", "toNodeID": "choice"},
            {"id": "e_choice_bypass", "fromNodeID": "choice", "toNodeID": "bypass", "roadShape": "horizontalFirst"},
            {"id": "e_choice_package", "fromNodeID": "choice", "toNodeID": "package", "roadShape": "horizontalFirst"},
            {"id": "e_package_destination", "fromNodeID": "package", "toNodeID": "destination"},
        ],
    },
    "startNodeID": "start",
    "packageNodeID": "package",
    "destinationNodeID": "destination",
    "timeLimitSeconds": 36,
    "parTaps": 1,
    "solution": {"tapNodeIDs": ["choice"]},
}


# ---------------------------------------------------------------------------
# RouteEdgeModel tests
# ---------------------------------------------------------------------------

class TestRouteEdgeModel:
    def test_from_dict_required_fields(self):
        data = {"id": "e1", "fromNodeID": "a", "toNodeID": "b"}
        edge = RouteEdgeModel.from_dict(data)
        assert edge.id == "e1"
        assert edge.fromNodeID == "a"
        assert edge.toNodeID == "b"
        assert edge.roadShape is None
        assert edge.availability == "always"

    def test_from_dict_with_road_shape(self):
        data = {"id": "e1", "fromNodeID": "a", "toNodeID": "b", "roadShape": "verticalFirst"}
        edge = RouteEdgeModel.from_dict(data)
        assert edge.roadShape == "verticalFirst"

    def test_to_dict_omits_none_road_shape(self):
        edge = RouteEdgeModel(id="e1", fromNodeID="a", toNodeID="b")
        d = edge.to_dict()
        assert "roadShape" not in d

    def test_to_dict_includes_road_shape_when_set(self):
        edge = RouteEdgeModel(id="e1", fromNodeID="a", toNodeID="b", roadShape="horizontalFirst")
        d = edge.to_dict()
        assert d["roadShape"] == "horizontalFirst"

    def test_round_trip_without_road_shape(self):
        data = {"id": "e1", "fromNodeID": "a", "toNodeID": "b"}
        assert RouteEdgeModel.from_dict(data).to_dict() == data

    def test_round_trip_with_road_shape(self):
        data = {"id": "e2", "fromNodeID": "x", "toNodeID": "y", "roadShape": "horizontalFirst"}
        assert RouteEdgeModel.from_dict(data).to_dict() == data

    @pytest.mark.parametrize("availability", ["always", "beforePackage", "afterPackage"])
    def test_round_trip_with_availability(self, availability):
        data = {
            "id": "e2",
            "fromNodeID": "x",
            "toNodeID": "y",
            "availability": availability,
        }

        edge = RouteEdgeModel.from_dict(data)

        assert edge.availability == availability
        assert edge.to_dict() == data

    def test_preserves_unknown_fields(self):
        data = {"id": "e1", "fromNodeID": "a", "toNodeID": "b", "_future": "value"}
        result = RouteEdgeModel.from_dict(data).to_dict()
        assert result["_future"] == "value"


# ---------------------------------------------------------------------------
# RouteNodeModel tests
# ---------------------------------------------------------------------------

class TestRouteNodeModel:
    def test_from_dict_basic(self):
        data = {"id": "start", "x": 0.0, "y": 1.5, "outgoingEdgeIDs": ["e1"]}
        node = RouteNodeModel.from_dict(data)
        assert node.id == "start"
        assert node.x == 0.0
        assert node.y == 1.5
        assert node.outgoingEdgeIDs == ["e1"]

    def test_from_dict_empty_outgoing(self):
        data = {"id": "end", "x": 3.0, "y": 0.0, "outgoingEdgeIDs": []}
        node = RouteNodeModel.from_dict(data)
        assert node.outgoingEdgeIDs == []

    def test_to_dict_round_trip(self):
        data = {"id": "start", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["e_start_package"]}
        assert RouteNodeModel.from_dict(data).to_dict() == data

    def test_preserves_unknown_fields(self):
        data = {"id": "n1", "x": 1.0, "y": 2.0, "outgoingEdgeIDs": [], "_meta": "test"}
        result = RouteNodeModel.from_dict(data).to_dict()
        assert result["_meta"] == "test"

    def test_missing_outgoing_edge_ids_raises(self):
        with pytest.raises(KeyError):
            RouteNodeModel.from_dict({"id": "n", "x": 0.0, "y": 0.0})

    def test_integer_coordinates_cast_to_float(self):
        data = {"id": "n", "x": 1, "y": 2, "outgoingEdgeIDs": []}
        node = RouteNodeModel.from_dict(data)
        assert isinstance(node.x, float)
        assert isinstance(node.y, float)


# ---------------------------------------------------------------------------
# EmbeddedSolution tests
# ---------------------------------------------------------------------------

class TestEmbeddedSolution:
    def test_from_dict(self):
        data = {"tapNodeIDs": ["switch_a", "switch_b"]}
        sol = EmbeddedSolution.from_dict(data)
        assert sol.tapNodeIDs == ["switch_a", "switch_b"]

    def test_to_dict_round_trip(self):
        data = {"tapNodeIDs": ["choice"]}
        assert EmbeddedSolution.from_dict(data).to_dict() == data

    def test_empty_tap_node_ids(self):
        data = {"tapNodeIDs": []}
        sol = EmbeddedSolution.from_dict(data)
        assert sol.tapNodeIDs == []

    def test_missing_tap_node_ids_raises(self):
        with pytest.raises(KeyError):
            EmbeddedSolution.from_dict({})

    def test_preserves_unknown_fields_in_solution(self):
        data = {"tapNodeIDs": ["choice"], "_hint": "extra"}
        result = EmbeddedSolution.from_dict(data).to_dict()
        assert result["_hint"] == "extra"


# ---------------------------------------------------------------------------
# LevelDocument tests
# ---------------------------------------------------------------------------

class TestLevelDocument:
    def test_from_dict_simple(self):
        doc = LevelDocument.from_dict(FIXTURE_LEVEL_SIMPLE)
        assert doc.id == "level_001"
        assert doc.name == "First Pickup"
        assert doc.startNodeID == "start"
        assert doc.packageNodeID == "package"
        assert doc.destinationNodeID == "destination"
        assert doc.timeLimitSeconds == 30
        assert doc.parTaps == 0
        assert doc.solution is None

    def test_from_dict_node_count(self):
        doc = LevelDocument.from_dict(FIXTURE_LEVEL_SIMPLE)
        assert len(doc.graph.nodes) == 3

    def test_from_dict_edge_count(self):
        doc = LevelDocument.from_dict(FIXTURE_LEVEL_SIMPLE)
        assert len(doc.graph.edges) == 2

    def test_from_dict_with_optionals(self):
        doc = LevelDocument.from_dict(FIXTURE_LEVEL_WITH_OPTIONALS)
        assert doc.id == "level_002"
        assert doc.solution is not None
        assert doc.solution.tapNodeIDs == ["choice"]

    def test_from_dict_optional_road_shape(self):
        doc = LevelDocument.from_dict(FIXTURE_LEVEL_WITH_OPTIONALS)
        bypass_edge = next(e for e in doc.graph.edges if e.id == "e_choice_bypass")
        assert bypass_edge.roadShape == "horizontalFirst"

    def test_round_trip_simple(self):
        assert LevelDocument.from_dict(FIXTURE_LEVEL_SIMPLE).to_dict() == FIXTURE_LEVEL_SIMPLE

    def test_round_trip_with_optionals(self):
        assert LevelDocument.from_dict(FIXTURE_LEVEL_WITH_OPTIONALS).to_dict() == FIXTURE_LEVEL_WITH_OPTIONALS

    def test_round_trip_json_serializable(self):
        doc = LevelDocument.from_dict(FIXTURE_LEVEL_SIMPLE)
        serialized = json.dumps(doc.to_dict())
        restored = json.loads(serialized)
        assert LevelDocument.from_dict(restored).to_dict() == FIXTURE_LEVEL_SIMPLE

    def test_preserves_unknown_top_level_fields(self):
        data = dict(FIXTURE_LEVEL_SIMPLE)
        data["_debugNote"] = "test"
        result = LevelDocument.from_dict(data).to_dict()
        assert result["_debugNote"] == "test"

    def test_preserves_unknown_fields_in_graph(self):
        import copy
        data = copy.deepcopy(FIXTURE_LEVEL_SIMPLE)
        data["graph"]["_layoutVersion"] = 2
        result = LevelDocument.from_dict(data).to_dict()
        assert result["graph"]["_layoutVersion"] == 2

    def test_missing_graph_nodes_raises(self):
        import copy
        data = copy.deepcopy(FIXTURE_LEVEL_SIMPLE)
        del data["graph"]["nodes"]
        with pytest.raises(KeyError):
            LevelDocument.from_dict(data)

    def test_missing_graph_edges_raises(self):
        import copy
        data = copy.deepcopy(FIXTURE_LEVEL_SIMPLE)
        del data["graph"]["edges"]
        with pytest.raises(KeyError):
            LevelDocument.from_dict(data)
