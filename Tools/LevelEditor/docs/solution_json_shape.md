# Solution JSON Shape

Solution sidecar files live in `TinyRoutesTests/Resources/LevelSolutions/` and use the filename pattern `level_###.solution.json`. They are loaded by the Level Editor and by the Swift solvability tests.

## Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `levelID` | string | yes | Must match the level `id`. |
| `description` | string | yes | Human-readable summary of the solution. |
| `expectedOutcome` | string | yes | Currently must be `"completed"`. |
| `maxTaps` | integer | yes | Must equal the number of scripted actions. |
| `requiresWithinTimeLimit` | boolean | yes | Whether every action and completion must respect the level time limit. |
| `actions` | array | yes | Ordered timed tap actions. Empty for no-tap levels. |
| `isPlaceholder` | boolean | no | Added by the editor for blank placeholder solutions. |

## Action Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `timeSeconds` | number | yes | Time in seconds when the tap occurs. Must be non-negative and sorted in nondecreasing order. |
| `tapNodeID` | string | yes | Node ID to tap at `timeSeconds`. This should normally reference a switchable node with at least two outgoing edges. |

## Placeholder Behavior

When a level has no sidecar solution file, the editor creates an in-memory placeholder so designers can start editing actions immediately. Placeholder solutions are reported by Validate and should be replaced before shipping.

Opening an existing solution does not silently repair `levelID` or `maxTaps`. Validate reports those metadata problems so broken sidecar files are visible. Once a designer edits actions through the Solution panel, the editor intentionally updates `levelID` to the open level and keeps `maxTaps` equal to the action count.

## Example

```json
{
  "levelID": "level_002",
  "description": "Tap the choice node after the dot reaches the approach.",
  "expectedOutcome": "completed",
  "maxTaps": 1,
  "requiresWithinTimeLimit": true,
  "actions": [
    {
      "timeSeconds": 0.5,
      "tapNodeID": "choice"
    }
  ]
}
```
