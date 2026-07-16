# Difficulty and Quality Tuning

This guide explains how to tune the generator without weakening runtime correctness or silently changing the fixed-seed campaign. Treat structural validation, runtime replay, and Swift parity as hard gates. Tune only the measured difficulty, quality, layout, and portfolio policies that run after those gates.

## Safe tuning loop

1. Reproduce the problem with a fixed seed and a dry run. Write reports outside the production resource folders.
2. Read `rejectionReasonCounts`, `rejectionStageCounts`, and `topRejectedNearMisses` in the JSON report before changing a threshold.
3. Change one policy family at a time: difficulty, timing, layout, candidate breadth, or diversity.
4. Run focused generator tests and the affected fixed-seed suite.
5. Run a multi-level stress dry run to make sure the improvement is not specific to one seed.
6. Run every fixed-seed suite and production-content gate before accepting the change.

Example scratch run:

```bash
python3 Tools/LevelGenerator/stress_test_generation.py \
  --start 1 \
  --count 20 \
  --difficulty auto \
  --seed 9001 \
  --candidate-pool-size 8 \
  --output-dir /tmp/tiny-routes-tuning
```

The stress command is always a dry run and disables similarity checks against production content. Use the normal generator with `--compare-existing` and required Swift validation before promoting any candidate.

## Decision thresholds

`DifficultyService` owns the preset ranges. `DecisionProfileService` supplies measured evidence from the solved and replayed route; recipe tags do not satisfy these gates.

| Difficulty | Required decisions | Minimum decision window | Strategic properties | Maximum independent ratio | Route interest minimum | Quality score minimum |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tutorial | 0–2 | 2.00 s | 0 | 1.00 | 0.00 | 65 |
| Easy | 1–3 | 1.60 s | 0 | 1.00 | 0.20 | 70 |
| Medium | 2–4 | 1.25 s | 1 | 0.75 | 0.42 | 75 |
| Hard | 3–6 | 1.00 s | 2 | 0.67 | 0.54 | 80 |
| Expert | 4–8 | 0.85 s | 2 | 0.60 | 0.58 | 85 |

A strategic property is measured evidence of an ordered dependency, switch-state change on revisit, recoverable mistake, route revisit, package-phase transition, or state-dependent route change. The independent-decision limit applies when a level has more than one required decision and no state-dependent route change.

The supporting content ranges are:

| Difficulty | Nodes | Switches | Required taps | Route edges | Dead ends | Maximum switch fan-out | Maximum visual complexity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Tutorial | 3–8 | 0–2 | 0–2 | 2–5 | 0–2 | 2 | 0.34 |
| Easy | 5–7 | 1–2 | 1–2 | 3–5 | 1–2 | 2 | 0.44 |
| Medium | 7–9 | 2–3 | 2–3 | 5–7 | 1–3 | 3 | 0.62 |
| Hard | 9–12 | 3–5 | 3–5 | 7–10 | 2–4 | 3 | 0.76 |
| Expert | 8–13 | 1–5 | 2–6 | 6–11 | 1–4 | 4 | 0.86 |

Changing a preset can affect topology eligibility, runtime timing, layout selection, quality scoring, rejection distributions, and golden hashes. Prefer changing generation inputs or motif coverage when candidates fail for a real design reason. Relax a threshold only when report evidence from several seeds shows that the current boundary rejects desirable content.

### Hard quality gates

Every accepted candidate must also meet these non-preset gates in `LevelGenerationService`:

- Runtime confidence: at least `0.75`.
- Switch clarity: at least `0.40`.
- Similarity during selection: no more than `0.87` in production.
- Duplicate signature threshold: `0.88` in `CandidateUniquenessService`.
- Total quality score: the difficulty-specific minimum in the table above.

Playtest portfolio mode relaxes similarity and duplicate thresholds to help assemble large exploratory batches. It is not a production acceptance profile.

## Timing windows

Generated recipe-first levels use `liveLookahead`. Their look-ahead value is:

```text
max(1.35 seconds, preset minimum decision window)
```

The default tap cooldown is `0.12` seconds. `RuntimeSolutionSearchService` finds each real eligibility window by replaying the shared runtime in `0.02`-second search steps. It schedules the first tap `0.12` seconds after the window opens, spaces multiple rotations by `cooldown + 0.001`, and requires the last tap to retain a `0.12`-second margin before route commitment.

Do not derive production action timestamps from geometric arrival estimates. Geometry can support analysis, but only runtime search proves that the first upcoming switch is eligible and that every tap is accepted.

Additional pacing checks include:

- Minimum spacing between solution actions: `0.40` seconds for tutorial through hard and `0.45` seconds for expert.
- Minimum pre-arrival buffer: tutorial `0.15`, easy `0.25`, medium `0.20`, hard `0.20`, expert `0.15` seconds.
- First-tap grace: `0.00` seconds for tutorial and `0.10` seconds for all other difficulties.
- Repeated taps on the same switch must be at least `1.5 ×` the preset spacing outside expert.

If `insufficient_rotation_window` appears, first inspect fan-out, initial route, and required rotation count. Increasing look-ahead may be appropriate, but it changes gameplay rules and therefore requires Python/Swift parity and fixed-seed review.

## Layout profiles

`--layout-orientation` defaults to `portrait_vertical`. The supported choices are `portrait_vertical`, `horizontal`, `vertical`, `mixed`, and `auto`.

`--layout-size-profile` supports:

- `difficulty_curve` — production default. Always tries `standard_portrait` and conditionally adds a large candidate when route length and measured structure justify it.
- `standard_portrait` — bounds `x = -1.2…1.2`, `y = -1.3…1.0`, minimum node distance `0.20`.
- `large_portrait` — bounds `x = -1.15…1.15`, `y = -3.4…1.35`, minimum node distance at least `0.24`.

The difficulty-curve map-size weights are tutorial/easy `1:0`, medium `5:1`, and hard/expert `2:3` for standard versus large. These are inputs to an eligibility policy, not unconditional probabilities: medium large layouts require a structure that benefits from room, while hard and expert also require route length and route-interest evidence.

Large portrait is penalized for tutorial/easy and rejected when the route does not justify the space. Use an explicit profile only for targeted experiments. Review `layoutSizeProfile`, `layoutSizeSelectionReason`, portrait metrics, empty-space ratio, readability issues, and `largeMapFit` in the report.

## Candidate pool sizing

The production defaults are:

| Setting | Default | Purpose |
| --- | ---: | --- |
| `--recipe-pool-size` | 4 | Solved recipe variants considered before layout |
| `--layouts-per-recipe` | 2 | Constructive layout variants per recipe |
| `--road-shapes-per-layout` | 2 | Road-shape strategies per layout |
| `--candidate-pool-size` | 4 | Fully valid, scored candidates retained per level |
| `--max-attempts-per-level` | 120 | Upper bound on candidate-generation attempts |

Candidate breadth is multiplicative, but failed intermediate variants do not enter the valid pool. Increase the dimension associated with the observed bottleneck:

- Topology or strategic-evidence starvation: increase recipe breadth or improve motif composition.
- Readability failures: increase layouts per recipe or fix layout/repair rules.
- Ambiguous switch exits: increase road-shape breadth or fix port assignment.
- Valid but low-scoring/repetitive candidates: increase candidate pool size.
- Pool never fills: inspect rejection counts before increasing max attempts.

For production, keep the pool at four or more unless a documented experiment proves otherwise. A production write with pool size one emits a warning because no meaningful portfolio choice is possible. Playtest portfolio mode defaults to one candidate when the flag is not explicitly overridden; this trades selection quality for batch throughput.

## Quality and diversity weights

The 100-point quality score has five categories:

| Category | Weight |
| --- | ---: |
| Logic | 0.26 |
| Route interest | 0.22 |
| Difficulty fit | 0.20 |
| Layout | 0.18 |
| Diversity | 0.14 |

Within the diversity category, topology/mechanic diversity contributes `0.50`, campaign pacing `0.28`, and uniqueness `0.22`.

After hard gates, batch portfolio selection ranks each candidate with these weights:

| Portfolio component | Weight |
| --- | ---: |
| Individual quality | 0.30 |
| Decision diversity | 0.22 |
| Difficulty fit | 0.15 |
| Visual diversity | 0.10 |
| Distance from production | 0.08 |
| Mechanic progression | 0.08 |
| Adjacent variety | 0.07 |

Decision diversity compares dependency patterns, switch degrees, revisit/reversal behavior, failure outcomes, package phases, and timing patterns. Visual diversity compares layout silhouettes and road-direction histograms. A weight change can alter accepted candidates without changing any hard validation result, so it still requires golden-seed review.

## Updating golden seeds safely

Golden hashes live in `Tools/LevelGenerator/fixtures/fixed_seed_regression_hashes.json`. Never update them merely to make a failing check green.

1. Run the affected suite without updating and save its report:

   ```bash
   python3 Tools/LevelGenerator/run_fixed_seed_regressions.py \
     --suite medium \
     --json-output /tmp/tiny-routes-medium-before.json
   ```

2. Confirm that replay, requested count, quality, semantic gates, and rejection-health assertions pass. The only expected failure should be the deterministic hash when output intentionally changed.
3. Run all suites once before updating:

   ```bash
   python3 Tools/LevelGenerator/run_fixed_seed_regressions.py \
     --json-output /tmp/tiny-routes-all-before.json
   ```

4. Review accepted levels, quality factors, rejection-code distribution, and semantic suites for revisits, high-arity switches, and conditional roads.
5. Update baselines only after that review:

   ```bash
   python3 Tools/LevelGenerator/run_fixed_seed_regressions.py --update-baselines
   ```

6. Review the baseline JSON diff. Unrelated suite hashes should not change without an explanation.
7. Rerun without `--update-baselines`, then run the complete local gate:

   ```bash
   python3 Tools/LevelGenerator/run_fixed_seed_regressions.py
   python3 Tools/LevelGenerator/run_all_generator_checks.py
   ```

For release evidence, use `python3 scripts/run_all_checks.py --reports-dir /tmp/tiny-routes-release`. Add `--swift-tests` when the supported simulator is available.

## Source-of-truth map

- Preset ranges and decision thresholds: `app/services/difficulty_service.py`
- Overall acceptance gates: `app/services/level_generation_service.py`
- Quality categories and ingredients: `app/services/generation_quality_service.py`
- Batch portfolio weights: `app/services/candidate_portfolio_selection_service.py`
- Timing search and safety margins: `app/services/runtime_solution_search_service.py`
- Layout-size eligibility: `app/services/level_generation_service.py`
- Fixed suites and semantic gates: `app/services/fixed_seed_regression_service.py`

Update this guide in the same change whenever a listed threshold, weight, profile, or fixed-seed workflow changes.
