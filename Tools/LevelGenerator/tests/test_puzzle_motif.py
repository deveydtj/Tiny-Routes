from app.models.graph_recipe import GraphRecipeEdge, GraphRecipeNode
from app.models.puzzle_motif import PuzzleMotif
from app.motifs.base_motif import BaseMotif
from app.motifs.motif_registry import MotifRegistry


class _StraightMotif(BaseMotif):
    @property
    def motif_id(self) -> str:
        return "straight"

    def build(self) -> PuzzleMotif:
        return PuzzleMotif(
            motif_id=self.motif_id,
            entry_connector="entry",
            exit_connectors=("exit",),
            nodes=(GraphRecipeNode("entry"), GraphRecipeNode("exit")),
            edges=(GraphRecipeEdge("entry", "exit"),),
            intended_decision_effect="No decision; adds route spacing.",
            allowed_difficulties=("tutorial", "easy", "medium", "hard", "expert"),
        )


def test_motif_validates_independently() -> None:
    assert _StraightMotif().validate() == ()


def test_registry_rejects_duplicate_motif_ids() -> None:
    registry = MotifRegistry([_StraightMotif()])
    try:
        registry.register(_StraightMotif())
    except ValueError as error:
        assert str(error) == "duplicate_motif_id:straight"
    else:
        raise AssertionError("duplicate motif ID was accepted")


def test_connector_definitions_must_reference_real_nodes() -> None:
    motif = _StraightMotif().build()
    invalid = PuzzleMotif(**{**motif.__dict__, "exit_connectors": ("missing",)})
    assert invalid.validate() == ("motif_exit_connector_unknown:missing",)
