# Optional Map Seed Import

Map import is an optional seed source for future Tiny Routes levels. It is not part of the normal procedural generation path and should not be required for production level generation.

Public map data can provide interesting road geometry, but it does not automatically produce readable, fun, solvable puzzles. The intended flow is:

```text
map data -> simplified seed graph -> Tiny Routes procedural template -> validated level
```

OpenStreetMap data requires attribution and license review before generated map-inspired work is shipped. Prefer small bounding boxes or local extracts, and do not hammer public APIs.

Install optional dependencies only when working on this feature:

```bash
python -m pip install -r Tools/LevelGenerator/requirements-map.txt
```
