from __future__ import annotations

from ..level_numbering import format_level_id
from ..random_source import RandomSource
from ..services.difficulty_service import DifficultyService
from ..templates.single_switch_template import SingleSwitchTemplate
from .osm_seed_importer import MapSeedGraph


class MapSeedToTemplateAdapter:
    """First-pass adapter that uses map data as attribution-bearing inspiration only."""

    def adapt_to_generated_level(
        self,
        seed_graph: MapSeedGraph,
        level_number: int,
        difficulty: str = "easy",
        seed: int = 0,
    ):
        preset = DifficultyService().get_preset(difficulty)
        template = SingleSwitchTemplate()
        generated = template.generate(format_level_id(level_number), level_number, preset, RandomSource(seed))
        generated.generation_notes.append(seed_graph.attribution)
        generated.generation_notes.append("Map seed geometry is not used directly in first-pass procedural output.")
        return generated
