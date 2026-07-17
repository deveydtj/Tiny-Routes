# V2 Generator Limitation Baseline

This baseline freezes the behavior of the legacy production generator before V3 work changes its puzzle model. It is evidence, not a quality target.

## Reproduce the baseline

From the repository root, run:

```bash
Tools/LevelEditor/.venv/bin/python Tools/LevelGenerator/run_v2_production_path_baseline.py
```

The command calls `LevelGenerationService.generate()` with `generator_architecture=v2_legacy`. That dispatches through `BatchOrchestrationService`, using the same configuration and orchestration boundary as the CLI and GUI. It does not use the template-only or named-motif shortcuts in the fixed-seed regression service.

The checked-in evidence is in `tests/fixtures/v2_generator_baseline/baseline.json`. It records requested and accepted counts, candidate attempts, generation errors, rejection codes, runtime, structural signatures, decision profiles, registry-family snapshots, duplicate signature groups, and known mislabeled families.

## Audited limitations

- The fixed suites accept zero- and one-tap tutorial/easy output. The easy result is solvable by assigning a permanent switch direction before movement.
- The medium, hard, and expert production-path suites do not complete at the frozen seeds and budgets. Their failures are preserved instead of being replaced by direct template output.
- Multiple registered recipe names share structural or behavioral signatures. The evidence file lists the exact duplicate groups.
- Several loop, ring, and four-way families fail their current declared topology contracts. These failures remain baseline evidence for later quarantine or repair tasks.
- `one_tap_recipe.json` and `static_policy_recipe.json` are adversarial fixtures that freeze the anti-triviality gaps V3 must reject.

Do not update this baseline merely to make V2 appear healthier. Regenerate it only when an intentional baseline repair changes the recorded behavior, and review the resulting signature and rejection changes.
