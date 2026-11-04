# Multi-Van two-person playtest kit (MV-47)

Use this sheet for two separate, independent sessions on the same physical iPhone. It collects early usability evidence; it does not satisfy the plan's broader five-person acceptance criteria or constitute TestFlight signoff. Do not change gameplay, levels, scoring, or defaults during these sessions.

## Objective

See whether two people new to the prototype can understand and complete its twelve levels, especially the live-switch and collision puzzles, and collect evidence for the later TestFlight decision. Record what happened, not what you expected them to do. Use anonymous codes **P1** and **P2** only; collect no names, contact details, or device identifiers.

## Before each participant

- [ ] Charge the iPhone; use the same device, orientation, sound setting, and reasonably quiet setting for both people. Note device model/iOS if readily available.
- [ ] Ask whether they have seen this prototype before. Prefer people who have not; note prior exposure without collecting identifying details.
- [ ] For the internal TestFlight configuration, enable **Settings → About → Multi-Van Prototype**, then return Home and tap **Prototype**. The list and gameplay show **Default tuning · Speed 1.50 · Collision 0.35 · Lock 0.40**. This build has no tuning panel and ignores saved Debug overrides. For a Debug build, open **Tuning · …** in the prototype list, tap **Reset to defaults** unless a source-plan-approved configuration says otherwise, and confirm **Default configuration** / **Tuning · Defaults**.
- [ ] Record the effective settings separately below: van speed **1.50 grid units/s**, collision distance **0.35 grid units**, live-switch lock radius **0.40 grid units** for defaults. Record build/content identity and any deviation. JSONL does not record tuning.
- [ ] Start a fresh participant session at **Level 1 Go!**. Use **Retry/Replay** only as the participant's retries; if leaving the prototype and reopening it, record that boundary. Each new level uses the current tuning; Retry/Replay retain that level's configuration.
- [ ] Do not delete or clear the append-only local log to separate people. Preserve existing records; see **Export and separate logs**.
- [ ] Keep this sheet and a pen/timer ready. Do not record audio/video unless separately arranged; it is unnecessary for this kit.

Participant code: `P__`  Date: `________`  New to prototype? `Yes / No / Unsure`

Device/build: `________________________`  Orientation: `Portrait / Other`  Sound: `On / Off`

Effective tuning (record actual values): speed `______`  collision distance `______`  lock radius `______`

Configuration: `Default / Experimental (describe): __________________________`  Fresh session boundary/time: `________________`

## Facilitator procedure

Run P1 and P2 separately. Reset and verify tuning before **each**. Follow levels 1–12 in order; let the participant advance at their own pace. No session duration is imposed by the plan; allow time to finish the full sequence, and note any interruption or level they leave on. Keep the environment and device setup consistent.

1. Give the phone to the participant at Level 1. Say only: **“Please play this game as you normally would. You can stop whenever you like.”** Do not explain the puzzle rules or route-preview meaning. Watch Levels 1–3 silently as required by the source plan. Note spontaneous questions and any help you had to give; do not coach.
2. After Level 3, continue observing quietly. Answer a direct control question with a short, neutral clarification of the control only (for example, “Tap Go to start the vans” or “Tap a switch to change its route”). Do not explain a solution, timing, or what a preview means. Record the question and clarification.
3. Let the participant experiment through retries. Do not suggest a route or tap time. If stuck, use the escalation guidance below and mark the level assisted. Never count a hinted/solved-for participant level as independent.
4. Observe every level, then ask the short interview questions. Capture their words briefly without interpreting them.
5. Return to the prototype list and export the local log. Associate the exported file with participant code, session boundaries, build, and tuning notes.

### When to intervene

- **Allow experimentation:** when they are trying switches, route options, Go, Retry, or Stop; remain quiet and give them time. Record attempts and visible uncertainty.
- **Neutral clarification:** only when they ask how to operate a control or cannot proceed because a control is unclear. Explain the control, not its consequence or best choice. Mark `clarification` and do not call the result fully unassisted if it materially enabled progress.
- **Hint:** if they are unable to proceed after sustained attempts and ask for help, offer one progressively specific hint without naming an exact action first: “Look at what happens where the roads meet”; then, only if needed, “Try the other route for one van.” Record exact hint/count and mark subsequent completion **assisted**.
- **Move on:** if they ask to skip, or remain stuck after a hint and another attempt, let them move on or stop. Do not solve it for them. Record `not completed`, attempts, help, and their stopping point. Do not impose a time cutoff absent from the plan.

**Independent success** means they complete the level without facilitator clarification, hint, or solution guidance. A neutral control clarification is documented and flagged as assisted for conservative reporting. A hint always means assisted success. Log completion is objective; assistance status requires facilitator notes.

## Level-by-level observation sheet

Fill a row for each level and participant. `Time` is elapsed wall-clock time from opening the level to advancing/leaving, approximate is fine; JSONL plan-phase time is not the same measure. The log can supply attempts, outcomes/failure reasons, plan-phase seconds, changes vs par, fast-forward use, switch taps/events, and quit markers. It has anonymous session IDs, not participant codes or tuning. Use facilitator notes for completion independence, hints, observed confusion, explanation of failure, touch/timing difficulty, comments, and level time if desired. Avoid duplicating logged counts unless needed to interpret a gap.

| P# | Level / title | Independent? Y/N | Attempts* | Hints / clarifications | Time (approx.) | Common failures / logged fail reasons | Confusing UI or visual? | Live-switch timing a problem? | Participant comment | Facilitator observation |
|---|---|---|---:|---|---|---|---|---|---|---|
| | 1 Go! | | | | | | | N/A | | |
| | 2 Pick a Lane | | | | | | | N/A | | |
| | 3 Two Turns | | | | | | | N/A | | |
| | 4 Roundabout | | | | | | | N/A | | |
| | 5 Two Colours | | | | | | | N/A | | |
| | 6 Convoy | | | | | | | | | |
| | 7 Merge | | | | | | | N/A | | |
| | 8 Hold the Loop | | | | | | | | | |
| | 9 Split | | | | | | | | | |
| | 10 Three's Company | | | | | | | N/A | | |
| | 11 Rush | | | | | | | | | |
| | 12 Big Delivery | | | | | | | | | |

\* Prefer JSONL attempt counts where session boundaries can be established. Include retries/replays according to the log summary and note any mismatch. `N/A` means the level has no live-switch timing task.

### Priority prompts for observation (do not read these to the player)

- **1–5 progression:** Does the player discover Go, switches, route choices, colour matching, and three-way cycling? Does each new idea build on the last? Note any confusion or unexpectedly easy/hard step.
- **6 Convoy:** Baseline measured usable live-switch window is **0.967 seconds** (simulation window, not a human reaction-time measurement). Does the player realize switching is needed during the run, understand when to tap, repeatedly miss it, understand why a failure occurred, and complete it independently? Distinguish rejected/locked taps, accepted but unsuccessful taps, and uncertainty about the cue where observable. Narrow timing alone is not proof that tuning must change.
- **7 Merge:** Do they understand that two correct-looking previews can still collide? Is the crash point visually clear? Does failure feedback explain the cause? Do they discover the detour without help?
- **8 Hold the Loop:** Baseline initial usable opportunity is **4.808 seconds**, with later opportunities available. Do they understand why the loop is useful, distinguish the live switch's locked/available states, and work out how/when to release the van? Note if they miss one opportunity and notice another.
- **9 Split:** Does the player understand the required action and notice the lock indicator? Does the switch feel fair, and can they time it? Baseline usable window is **1.417 seconds**. Separate understanding/cue issues from touch execution.
- **10–12:** Does difficulty progress logically? Do earlier mechanics transfer? Is Level 10 a useful consolidation? Does Level 12 feel like an appropriately challenging finale? Do repeated failures teach something or seem arbitrary?

## Post-test interview

Ask neutrally, after play. The first three questions are the source plan's questions; the rest address this kit's required usability checks.

1. “What were you trying to do?”
2. “Which level was best for you, and which was worst?”
3. “Would you play more?”
4. “How clear were the goals?”
5. “How useful were the route previews?”
6. “What did the locked switches communicate to you?”
7. “How did the vans’ movements make sense or not make sense?”
8. “When something went wrong, what did you think happened?”
9. “How, if at all, did you use fast-forward?”
10. “What did you think of the delivery and win effects?”

Notes (participant's wording where useful): `______________________________________________________________`

## Export and separate logs

The local JSONL is append-style and can contain multiple anonymous sessions. It is not automatically uploaded. Never assume one export is one participant, and do not delete prior records to create a boundary.

1. Finish the level or leave it using **Levels** (if still in a level) to return to **Multi-Van Prototype** list. Avoid **Close** until ready to exit; leaving may record a quit marker.
2. In the list, open **Playtest log**. The screen shows a per-level summary and **Share Playtest Log**.
3. Tap **Share Playtest Log**. In the iOS share sheet, save the `.jsonl` attachment to the agreed local folder (for example, Files/iCloud Drive if the facilitator's normal workflow uses it) or AirDrop it to the facilitator's Mac. Sharing is an explicit action; do not upload automatically.
4. Confirm the saved attachment exists, is nonempty, and opens as readable UTF-8 JSON Lines (one JSON record per line). If sharing fails or no records exist, note that; a local log on the phone is not a successful export.
5. Label the file with anonymous participant code and session date/boundary **without altering the JSONL**, and store alongside a note containing build/content identity and the effective tuning tuple/status. The file itself lacks tuning and P1/P2 labels.

To separate sessions, use recorded start/end times and log session IDs/events if available, plus level order and facilitator notes. The UUID session ID is anonymous but does not identify a participant; `quit_at_level` may mark backgrounding, closing, or leaving. An export can include previous participants and unrelated prototype use. If boundaries are ambiguous, report the combined log and do not attribute uncertain rows to P1/P2. Keep files locally with restricted access and remove them when no longer needed under the team's normal data-retention practice.

## Physical-iPhone verification (developer checklist)

Review on the actual intended iPhone/build; source-level checks do not establish device behavior. Keep ordinary gameplay observations separate from accessibility checks. Do not ask a participant to use accessibility settings they do not normally use.

| Device check | Result / issue |
|---|---|
| Board visible in portrait orientation | |
| Four van colors distinguishable | |
| Overlapping route previews readable | |
| House and van artwork clear | |
| Delivery animations render well | |
| Crash effects readable and not obscuring needed information | |
| Sound quality and latency | |
| Haptic response | |
| Touch targets usable | |
| Hold-to-fast-forward works and releases cleanly | |
| Share sheet opens and attachment can be saved/shared | |
| Return to gameplay after sharing works | |
| Larger Dynamic Type layout | |
| VoiceOver labels, focus order, and operation | |
| Reduce Motion behavior | |

## Two-person results summary

Complete after both independent sessions. Keep observed facts distinct from interpretation. Two people can reveal problems but cannot satisfy criteria written for five people.

| Measure | P1 | P2 | Combined / evidence |
|---|---|---|---|
| Levels reached / completed (of 12) | | | |
| Independent completions / completed levels | | | |
| Assisted completions and where help was needed | | | |
| Attempts and failures by level (JSONL where attributable) | | | |
| Level 7–12 attempts; mean per level and participant (descriptive only) | | | |
| Level 6 timing / misses / understanding | | | |
| Level 7 collision and detour understanding | | | |
| Level 8 loop / lock-state understanding | | | |
| Level 9 timing / lock-indicator understanding | | | |
| Fast-forward use; did they watch most runs? | | | |
| Most common usability issue | | | |
| Participant feedback / would continue? | | | |

**Proposed tuning or product changes (one per row):**

| Proposed change | Observed problem or verified defect | Evidence (participant/level, notes or log records) | Why this change addresses it | Retest needed |
|---|---|---|---|---|
| | | | | |

Known unresolved issues: `___________________________________________________________________`

Log files and boundaries (local paths/labels): `____________________________________________________________`

### Source-plan criteria and direction signals

Copy the plan's thresholds exactly when the full five-person playtest is run. Do not mark the two-person sample as a pass/fail for these thresholds.

| Source-plan criterion / signal | Plan wording / threshold | Two-person evidence (descriptive; no extrapolation) |
|---|---|---|
| Press Go without help by Level 2 | At least **4 of 5** players | P1: ___  P2: ___ (criteria not evaluable with n=2) |
| Levels 7–12 attempts | Average **1–3**; fewer suggests too easy, more too hard | P1: ___  P2: ___; sample is descriptive, not plan acceptance |
| Finish all 12 or ask for more | At least **3 of 5** players | P1: ___  P2: ___ (criteria not evaluable with n=2) |
| Watch runs rather than fast-forward every time | Players watch **most runs** | Notes/log: ___; no numeric threshold specified |
| Crash visibility | If players don't spot crashes before Go, even by Level 9: consider clearer timing / ghost-run preview | Observation: ___ |
| Finding Stop | If players feel trapped watching a known failure and don't find Stop: consider larger/pulsing Stop | Observation: ___ |
| Live-switch planning bypass | If players use live switches to skip planning in Levels 9–12: consider at most one live switch or locking after a van passes | Observation: ___ |
| Run-phase pace | If it feels boring even when short: consider speed, shorter roads, or more vans | Observation: ___ |

**Signoff checklist (record status; no team signoff is implied by this blank form):**

- [ ] P1 and P2 completed separately, or incomplete/stop reason recorded.
- [ ] Default tuning checked/reset and actual effective settings recorded for each.
- [ ] All 12 level rows reviewed; missing observations identified.
- [ ] Logs exported and participant boundaries/configuration associations documented, or export limitation noted.
- [ ] Proposed changes each cite an observed issue or verified defect; no change is based only on a narrow theoretical window.
- [ ] Required retests identified; experimental settings, if later tested, have separate records and are not mixed with defaults.
- [ ] Physical-device checklist completed by developer, with open items noted.
- [ ] Broader five-person plan criteria and team agreement on whether each level's idea comes across remain explicitly open until completed.

Prepared by: `________`  Date: `________`  Status: `Draft / Ready for two sessions / Sessions recorded / Follow-up needed`

## MV-46 baseline to preserve

MV-46 found all twelve levels win at par under deterministic defaults. Experiments at speed **1.3** and lock radius **0.3** preserved the authored solutions; neither established evidence to change defaults. No human playtest records were available. Keep engine defaults, level geometry, solution scripts, scoring, collision behavior, live-switch locking, animation, and production gameplay unchanged during MV-47. Any later proposed fix must cite an observed problem or verified defect and be retested.
