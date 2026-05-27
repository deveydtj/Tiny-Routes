from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..models.generated_level import GeneratedLevel
from ..models.template_variant_spec import TemplateVariantSpec
from ..random_source import RandomSource
from .base_template import LevelTemplate


class SingleSwitchTemplate(LevelTemplate):
    name = "single_switch"
    variant_specs = [
        TemplateVariantSpec("single_switch_classic", name, ("tutorial", "easy")),
        TemplateVariantSpec("single_switch_upper_package", name, ("easy",)),
        TemplateVariantSpec("single_switch_lower_package", name, ("easy",)),
        TemplateVariantSpec("single_switch_short_dead_end", name, ("easy",)),
    ]

    def supports_difficulty(self, preset: DifficultyPreset) -> bool:
        return preset.name in {"tutorial", "easy"}

    def generate(
        self,
        level_id: str,
        level_number: int,
        preset: DifficultyPreset,
        rng: RandomSource,
    ) -> GeneratedLevel:
        builder = self.builder()
        include_approach = preset.name != "tutorial"
        variant = rng.choice([spec.name for spec in self.variant_specs if spec.supports_difficulty(preset.name)])
        positions, switch_id, dead_end_id, route = _variant_spec(variant, include_approach)
        layout_variant = self.apply_layout_variant(positions, preset, rng)
        positions = layout_variant.positions

        node_ids = ["start"]
        if include_approach:
            node_ids.append("approach")
        node_ids.extend([switch_id, dead_end_id, "package", "destination"])
        for node_id in node_ids:
            builder.add_node(node_id, *positions[node_id])

        if include_approach:
            builder.add_edge("start", "approach")
            builder.add_edge("approach", switch_id)
        else:
            builder.add_edge("start", switch_id)
        builder.add_edge(switch_id, dead_end_id)
        builder.add_edge(switch_id, "package")
        builder.add_edge("package", "destination")

        time_limit = self.calculate_time_limit([positions[node_id] for node_id in route], preset)
        level = builder.build_level_document(
            level_id=level_id,
            name=self.naming.name_for_level_number(level_number),
            start_node_id="start",
            package_node_id="package",
            destination_node_id="destination",
            time_limit_seconds=time_limit,
            par_taps=1,
        )
        solution = self.solution_builder.build_route_timed_tap_solution(
            level_id,
            [switch_id],
            route,
            positions,
            preset,
            "Rotate choice once so the route collects the package before heading to destination.",
            route_edge_shapes=self.route_edge_shapes_for(level, route),
        )
        return self.generated(
            level,
            solution,
            preset,
            rng.seed,
            notes=[f"Template variant: {variant}", f"Layout variant: {layout_variant.name}"],
        )


def _variant_spec(
    variant: str,
    include_approach: bool,
) -> tuple[dict[str, tuple[float, float]], str, str, list[str]]:
    if variant == "single_switch_upper_package":
        switch_id = "upper_choice"
        dead_end_id = "upper_dead_end"
        positions = {
            "start": (-1.1, -0.15),
            "approach": (-0.55, -0.05),
            switch_id: (0.0, 0.08),
            dead_end_id: (0.78, -0.68),
            "package": (0.7, 0.6),
            "destination": (1.08, 0.9),
        }
    elif variant == "single_switch_lower_package":
        switch_id = "lower_choice"
        dead_end_id = "lower_dead_end"
        positions = {
            "start": (-1.1, 0.18),
            "approach": (-0.56, 0.08),
            switch_id: (0.0, -0.08),
            dead_end_id: (0.78, 0.68),
            "package": (0.7, -0.6),
            "destination": (1.08, -0.9),
        }
    elif variant == "single_switch_short_dead_end":
        switch_id = "short_choice"
        dead_end_id = "short_dead_end"
        positions = {
            "start": (-1.1, 0.02),
            "approach": (-0.58, 0.02),
            switch_id: (-0.04, 0.02),
            dead_end_id: (0.48, -0.4),
            "package": (0.78, 0.46),
            "destination": (1.12, 0.82),
        }
    else:
        switch_id = "choice"
        dead_end_id = "dead_end_a"
        positions = {
            "start": (-1.1, 0.0),
            "approach": (-0.55, 0.0),
            switch_id: (0.0, 0.0),
            dead_end_id: (0.75, -0.65),
            "package": (0.72, 0.55),
            "destination": (1.1, 0.95),
        }
    route = ["start"] + (["approach"] if include_approach else []) + [switch_id, "package", "destination"]
    return positions, switch_id, dead_end_id, route
