from __future__ import annotations

import pytest

from app.models.template_variant_spec import TemplateVariantSpec


def test_template_variant_spec_normalizes_names_and_checks_difficulty() -> None:
    spec = TemplateVariantSpec(" Single_Switch_Upper_Package ", " Single_Switch ", (" Easy ",))

    assert spec.name == "single_switch_upper_package"
    assert spec.template_name == "single_switch"
    assert spec.supports_difficulty("EASY") is True
    assert spec.supports_difficulty("hard") is False


def test_template_variant_spec_requires_difficulty() -> None:
    with pytest.raises(ValueError):
        TemplateVariantSpec("variant", "template", ())
