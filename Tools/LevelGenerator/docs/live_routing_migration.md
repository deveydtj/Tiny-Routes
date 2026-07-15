# Live-Routing Migration Analyzer

Run the read-only corpus analyzer from the repository root:

```bash
python Tools/LevelGenerator/migrate_levels_to_live_routing.py
```

It writes deterministic JSON and Markdown reports to `docs/quality/`. Each
level record includes its serialized and effective rules, current solution
replay, current and expanded-window live-routing searches, required decision
window sizes, repeated-decision evidence, campaign decision-quality result,
and recommendation. The command never changes a level or solution sidecar.

## Migration categories

- **Automatic conversion:** The current solution passes, the topology has a
  legal live-routing solution with its current window, and the measured
  decision profile meets the current campaign difficulty thresholds.
- **Timing/layout adjustment:** The topology becomes schedulable with a larger
  look-ahead, a rotation window is shorter than its legal tap/cooldown margin,
  or decision quality misses only the preset's minimum window. Adjust road
  length or rules, then rerun the analyzer.
- **Manual redesign:** The current solution is invalid, the decision structure
  is too trivial for its campaign position, or the route cannot expose a legal
  live-routing decision schedule. A designer must review the topology.
- **Regeneration:** Live routing is schedulable, but other decision-quality
  requirements do not match the campaign position. Replace the level while
  retaining its `level_###` ID and campaign slot.

Category precedence is deterministic: invalid/trivial content is manual,
window-only failures are timing/layout, fully passing content is automatic,
and remaining replaceable quality mismatches are regeneration.
