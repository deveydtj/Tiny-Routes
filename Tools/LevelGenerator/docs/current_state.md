# Level Generator Current State

## CLI

Generate levels:

```bash
python Tools/LevelGenerator/generate_levels.py --start 12 --count 1 --difficulty tutorial --template straight_delivery --seed 1 --dry-run
```

Validate generated files:

```bash
python Tools/LevelGenerator/validate_generated_levels.py --levels level_012 level_013
```

Use `python3` on macOS setups that do not provide a `python` shim.

## GUI

Launch the Tkinter wrapper:

```bash
python Tools/LevelGenerator/launch_gui.py
```

The GUI calls the same generation and validation services as the CLI.

## Templates

| Template | Supported Difficulty | Current Layout Behavior |
|---|---|---|
| `straight_delivery` | `tutorial` | Fixed route positions with optional vertical mirror and 0-2 intermediate nodes. |
| `single_switch` | `tutorial`, `easy` | Variant-specific fixed layouts with optional vertical mirror. |
| `package_gate` | `easy`, `medium` | Variant-specific fixed layouts with optional vertical mirror. |
| `return_loop` | `medium` | Variant-specific fixed layouts with optional horizontal mirror. |
| `multi_switch_chain` | `medium`, `hard` | Procedural switch count plus zigzag, stair-step, and split-dead-end variants. |
| `ring_route` | `hard` | Fixed positions with optional vertical mirror. |

## Known Limitations

Some templates still begin from fixed node positions. Candidate signature checks reject exact or near-duplicate candidates within a batch, and medium chain/gate/loop templates now have enough variant signatures for normal mixed batches. Larger production batches should still be reviewed visually because template variety is not a replacement for manual Level Editor review.

## Output Paths

Production level JSON:

```text
TinyRoutes/Resources/Levels
```

Matching solution sidecars:

```text
TinyRoutesTests/Resources/LevelSolutions
```

Generated production levels should always be committed with matching `level_###.solution.json` files. A level without its solution sidecar is not production-ready.
