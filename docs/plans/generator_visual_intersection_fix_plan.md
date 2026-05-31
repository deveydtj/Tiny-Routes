# Generator Visual Intersection Fix Plan

## Goal

Fix the Tiny Routes level generator so newly generated levels do not contain roads that visually look like connected intersections unless the level graph actually contains a playable node at that location.

The immediate example is the Level 016-style issue where two route lines appear to intersect or merge near the destination path, but the graph has no switch or junction there. The dot therefore follows the graph correctly, while the player sees what looks like a missing intersection. This plan fixes the generator and validation pipeline only. Existing production level JSON files should not be edited in this work.

## Scope

In scope:

- Generator validation logic.
- Generator road-shape scoring logic.
- Generator templates and template layout safeguards.
- Generator reports and diagnostics.
- Python generator tests.
- Dry-run generation checks.

Out of scope:

- Do not edit `TinyRoutes/Resources/Levels/*.json`.
- Do not edit `TinyRoutesTests/Resources/LevelSolutions/*.solution.json` as part of the fix.
- Do not manually patch Level 016.
- Do not change gameplay runtime behavior unless a later separate task proves the runtime is wrong.
- Do not change Swift UI rendering just to hide a generator defect.

## Problem Summary

The generator currently allows some layouts where the rendered road geometry creates a false visual promise. A road can cross, touch, overlap, or pass very close to another road in a way that looks like a usable intersection. If no graph node exists at that point, the player expects the dot to turn but the engine continues along the only valid graph edge.

The generator needs to reject these candidates before they are written. The desired rule is simple:

> If the player can reasonably read two roads as connected, the graph must contain a real node that supports that connection. Otherwise, the layout is invalid.

## Target Files

Primary files likely to change:

- `Tools/LevelGenerator/app/services/visual_clarity_validation_service.py`
- `Tools/LevelGenerator/app/services/road_shape_service.py`
- `Tools/LevelGenerator/app/services/generated_level_validation_service.py`
- `Tools/LevelGenerator/app/services/generation_quality_service.py`
- `Tools/LevelGenerator/app/templates/return_loop_template.py`
- `Tools/LevelGenerator/tests/test_visual_clarity_validation_service.py`
- `Tools/LevelGenerator/tests/test_road_shape_service.py`
- `Tools/LevelGenerator/tests/test_generated_level_validation_service.py`
- `Tools/LevelGenerator/tests/test_generation_quality_service.py`
- `Tools/LevelGenerator/tests/test_templates_return_loop.py`

Only add or update generator code, generator tests, and generator documentation. Do not update generated production level or solution files.

## Desired Validation Rules

Add generator validation for these design defects.

### 1. Implicit intersection without graph node

Reject a candidate when two road segments intersect at a point that is not represented by a graph node.

Error code:

```text
implicit_intersection_without_graph_node
```

Example message:

```text
Edges 'edge_a' and 'edge_b' visually intersect at (0.42, -0.10), but no route node exists there.
```

### 2. Road crosses through unconnected node

Reject a candidate when a road segment passes through or very near an existing node that is not one of that edge's endpoints.

Error code:

```text
road_crosses_through_unconnected_node
```

Example message:

```text
Edge 'edge_a' passes through node 'switch_b' without being connected to it.
```

### 3. Unconnected road endpoint touches another road

Reject a candidate when a road endpoint lands close enough to another road segment that it reads as connected, but the graph does not connect those entities.

Error code:

```text
unconnected_road_endpoint_touches_segment
```

Example message:

```text
Edge 'edge_a' ends near edge 'edge_b' without a shared graph node.
```

### 4. Unconnected parallel overlap

Reject or heavily penalize a candidate when two roads overlap or run directly on top of each other without being the same intended route segment.

Error code:

```text
unconnected_parallel_road_overlap
```

Example message:

```text
Edges 'edge_a' and 'edge_b' visually overlap without a valid shared route node.
```

### 5. Return-loop false shortcut

Reject a candidate when a return-loop path visually touches or closely parallels the route to the destination before the dot reaches the intended return switch.

Error code:

```text
return_loop_false_shortcut
```

Example message:

```text
Return-loop edge 'edge_return_alpha' visually creates a shortcut into destination edge 'edge_alpha_destination'.
```

## Implementation Plan

### Phase 1: Reproduce and document the issue without editing level JSON

- [ ] Open `TinyRoutes/Resources/Levels/level_016.json` only as a reference example.
- [ ] Do not save or modify `level_016.json`.
- [ ] Sketch the issue in notes using the node IDs and edge IDs, especially the return-loop route and destination route.
- [ ] Identify which generated edge pair creates the visual false intersection.
- [ ] Add a short test comment explaining that this is a Level 016-style regression fixture, not a production-level patch.
- [ ] Run the current generator tests before changing code:

```bash
python -m pytest Tools/LevelGenerator/tests
```

- [ ] Run the generator smoke test before changing code:

```bash
python Tools/LevelGenerator/generate_levels.py --start 99 --count 2 --difficulty easy --template mixed --seed 123 --dry-run
```

- [ ] Save the before/after command results in local notes or in the PR description.

### Phase 2: Add reusable visual geometry helpers

Add helper methods inside `VisualClarityValidationService` first. If the helpers become too large, extract them into a small generator-only service later.

- [ ] Add a helper that returns all road segments with edge ID, from-node ID, to-node ID, segment start, segment end, and segment index.
- [ ] Reuse the existing `_SegmentRef` model where possible.
- [ ] Add a helper to find the nearest graph node to a point within a small tolerance.
- [ ] Add a helper to determine whether an intersection point is exactly at a valid shared endpoint.
- [ ] Add a helper to determine whether two edges are intentionally connected through a shared graph node.
- [ ] Add a helper to determine whether a point is inside the interior of a segment instead of only at the segment endpoint.
- [ ] Add a helper to calculate endpoint-to-segment distance for non-connected edges.
- [ ] Keep all tolerances named as class constants near the existing spacing constants.

Suggested constants:

```python
implicit_intersection_node_tolerance = 0.035
unconnected_endpoint_touch_distance = 0.09
unconnected_node_road_clearance = 0.10
unconnected_parallel_overlap_min_length = 0.12
return_loop_false_shortcut_clearance = 0.14
```

Entry-level implementation notes:

- [ ] Do not hard-code Level 016 node IDs in validation logic.
- [ ] Build rules from geometry and graph connectivity.
- [ ] Keep helper names plain and specific.
- [ ] Add small docstrings to non-obvious helpers.
- [ ] Avoid using Swift board pixel sizes in the Python generator. Keep everything in normalized board coordinates.

### Phase 3: Implement implicit-intersection detection

Update `VisualClarityValidationService._route_crossing_issues()` or add a new private method called from `report_for_level()`.

Recommended method name:

```python
def _implicit_intersection_issues(...):
```

Tasks:

- [ ] Iterate every pair of road segments.
- [ ] Skip pairs from the same edge.
- [ ] Find the intersection point using the existing segment-intersection helper.
- [ ] If there is no intersection, continue.
- [ ] If the edges share a real endpoint node and the intersection is at that shared node coordinate, allow it.
- [ ] If a real graph node exists at the intersection, verify that both edges are actually connected to that node.
- [ ] If no graph node exists at the intersection, add `implicit_intersection_without_graph_node` as an error.
- [ ] If a graph node exists but one or both edges are not connected to it, add `road_crosses_through_unconnected_node` as an error.
- [ ] Include both edge IDs in `related_edge_ids`.
- [ ] Include the nearest related node ID when helpful.
- [ ] Add the new method into `report_for_level()` before scoring.

Acceptance criteria:

- [ ] A normal L-shaped road made of two segments from the same edge is not flagged.
- [ ] Two edges meeting at their real shared node are not flagged.
- [ ] Two edges crossing away from any node are flagged.
- [ ] A road passing through a switch that is not connected to that road is flagged.

### Phase 4: Implement endpoint-touch and parallel-overlap detection

Update `VisualClarityValidationService._route_overlap_issues()` or add a dedicated method.

Recommended method names:

```python
def _unconnected_endpoint_touch_issues(...):
def _unconnected_parallel_overlap_issues(...):
```

Tasks:

- [ ] For every segment endpoint, compare it against every non-connected segment.
- [ ] Ignore cases where the endpoint belongs to a shared graph node and the other segment is connected to that same node.
- [ ] If endpoint-to-segment distance is below the configured clearance, add `unconnected_road_endpoint_touches_segment`.
- [ ] For collinear segments, calculate overlap length.
- [ ] If overlap length exceeds the threshold and the edges are not intentionally connected, add `unconnected_parallel_road_overlap`.
- [ ] Treat a repeated edge pair as one issue; do not spam duplicate messages.
- [ ] Include both edge IDs in the report.

Acceptance criteria:

- [ ] Roads may meet cleanly at shared graph nodes.
- [ ] Roads may pass near each other if the clearance is visibly safe.
- [ ] Roads that almost touch without graph connectivity are rejected.
- [ ] Roads that overlap without graph connectivity are rejected.

### Phase 5: Add return-loop-specific false-shortcut detection

Return-loop levels are more vulnerable because a repeated switch can make the correct path intentionally backtrack. The generator must ensure the backtracking does not visually imply a shortcut.

Tasks:

- [ ] Use solution metadata or the required path to detect repeated-node routes.
- [ ] Identify repeated switch nodes in the required path.
- [ ] Identify return edges that lead back toward a repeated switch.
- [ ] Identify destination-bound edges that leave that repeated switch after the return.
- [ ] Compare return-edge segments against destination-bound edge segments.
- [ ] If they intersect, touch, overlap, or run inside the false-shortcut clearance before the repeated switch, add `return_loop_false_shortcut` as an error.
- [ ] Include the repeated switch ID as `related_node_id`.
- [ ] Include the return edge and destination edge in `related_edge_ids`.

Acceptance criteria:

- [ ] A clean return loop with visually separate roads passes.
- [ ] A return loop that visually merges into the destination path before the repeated switch fails.
- [ ] The rule is based on required-path structure, not hard-coded template names.

### Phase 6: Ensure visual-clarity errors reject candidates

`GeneratedLevelValidationService` already converts visual clarity issues into generator messages. Make sure the new visual-clarity errors stop candidates from being accepted.

Tasks:

- [ ] Confirm `_visual_clarity_messages()` passes through severity exactly.
- [ ] Confirm the generator rejects candidates when `GeneratorValidationResult.has_errors` is true.
- [ ] Add a test proving a generated level with `implicit_intersection_without_graph_node` fails validation.
- [ ] Add a test proving a generated level with `return_loop_false_shortcut` fails validation.
- [ ] Confirm warnings still lower quality but do not necessarily reject candidates.

Acceptance criteria:

- [ ] All new issue codes with severity `error` prevent candidate acceptance.
- [ ] The CLI report lists the failed issue code and edge IDs.
- [ ] Dry-run generation does not write files when candidates fail.

### Phase 7: Improve road-shape scoring so the generator avoids bad candidates early

Validation rejection is necessary, but the generator should also prefer road shapes that avoid false intersections.

Update `RoadShapeService.plan_for_graph()` scoring.

Tasks:

- [ ] Add issue detection for implicit intersections inside road-shape candidate scoring.
- [ ] Penalize road-shape assignments that create implicit intersections.
- [ ] Penalize assignments that create unconnected endpoint touches.
- [ ] Penalize assignments that create long unconnected parallel overlaps.
- [ ] Penalize required-path crossings more strongly than decorative crossings.
- [ ] Add metadata issue strings that match the new visual clarity concepts where practical.
- [ ] Keep existing switch-direction scoring intact.
- [ ] Do not make road-shape planning depend on Level 016 specifically.

Suggested scoring changes:

```python
score -= implicit_intersection_count * 0.30
score -= unconnected_endpoint_touch_count * 0.22
score -= unconnected_parallel_overlap_count * 0.18
score -= return_loop_false_shortcut_count * 0.35
```

Acceptance criteria:

- [ ] If one road-shape assignment avoids a fake intersection, it scores higher than an assignment that creates one.
- [ ] If all assignments are bad, validation still rejects the candidate.
- [ ] Existing switch clarity behavior does not regress.

### Phase 8: Update return-loop template safeguards

The generator can still waste candidates if the return-loop template naturally places roads too close together. Adjust template positions only in generator templates, not production level JSON.

Tasks:

- [ ] Review `ReturnLoopTemplate` variants: `return_loop_classic`, `return_loop_upper`, and `return_loop_lower`.
- [ ] Increase spacing between return-path nodes and destination-path nodes.
- [ ] Avoid placing the return edge and destination edge on the same horizontal or vertical corridor.
- [ ] Avoid placing the destination edge immediately beside the package-return path.
- [ ] Keep the intended mechanic: collect package, route through beta switch, return to alpha switch, then route to destination.
- [ ] Keep route length inside the medium difficulty range.
- [ ] Keep required tap count unchanged unless the template design intentionally changes.
- [ ] Add comments explaining the spacing constraints so future edits do not reintroduce false shortcuts.

Acceptance criteria:

- [ ] Return-loop generated candidates pass the new visual-clarity rules.
- [ ] The template still creates repeated-switch gameplay.
- [ ] The template does not require production level JSON edits.

### Phase 9: Add focused Python tests

Create small, direct tests first. Avoid huge integration tests until the geometry rules are proven.

Add or update `Tools/LevelGenerator/tests/test_visual_clarity_validation_service.py`.

Tests to add:

- [ ] `test_reports_implicit_intersection_without_graph_node()`
- [ ] `test_allows_edges_that_meet_at_shared_graph_node()`
- [ ] `test_reports_road_crosses_through_unconnected_node()`
- [ ] `test_reports_unconnected_endpoint_touches_segment()`
- [ ] `test_reports_unconnected_parallel_road_overlap()`
- [ ] `test_reports_return_loop_false_shortcut()`
- [ ] `test_clean_return_loop_does_not_report_false_shortcut()`

Add or update `Tools/LevelGenerator/tests/test_generated_level_validation_service.py`.

Tests to add:

- [ ] `test_visual_clarity_error_rejects_generated_candidate()`
- [ ] `test_return_loop_false_shortcut_rejects_generated_candidate()`

Add or update `Tools/LevelGenerator/tests/test_road_shape_service.py`.

Tests to add:

- [ ] `test_road_shape_plan_penalizes_implicit_intersection()`
- [ ] `test_road_shape_plan_prefers_assignment_without_false_shortcut()`

Add or update `Tools/LevelGenerator/tests/test_templates_return_loop.py`.

Tests to add:

- [ ] `test_return_loop_variants_pass_visual_clarity_validation()`
- [ ] `test_return_loop_variants_keep_repeated_switch_required_path()`

Test fixture guidance:

- [ ] Build minimal level objects directly in tests.
- [ ] Do not load production `level_016.json` as a fixture that the test modifies.
- [ ] Do not snapshot generated production JSON.
- [ ] Keep each fixture small enough that a new engineer can inspect it visually from the coordinates.

### Phase 10: Improve reports and debugging output

When a candidate fails for a fake-intersection issue, the report should make it easy to fix.

Tasks:

- [ ] Include `related_edge_ids` for all new visual-clarity issues.
- [ ] Include `related_node_id` when the issue is near a node or repeated switch.
- [ ] Add issue counts to existing visual clarity metadata automatically through the existing report flow.
- [ ] Confirm markdown and JSON reports include the new issue codes.
- [ ] Confirm failed candidate debug files contain enough data to reproduce the issue.
- [ ] Do not add screenshots or generated production level files to the commit.

Acceptance criteria:

- [ ] A failed dry run clearly names the issue code.
- [ ] The report identifies both conflicting edges.
- [ ] A developer can find the problem without opening the game.

### Phase 11: Run targeted validation commands

Run these commands after the focused tests pass.

```bash
python -m pytest Tools/LevelGenerator/tests/test_visual_clarity_validation_service.py
python -m pytest Tools/LevelGenerator/tests/test_road_shape_service.py
python -m pytest Tools/LevelGenerator/tests/test_generated_level_validation_service.py
python -m pytest Tools/LevelGenerator/tests/test_templates_return_loop.py
```

Then run the full generator test suite:

```bash
python -m pytest Tools/LevelGenerator/tests
```

Then run the generator check suite:

```bash
python Tools/LevelGenerator/run_all_generator_checks.py
```

Acceptance criteria:

- [ ] Targeted tests pass.
- [ ] Full generator tests pass.
- [ ] Generator checks pass.
- [ ] No production level JSON files are modified.
- [ ] No production solution JSON files are modified.

### Phase 12: Run dry-run generation batches

Use dry-run batches so the generator is tested without writing production levels.

Commands:

```bash
python Tools/LevelGenerator/generate_levels.py --start 16 --count 1 --difficulty medium --template return_loop --seed 123 --dry-run
python Tools/LevelGenerator/generate_levels.py --start 16 --count 10 --difficulty medium --template return_loop --seed 123 --dry-run
python Tools/LevelGenerator/generate_levels.py --start 1 --count 30 --difficulty auto --template mixed --seed 1234 --dry-run
```

Optional stress commands:

```bash
python Tools/LevelGenerator/generate_levels.py --start 31 --count 25 --difficulty hard --template mixed --seed 5678 --dry-run
python Tools/LevelGenerator/generate_levels.py --start 41 --count 25 --difficulty expert --template mixed --seed 91011 --dry-run
```

Acceptance criteria:

- [ ] Return-loop dry runs produce accepted candidates without fake-intersection errors.
- [ ] Mixed auto dry runs still produce enough accepted candidates.
- [ ] The new validation does not make generation fail too often.
- [ ] Reports show fewer visual confusion issues.

### Phase 13: Guard against over-rejection

The new rules should catch fake intersections without rejecting all interesting road layouts.

Tasks:

- [ ] Review at least 10 accepted dry-run previews from mixed generation.
- [ ] Confirm legitimate four-way intersection templates still pass when they contain real graph nodes.
- [ ] Confirm decorative crossings can still be allowed when they are visibly separated and not misleading.
- [ ] If too many candidates fail, tune only the clearance constants first.
- [ ] If tuning constants is not enough, update template spacing and road-shape scoring before relaxing hard errors.

Acceptance criteria:

- [ ] The generator still creates varied levels.
- [ ] Real intersections remain possible.
- [ ] Fake intersections are rejected.
- [ ] No validation rule is hard-coded around one production level.

## Suggested Task Order for an Entry-Level Software Engineer

Work in this order to keep each step small and testable.

1. Add one failing unit test for `implicit_intersection_without_graph_node`.
2. Implement the smallest geometry helper needed to make that test pass.
3. Add one passing unit test for a valid shared-node intersection.
4. Add the unconnected-node crossing test.
5. Implement the unconnected-node crossing rule.
6. Add endpoint-touch and parallel-overlap tests.
7. Implement endpoint-touch and parallel-overlap rules.
8. Add the return-loop false-shortcut test.
9. Implement return-loop false-shortcut detection.
10. Add generated-level validation tests proving the errors reject candidates.
11. Update road-shape scoring to prefer safer assignments.
12. Update return-loop template spacing if dry runs reject too many return-loop candidates.
13. Run targeted tests.
14. Run full generator tests.
15. Run dry-run generation batches.
16. Check `git status` and confirm no production level or solution JSON files changed.
17. Write the PR summary with before/after behavior and commands run.

## Definition of Done

This work is complete when all of the following are true:

- [ ] The generator rejects road layouts with implicit visual intersections that do not have graph nodes.
- [ ] The generator rejects roads that visually pass through unconnected switches or important nodes.
- [ ] The generator rejects false shortcuts in return-loop layouts.
- [ ] The road-shape planner prefers safer road-shape assignments when possible.
- [ ] Return-loop templates generate readable repeated-switch layouts.
- [ ] Python tests cover the new rules.
- [ ] Generator dry-run batches complete successfully.
- [ ] Reports expose the issue code, related node, and related edge IDs.
- [ ] No existing production level JSON files are edited.
- [ ] No existing production solution JSON files are edited.

## PR Checklist

Before opening the PR:

- [ ] Confirm `git diff -- TinyRoutes/Resources/Levels` is empty.
- [ ] Confirm `git diff -- TinyRoutesTests/Resources/LevelSolutions` is empty.
- [ ] Confirm all changed files are generator code, generator tests, or generator docs.
- [ ] Paste the targeted test commands into the PR description.
- [ ] Paste the dry-run generation commands into the PR description.
- [ ] Mention that production levels should be regenerated in a separate follow-up after this generator fix lands.
