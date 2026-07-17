# Level Editor Manual Usability Test

Use this script to verify that a first-time designer can discover the complete
level-authoring workflow without verbal coaching. The document is the only
instruction the tester may receive.

## Test record

- Tester:
- Date:
- Commit:
- macOS/Xcode version:
- Python version:
- Start time:
- Finish time:
- Result: Pass / Fail

The test passes only when every checkpoint below passes and the tester does not
receive verbal instructions, demonstrations, or hints. The tester may use
labels, tooltips, status messages, validation messages, and **Help > Keyboard
Shortcuts**. Record any confusing label, abandoned attempt, or requested hint
under **Observations**, even if the tester later succeeds.

## Preparation

The facilitator completes only these setup steps, then hands control to the
tester:

1. Use a clean checkout with the editor requirements installed.
2. Confirm that full Xcode and an available iOS Simulator are installed.
3. Create an empty temporary folder where the tester may save JSON files.
4. From the repository root, launch the editor:

   ```bash
   python Tools/LevelEditor/run_level_editor.py
   ```

5. Do not point to controls or otherwise coach the tester during the test.

## Target puzzle

Build a live look-ahead level with this directed route. The two lower branches
are intentional dead ends. The initial route at each switch must lead to its
dead end, so a successful run requires one correctly timed tap at each switch.

```text
start -> switch -> package -> switch_1 -> node -> destination
             |                    |
             v                    v
           node_1               node_2
```

Use these approximate positions. Exact placement is not required, but keep at
least 2 level units between nodes.

| Node | Role | X | Y |
| --- | --- | ---: | ---: |
| `start` | Start | -6 | 0 |
| `switch` | Switch/route | -2 | 0 |
| `package` | Package | 1 | 2 |
| `node_1` | Route/dead end | 1 | -2 |
| `switch_1` | Switch/route | 4 | 2 |
| `node` | Route | 7 | 4 |
| `node_2` | Route/dead end | 7 | 0 |
| `destination` | Destination | 10 | 4 |

## Scenario

### 1. Create a live-routing level

1. Choose **File > New Level**.
2. Select the initial `start` node and delete it so that Start placement is
   exercised rather than inherited from the template.
3. In the Palette, choose **Start**, then click near `(-6, 0)` on the canvas.
4. Choose **Tools > Edit Level Metadata**. Use a non-production level number,
   name the level `Usability Test`, set **Time Limit** to `45`, set **Par Taps**
   to `2`, and apply the changes.
5. Choose **Tools > Edit Level Rules**. Confirm **Schema Version** is at least
   `2`, choose **Live Look-ahead**, set **Look-ahead Seconds** to `2.00`, leave a
   nonzero tap cooldown, and accept.

Checkpoint: the canvas contains a Start node, and reopening **Edit Level
Rules** shows **Live Look-ahead**.

### 2. Place every required piece

Use the Palette and click the canvas to add:

- two **Switch** pieces at the target `switch` and `switch_1` positions;
- one **Package**;
- one **Destination**;
- three **Route Node** pieces for `node`, `node_1`, and `node_2`.

Select each item and use the Properties panel to confirm its ID and adjust its
position if necessary. It is acceptable for the auto-generated route-node IDs
to appear in a different order; rename them in Properties to match the target
table.

Checkpoint: all eight target IDs are visible, and Start, Package, and
Destination have their distinct canvas annotations.

### 3. Connect directed roads

Choose **Connect** (`C`). Create these roads in the listed order by dragging
from a source node's visible connection handle to its destination:

1. `start` to `switch`
2. `switch` to `package`
3. `switch` to `node_1`
4. `package` to `switch_1`
5. `switch_1` to `node`
6. `switch_1` to `node_2`
7. `node` to `destination`

While previewing the first switch branch, press **Tab** and confirm the preview
changes between **Horizontal First** and **Vertical First**. Use **Vertical
First** for both branches leaving each switch so their roads separate clearly.
Press **Escape** once during any unused connection attempt and confirm that the
pending road disappears without adding an edge; resume connecting afterward.

Checkpoint: each switch shows two numbered outgoing options, the canvas has
seven directed roads, and the canceled attempt added nothing.

### 4. Reorder switch options and set initial roads

1. Return to **Select** (`V`) and select `switch`.
2. In Properties under **Outgoing Edge Order**, select the row targeting
   `node_1`, choose **Move Up**, then choose **Set as Initial Route**.
3. Select `switch_1`. Move the row targeting `node_2` to the top and set it as
   the initial route.

Checkpoint: on each switch, option `1` and the initial-road emphasis point to
the dead-end branch. Use Undo and Redo once to confirm the reorder is a single
reversible edit and finishes in the intended state.

### 5. Validate and resolve issues

Choose **Validate**. Double-click each validation message to focus its related
item. Resolve every error before continuing. Typical fixes are missing roads,
overlapping nodes, duplicate IDs, or an incorrect Start/Package/Destination
role. Warnings must be reviewed and recorded under **Observations**; any warning
that describes broken route readability or an invalid solution must be fixed.

Checkpoint: validation shows no errors.

### 6. Playtest and record the solution

1. Choose **Playtest** (`P`). Editing controls should become unavailable and a
   moving dot should appear.
2. Wait for `switch` to receive the active-switch highlight, then click it once.
3. After the package is collected, wait for `switch_1` to receive the highlight
   and click it once.
4. Confirm the run reaches Destination with a completed outcome.
5. Choose **Use Run as Solution** in the Editor Tools toolbar.
6. In the Solution panel, confirm there are two actions, in time order, for
   `switch` and `switch_1`.
7. Choose **Validate** again and resolve any solution error.

If the dot takes a dead-end branch, choose **Reset** and try again. Do not edit
action node IDs or timestamps manually.

Checkpoint: the completed run has replaced the solution, exactly two actions
are present, and validation shows no errors. The editor keeps `maxTaps`
synchronized with the action count automatically.

### 7. Save, reopen, and verify persistence

1. Choose **File > Save Level As** and save `usability_level.json` in the empty
   temporary folder prepared for the test. Do not save into the production
   `Levels` directory.
2. Confirm that the folder contains `usability_level.json` and a solution JSON
   sidecar.
3. Close the level or create a new one, then choose **File > Open Level** and
   reopen `usability_level.json`.
4. Confirm the node positions, seven roads, switch option order, Live
   Look-ahead rules, and two recorded solution actions remain intact.
5. Replay the saved solution from the Solution panel and confirm it completes.

Checkpoint: the reopened document matches the saved document and its solution
replay completes.

### 8. Run Swift verification

Choose **Tools > Run Tests**. If prompted to save, save first. Wait for the test
run to finish and inspect the Validation panel.

Checkpoint: the panel reports `swift_tests_passed`. An unavailable simulator,
missing Xcode installation, timeout, crash, or failed test is a failed
checkpoint; record the output under **Observations**.

## Final acceptance checklist

- [ ] Created a new schema-v2 Live Look-ahead level.
- [ ] Placed Start, Package, Destination, Route Node, and Switch pieces.
- [ ] Connected all roads through visible Connect-mode handles.
- [ ] Discovered and used the Tab road-shape toggle and Escape cancellation.
- [ ] Reordered both switches and set their initial dead-end roads.
- [ ] Completed a two-tap playtest and saved the run as the solution.
- [ ] Cleared all validation errors.
- [ ] Saved and reopened both the level and solution without data loss.
- [ ] Replayed the reopened solution successfully.
- [ ] Swift tests passed.
- [ ] No verbal instruction, demonstration, or hint was provided.

## Observations

Record the step number, what the tester expected, what happened, and whether the
tester recovered without help. Attach screenshots or validation output when
useful.

| Step | Observation | Recovered without help? |
| --- | --- | --- |
| | | |
