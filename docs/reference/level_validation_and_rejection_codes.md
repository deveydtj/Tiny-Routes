# Level Validation and Rejection Codes

## How to read this reference

Codes are stable machine-facing identifiers. Human messages may add node IDs,
edge IDs, measured values, or paths. A suffix after `:` is diagnostic context
and is not part of the code. For example,
`node_count_outside_difficulty_range:12:4-8` has code
`node_count_outside_difficulty_range`.

“Blocks production” describes the current gates:

- **Yes**: the candidate/file cannot be accepted while the code is present.
- **Replay**: normal player input may produce it, but it blocks a saved or
  generated solution when replayed.
- **When error**: some services emit it as a warning/info while stricter
  generator contexts promote it to an error.
- **No**: advisory, informational, or a successful status.

The generator rejects any `GeneratorValidationMessage` with severity `error`.
The editor prevents a clean validation result on `ValidationSeverity.ERROR` but
still lets a designer save drafts. Production-content and Swift replay gates are
the final authority for shipped content.

## Repository and rules decoding

| Code | Stage | Meaning | Typical cause | How to fix | Blocks production |
|---|---|---|---|---|---|
| `missing_file` | File load | Requested level or sidecar does not exist. | Wrong path or absent sidecar. | Restore the file or select the correct path. | Yes |
| `invalid_json` | File load | JSON is malformed or does not match the required shape. | Syntax error, wrong top-level type, or missing required field. | Correct the JSON and required fields. | Yes |
| `io_error` | File load/save | The OS could not read or write the file. | Permissions, missing directory, or disk error. | Fix the path/permissions and retry. | Yes |
| `rules_must_be_an_object` | Rules decode | `rules` is present but is not an object. | Array, string, or scalar supplied as rules. | Serialize a rules object or omit it only for legacy data. | Yes |
| `unknown_switch_interaction_mode` | Rules decode | The interaction mode is not recognized. | Misspelled or future enum value. | Use `legacyGlobal` or `liveLookahead`. | Yes |
| `invalid_switch_lookahead_seconds` | Structure | Look-ahead is negative, nonnumeric, or nonfinite. | Bad inspector/JSON value. | Use a finite number greater than or equal to zero. | Yes |
| `invalid_switch_tap_cooldown_seconds` | Structure | Tap cooldown is negative, nonnumeric, or nonfinite. | Bad inspector/JSON value. | Use a finite number greater than or equal to zero. | Yes |
| `legacy_switch_interaction_mode` | Migration | Level still uses unrestricted legacy interaction. | Missing rules or explicit legacy mode. | Migrate to schema 2 and `liveLookahead`, then regenerate/replay the solution. | Production corpus: Yes; editor warning: No |

## Runtime input and simulation outcomes

Python names are serialized in traces. Swift `SwitchTapResult` cases map to the
nearest row (`rejectedNoLevel` and `rejectedPaused` are Swift-only UI/runtime
states).

| Code | Stage | Meaning | Typical cause | How to fix | Blocks production |
|---|---|---|---|---|---|
| `accepted` | Runtime tap | Tap rotated the eligible switch. | Legal tap in an open window. | None. | No |
| `rejectedNoLevel` | Swift runtime tap | No graph is loaded. | UI sent input before load. | Load/start the level before accepting input. | Replay |
| `rejectedPaused` | Swift/UI runtime tap | Gameplay is paused. | Input reached gameplay while pause is active. | Resume or suppress paused input. | Replay |
| `level_finished` / `rejectedLevelFinished` | Runtime tap | Input arrived after a terminal outcome. | Sidecar tap is later than completion/failure. | Remove/reschedule the tap. | Replay |
| `tap_after_route_commitment` / `rejectedCommitted` | Runtime tap | The dot already committed to an outgoing road at that switch. | Tap timestamp is at or after departure. | Move the tap inside the eligibility window. | Replay |
| `tap_node_is_not_switchable` / `rejectedNotSwitchable` | Runtime tap | Target has fewer than two usable roads. | Wrong tap node or package phase closed choices. | Target a switch and correct availability. | Replay |
| `tap_before_activation_window` | Runtime tap | Correct upcoming switch is still too far away. | Tap is earlier than look-ahead permits. | Move it to the window opening or enlarge a valid window. | Replay |
| `tap_noneligible_switch` / `rejectedNotEligible` | Runtime tap | Target is not the first eligible upcoming switch. | Downstream/off-route switch tapped. | Tap the published eligible switch at the proper route state. | Replay |
| `tap_cooldown` / `rejectedCooldown` | Runtime tap | Time since the last accepted tap is below cooldown. | Repeated taps are too close. | Increase action spacing or lower an intentionally tuned cooldown. | Replay |
| `time_expired` | Simulation outcome | Countdown reached zero before completion. | Route/action timing exceeds the limit. | Shorten route/timing or increase a justified time limit. | Yes |
| `dead_end` | Simulation outcome | Current node has no usable outgoing road. | Wrong branch or invalid availability. | Make the intended replay choose a valid road; repair accidental dead ends. | Yes |
| `reached_destination_without_package` | Simulation outcome | Destination was reached before package collection. | Package bypass. | Force package-first topology and update the sidecar. | Yes |
| `max_step_count_exceeded` | Simulation safety | Movement traversal exceeded its deterministic guard. | Nonterminating cycle or too-small fixture limit. | Repair the cycle or set an intentional fixture limit. | Yes |
| `solution_actions_not_monotonic` | Simulation input | An action goes backward relative to elapsed time. | Unsorted/invalid action stream. | Sort actions and preserve nondecreasing timestamps. | Yes |
| `runtime_search_requires_live_lookahead` | Runtime solution search | Scheduler was asked to solve a non-live level. | Legacy rules entered the new pipeline. | Migrate rules before runtime search. | Yes |
| `activation_window_not_found` | Runtime solution search | Required decision never became eligible. | Topology path and active route diverge or window is unreachable. | Repair topology/initial states/layout timing. | Yes |
| `insufficient_rotation_window` | Runtime solution search | Required rotations do not fit before commitment. | High arity, cooldown, short approach, or small look-ahead. | Lengthen approach/window, reduce rotations, or adjust cooldown. | Yes |
| `runtime_replay_rejected_action` | Runtime solution search | Scheduled action was rejected without a more specific reason. | Scheduler/runtime disagreement. | Inspect tap trace and fix scheduling or parity. | Yes |
| `final_runtime_replay_failed` | Runtime solution search | Complete scheduled script did not finish. | Later route state differs from the topology solution. | Inspect final replay and repair topology/timing. | Yes |

Eligibility diagnostics `eligible`, `outsideLookaheadWindow`,
`noUpcomingSwitch`, `invalidSpeed`, `cycleDetected`, and `stepLimitReached` are
snapshot reasons, not candidate rejection codes. `cycleDetected` and
`stepLimitReached` must still be investigated whenever they prevent a required
solution tap.

## Level identity, graph, and package-state validation

| Code | Stage | Meaning | Typical cause | How to fix | Blocks production |
|---|---|---|---|---|---|
| `missing_level_id` | Structure | Level ID is empty. | Required metadata omitted. | Assign a unique ID. | Yes |
| `missing_level_name` | Structure | Display name is empty. | Required metadata omitted. | Assign a nonempty name. | Yes |
| `non_padded_level_id` | Identity | Production-like ID is not zero padded. | `level_7` instead of `level_007`. | Rename through the identity/rename service. | No |
| `default_level_name_in_production_level` | Identity | Production-like level still says “New Level”. | Draft metadata was never edited. | Give it a reviewed production name. | No |
| `non_padded_level_filename` | Identity | Filename is not canonical. | Manual rename. | Use `level_NNN.json`. | No |
| `level_id_filename_mismatch` | Identity | JSON ID differs from filename stem. | Renamed only file or document. | Rename both with the identity service. | Yes |
| `draft_level_id_in_production_path` | Identity | `new_level` is inside app production resources. | Draft saved to the wrong directory. | Move to drafts or assign a production identity. | Yes |
| `production_metadata_consistent` | Identity info | Filename, level ID, and sidecar ID agree. | Successful production identity check. | None. | No |
| `invalid_time_limit` | Structure | Time limit is not positive numeric data. | Zero, negative, Boolean, or invalid type. | Set a positive number. | Yes |
| `invalid_par_taps` | Structure | Par is not a nonnegative integer. | Negative/fractional/Boolean value. | Set an integer at least zero. | Yes |
| `missing_start_node` | Structure | `startNodeID` is empty. | Required role not assigned. | Assign a start node. | Yes |
| `start_node_not_found` | Structure | Start ID is absent from nodes. | Deleted/renamed node left a stale reference. | Repair the reference or restore the node. | Yes |
| `missing_package_node` | Structure | `packageNodeID` is empty. | Required role not assigned. | Assign a package node. | Yes |
| `package_node_not_found` | Structure | Package ID is absent from nodes. | Stale reference. | Repair the reference or restore the node. | Yes |
| `missing_destination_node` | Structure | `destinationNodeID` is empty. | Required role not assigned. | Assign a destination node. | Yes |
| `destination_node_not_found` | Structure | Destination ID is absent from nodes. | Stale reference. | Repair the reference or restore the node. | Yes |
| `duplicate_node_id` | Structure | More than one node has the same ID. | Copy/manual JSON edit. | Rename nodes uniquely and update references. | Yes |
| `duplicate_edge_id` | Structure | More than one road has the same ID. | Copy/manual JSON edit. | Rename roads uniquely and update outgoing lists. | Yes |
| `duplicate_outgoing_edge_id` | Structure | A node lists one road more than once. | Corrupt outgoing order. | Remove the duplicate while preserving intended order. | Yes |
| `edge_references_missing_node` | Structure | A road endpoint does not exist. | Endpoint node was deleted/renamed. | Repair endpoint or restore node. | Yes |
| `outgoing_edge_id_not_found` | Structure | Node lists a nonexistent road. | Road deleted without reference cleanup. | Remove stale ID or restore road. | Yes |
| `outgoing_edge_wrong_source_node` | Structure | Listed road starts at another node. | Road moved without updating both source lists. | Put it only in its `fromNodeID` node. | Yes |
| `edge_missing_from_source_outgoing_ids` | Structure | Graph road is absent from its source's list. | Manual JSON/editor bug. | Add the road ID in authored rotation order. | Yes |
| `invalid_road_shape` | Structure/geometry | Road shape is unsupported. | Unknown `roadShape`. | Use `horizontalFirst` or `verticalFirst`. | Yes |
| `invalid_road_availability` | Structure/package | Availability value is unsupported. | Misspelled phase. | Use `always`, `beforePackage`, or `afterPackage`. | Yes |
| `switch_has_too_many_outgoing_edges` | Structure | Switch has more than four valid roads. | Overconnected node. | Split the intersection or remove choices. | Yes |
| `conditional_road_dead_end_before_package` | Package structure | Authored node has no road usable before collection. | All roads are `afterPackage`. | Add an `always`/`beforePackage` route or remove the unreachable state. | Yes |
| `conditional_road_dead_end_after_package` | Package structure | Authored node has no road usable after collection. | All roads are `beforePackage`. | Add an `always`/`afterPackage` route or remove the reachable state. | Yes |
| `unreachable_package_node` | Reachability | Package cannot be reached from start ignoring phase. | Disconnected/directed graph. | Connect a directed start-to-package route. | Yes |
| `unreachable_destination_node` | Reachability | Destination cannot be reached from start ignoring phase. | Disconnected/directed graph. | Connect a directed route. | Yes |
| `unreachable_non_critical_node` | Reachability | Ordinary node cannot be reached from start. | Orphan decorative topology. | Connect or delete it. | No |
| `destination_unreachable_from_package_node` | Reachability | No directed package-to-destination route exists. | One-way topology points away from goal. | Add/correct the post-package route. | Yes |
| `package_unreachable_before_collection` | Package reachability | Availability prevents reaching the package in the pre-package phase. | Needed road is `afterPackage`. | Correct phase conditions. | Yes |
| `destination_unreachable_after_collection` | Package reachability | Availability prevents reaching destination after collection. | Needed road closes after package. | Correct phase conditions. | Yes |
| `impossible_road_availability_condition` | Decision/package validation | A conditional road's required phase cannot reach its source. | Condition can never be observed. | Move/remove the road or make its source reachable in that phase. | Yes |
| `irrelevant_road_availability_condition` | Decision/package validation | Conditional road does not change any reachable route state. | Duplicate always route or unreachable opposite phase. | Remove it or redesign a real phase-dependent choice. | Yes |

## Solution sidecar validation

| Code | Stage | Meaning | Typical cause | How to fix | Blocks production |
|---|---|---|---|---|---|
| `missing_solution` | Sidecar structure | No sidecar is loaded. | Missing file. | Create/record a verified sidecar. | Yes |
| `solution_level_id_mismatch` | Sidecar identity | Sidecar level ID differs from document ID. | Copied or renamed sidecar. | Update sidecar identity and replay. | Yes |
| `solution_level_id_filename_mismatch` | Sidecar identity | Sidecar ID differs from canonical filename identity. | Partial production rename. | Normalize file, level ID, and sidecar ID together. | Yes |
| `invalid_expected_outcome` | Sidecar structure | Expected outcome is not `completed`. | Failure script used as production solution. | Record a completing script. | Yes |
| `invalid_max_taps` | Sidecar structure | `maxTaps` is not a nonnegative integer. | Invalid metadata. | Set it to the accepted action count. | Yes |
| `max_taps_less_than_action_count` | Sidecar structure | Declared cap is below action count. | Stale metadata. | Set `maxTaps` to action count. | Yes |
| `max_taps_greater_than_action_count` | Sidecar structure | Declared cap exceeds action count. | Stale/placeholder metadata. | Set `maxTaps` to action count. | Yes |
| `solution_marked_placeholder` | Sidecar policy | Script is explicitly a placeholder. | Generated/manual stub. | Replace with a verified replay and clear the flag. | Generator: Yes; editor warning |
| `solution_requires_without_time_limit` | Sidecar policy | Script does not require the level time limit. | Debug solution setting. | Set `requiresWithinTimeLimit` true and replay. | Generator: Yes; editor warning |
| `solution_action_missing_tap_node_id` | Sidecar action | Action target is empty. | Malformed action. | Supply a valid switch ID. | Yes |
| `solution_action_unknown_tap_node` | Sidecar action | Action target is absent from graph. | Node renamed/deleted. | Update tap references or rerecord. | Yes |
| `tap_node_is_not_switchable` | Sidecar action | Target has fewer than two valid roads. | Tapping pass-through/terminal node. | Remove or retarget action. | Generator/Replay: Yes |
| `tap_node_has_too_many_outgoing_edges` | Sidecar action | Target is an unsupported high-arity switch. | More than four outgoing roads. | Split/reduce the switch. | Yes |
| `tap_node_switch_context` | Sidecar info | Reports the target's switch kind/options. | Normal validation context. | None. | No |
| `solution_action_invalid_time` | Sidecar action | Timestamp is not numeric. | Malformed JSON/editor input. | Use a finite numeric time. | Yes |
| `solution_action_negative_time` | Sidecar action | Timestamp is before time zero. | Bad recording/manual input. | Use zero or later. | Yes |
| `solution_action_after_time_limit` | Sidecar action | Required action occurs after timeout. | Stale timing/time-limit edit. | Reschedule or retune the level. | Yes |
| `solution_actions_not_sorted` | Sidecar action | Action order is not chronological. | Manual reorder. | Sort by nondecreasing timestamp. | Yes |
| `duplicate_solution_action_time` | Sidecar action | Adjacent actions share a timestamp. | Multiple taps authored simultaneously. | Space intentional taps beyond cooldown. | When error |
| `solution_action_spacing_too_small` | Difficulty/timing | Consecutive actions violate preset spacing. | Decisions are too compressed. | Increase route/window spacing. | Yes |
| `solution_first_tap_too_early` | Difficulty/timing | First tap violates start grace. | Immediate opening decision. | Move first decision later or adjust approach. | Yes |
| `repeated_switch_taps_too_close` | Difficulty/timing | Repeat taps on one switch are too close for preset. | High rotation count in short window. | Increase approach/window or reduce rotations. | Yes |
| `four_way_switch_requires_too_many_taps` | Difficulty/timing | One four-way choice needs excessive rotations. | Bad initial active edge/order. | Reorder initial roads or redesign choice. | Yes |
| `four_way_switch_taps_too_close` | Difficulty/timing | Four-way rotations are not comfortably spaced. | Short window/cooldown pressure. | Lengthen the window or reduce rotations. | Yes |
| `solution_tap_not_before_switch_arrival` | Runtime timing | Tap lacks required pre-arrival reaction buffer. | Action is at/near commitment. | Schedule earlier within the open window. | Yes |
| `solution_simulation_failed` | Runtime replay | Python replay threw, rejected a tap, or did not complete. | Any runtime/sidecar mismatch. | Inspect embedded failure reason and repair/rerecord. | Yes |
| `level_output_file_exists` | Output preflight | Target level file already exists and overwrite is disabled. | ID/path collision. | Choose a new ID/path or explicitly enable reviewed overwrite. | Yes |
| `solution_output_file_exists` | Output preflight | Target sidecar already exists and overwrite is disabled. | ID/path collision. | Choose a new ID/path or explicitly enable reviewed overwrite. | Yes |

## Recipe, topology, and unique-solution validation

All recipe-validation rows block that candidate before production.

| Code | Stage | Meaning | Typical cause | How to fix | Blocks production |
|---|---|---|---|---|---|
| `candidate_generation_error` | Candidate construction | Uncoded exception escaped topology/layout construction. | Invalid recipe, unsupported config, or implementation defect. | Read detail/trace; fix the originating stage and add a stable code if recurring. | Yes |
| `topology_rules_missing` | Recipe topology | Recipe has no explicit topology rules. | Old/incomplete family. | Add `RecipeTopologyRules`. | Yes |
| `required_path_empty` | Recipe topology | No intended route is declared. | Composer omitted path. | Supply a solved start-to-destination path. | Yes |
| `required_path_must_start_at_start` | Recipe topology | Intended path begins elsewhere. | Bad composition. | Begin at `start`. | Yes |
| `required_path_must_end_at_destination` | Recipe topology | Intended path ends before/after goal. | Bad composition. | End at destination ID. | Yes |
| `required_path_must_visit_package` | Recipe topology | Intended path omits package. | Incorrect route metadata. | Insert package on the required route. | Yes |
| `required_path_must_visit_package_before_destination` | Recipe topology | Path orders goal before package. | Incorrect route metadata. | Reorder/redesign package-first path. | Yes |
| `required_path_unknown_node` | Recipe topology | Path names an absent node. | Rename/composition bug. | Correct node ID. | Yes |
| `edge_unknown_from_node` / `edge_unknown_to_node` | Recipe topology | Recipe edge endpoint is absent. | Rename/composition bug. | Correct endpoint or add node. | Yes |
| `edge_unknown_availability` | Recipe topology | Recipe edge has unsupported phase. | Bad motif data. | Use a supported availability. | Yes |
| `conditional_road_dead_end` | Recipe topology | A node loses every road in a package phase. | Conditional-road composition bug. | Add a phase-usable road or change conditions. | Yes |
| `required_path_missing_edge` | Recipe topology | Consecutive required nodes lack an edge. | Path/edge list diverged. | Add edge or correct path. | Yes |
| `topology_rules_missing_for_cycle_validation` | Cycle validation | A cycle exists without rules to classify it. | Accidental/legacy loop. | Declare loop rules/metadata or remove cycle. | Yes |
| `undeclared_cycle` | Cycle validation | Graph cycle does not match allowed topology. | Accidental cycle or incomplete rules. | Remove it or declare the exact loop mechanic. | Yes |
| `topology_rules_missing_for_declared_loop_validation` | Loop validation | Loop validation cannot find rules. | Missing topology rules. | Add matching loop rules and metadata. | Yes |
| `declared_loop_count_exceeds_allowed` | Loop validation | Actual cycles exceed allowed count. | Composer created extra cycle. | Reduce cycles or intentionally update limits/evidence. | Yes |
| `declared_loop_allowed_count_must_be_positive` | Loop validation | Cycles are allowed with a nonpositive cap. | Inconsistent rule object. | Set a positive allowed count. | Yes |
| `declared_loop_ring_rule_without_ring_topology` | Loop validation | Ring flag conflicts with topology class. | Metadata drift. | Use ring topology or remove ring flag. | Yes |
| `declared_loop_topology_missing` | Loop validation | Cycles are allowed without a recognized loop form. | Vague rules. | Declare ring/return/revisit/loop topology. | Yes |
| `declared_loop_disconnected_from_required_route` | Loop validation | Declared cycle is unrelated to intended route. | Decorative unreachable loop. | Connect it meaningfully or remove it. | Yes |
| `declared_loop_topology_mismatch` | Loop validation | Concrete cycle does not match declared loop. | Stale metadata/composition. | Align graph and declaration. | Yes |
| `declared_loop_metadata_missing` | Loop metadata | Concrete rules allow cycles but report metadata is absent. | Builder did not serialize evidence. | Add synchronized `topologyRules` metadata. | Yes |
| `declared_loop_metadata_allows_cycles_mismatch` | Loop metadata | Metadata and rule Boolean disagree. | Duplicate sources drifted. | Make metadata mirror rules. | Yes |
| `declared_loop_metadata_allowed_cycle_count_mismatch` | Loop metadata | Metadata and rule cycle caps disagree. | Duplicate sources drifted. | Synchronize counts. | Yes |
| `declared_loop_metadata_topology_class_mismatch` | Loop metadata | Metadata topology class differs from recipe. | Stale tag. | Synchronize topology class. | Yes |
| `topology_rules_missing_for_declared_rejoin_validation` | Rejoin validation | Converging paths lack rules/metadata. | Undeclared rejoin. | Declare rejoin behavior and evidence. | Yes |
| `undeclared_rejoin` | Rejoin validation | Graph converges although rules disallow it. | Accidental convergence. | Remove or declare it. | Yes |
| `declared_rejoin_count_exceeds_metadata` | Rejoin validation | Actual rejoins exceed declaration. | Metadata drift/extra convergence. | Update intentional count or repair graph. | Yes |
| `declared_rejoin_node_metadata_mismatch` / `declared_rejoin_metadata_node_mismatch` | Rejoin validation | Declared rejoin nodes differ from detected nodes. | Renamed/changed topology. | Synchronize node list. | Yes |
| `declared_rejoin_metadata_missing` | Rejoin metadata | Rejoin exists without report metadata. | Builder omitted metadata. | Serialize synchronized rules. | Yes |
| `declared_rejoin_metadata_allows_rejoin_mismatch` | Rejoin metadata | Metadata and rule Boolean disagree. | Drift. | Synchronize metadata. | Yes |
| `declared_rejoin_package_bypass_detected` | Rejoin safety | Rejoin enables destination before package. | Unsafe convergence. | Gate/restructure the rejoin. | Yes |
| `declared_rejoin_multiple_solutions` | Rejoin safety | Rejoin creates multiple valid solutions. | Branches reconverge equivalently. | Make intended decisions consequential. | Yes |
| `declared_rejoin_shortcut_detected` | Rejoin safety | Rejoin bypasses intended path/taps. | Early convergence. | Lengthen/gate/restructure path. | Yes |
| `declared_rejoin_search_limit_reached` | Rejoin safety | Rejoin proof exhausted its search bound. | Large/cyclic state space. | Simplify topology or intentionally increase tested bound. | Yes |
| `topology_rules_missing_for_declared_revisit_validation` | Revisit validation | Repeated route node lacks rules/metadata. | Undeclared revisit. | Declare revisit behavior and evidence. | Yes |
| `undeclared_revisit` | Revisit validation | Required route repeats a node although disallowed. | Accidental path loop. | Remove or declare it. | Yes |
| `declared_revisit_count_exceeds_metadata` | Revisit validation | Actual revisit count exceeds declaration. | Metadata drift/extra loop. | Synchronize count or repair path. | Yes |
| `declared_revisit_node_metadata_mismatch` / `declared_revisit_metadata_node_mismatch` | Revisit validation | Declared repeated nodes differ from detected nodes. | Renamed/changed route. | Synchronize node list. | Yes |
| `declared_revisit_repeated_taps_not_allowed` | Revisit validation | Revisit requires repeated taps but metadata disallows them. | Inconsistent mechanic policy. | Allow intentionally and validate, or redesign. | Yes |
| `declared_revisit_metadata_missing` | Revisit metadata | Revisit exists without report metadata. | Builder omitted metadata. | Serialize synchronized rules. | Yes |
| `declared_revisit_metadata_allows_revisit_mismatch` | Revisit metadata | Metadata and rule Boolean disagree. | Drift. | Synchronize metadata. | Yes |
| `declared_revisit_package_bypass_detected` | Revisit safety | Revisit enables goal before package. | Unsafe loop state. | Gate/restructure package phases. | Yes |
| `declared_revisit_multiple_solutions` | Revisit safety | Revisit creates multiple valid solutions. | Equivalent loop states. | Make state/order consequential. | Yes |
| `declared_revisit_shortcut_detected` | Revisit safety | Revisit bypasses intended decisions. | Loop exit skips route. | Repair exit/availability. | Yes |
| `declared_revisit_infinite_traversal_risk` | Revisit safety | Search found a nonterminating revisit risk. | Loop can repeat without forced progress. | Add a state change/exit or remove loop. | Yes |
| `abstract_no_solution` | Topology solve | Abstract solver found no package-first completion. | Unsatisfiable choices. | Repair topology/initial switch states. | Yes |
| `abstract_destination_before_package` | Topology solve | Abstract routes reach goal before package. | Package bypass. | Gate or redirect pre-package routes. | Yes |
| `package_gate_metadata_not_enforceable` | Package proof | Gate metadata exists without a distinct enforceable package step. | Package equals goal or is optional. | Make package distinct and required. | Yes |
| `package_state_ambiguous` | Package proof | Intended-route metadata cannot prove package ordering. | Missing/repeated/ambiguous intended path. | Correct route metadata and graph. | Yes |
| `package_order_intended_route_invalid` | Package proof | Intended route has an invalid package order/status. | Package missing or after goal. | Correct required route. | Yes |
| `package_bypass_detected` | Package proof | Some structural path reaches goal before package. | Ungated shortcut. | Close/redesign bypass. | Yes |
| `shortcut_validation_missing_intended_route` | Shortcut proof | No intended path is available for comparison. | Missing solution route/solver metadata. | Persist intended route metadata. | Yes |
| `shortcut_path_detected` | Shortcut proof | Alternate path/tap order bypasses intended challenge. | Extra solution or shorter branch. | Make decisions/path unique. | Yes |
| `wrong_branch_dead_end_continues` | Wrong-branch proof | A branch declared/expected as dead end continues. | Misnamed or connected dead-end node. | Terminate it or reclassify mechanic. | Yes |
| `wrong_branch_reached_goal` | Wrong-branch proof | Off-route branch reaches destination. | Branch is not actually wrong. | Gate/terminate branch. | Yes |
| `wrong_branch_ambiguous_termination` | Wrong-branch proof | Branch hits search limits instead of clear failure. | Loop/long ambiguous branch. | Provide deterministic failure/return behavior. | Yes |
| `unique_solution_multiple_solutions` / `multiple_solutions_found` | Unique-solution proof | More than one accepted solution exists. | Equivalent choices/shortcut. | Make intended decisions necessary. | Yes |
| `unique_solution_not_found` / `no_valid_solution_found` | Unique-solution proof | No valid solution was found. | Unsolvable runtime/topology. | Repair and regenerate sidecar. | Yes |
| `unique_solution_search_limit_reached` / `unique_solution_not_proven` | Unique-solution proof | Bounded search could not prove uniqueness. | State space too large/cyclic. | Simplify or raise a reviewed bound with regression coverage. | Yes |

## Difficulty, timing, quality, parity, and selection

`<metric>_outside_difficulty_range` currently expands to
`node_count`, `switch_count`, `required_tap_count`, `dead_end_count`, or
`decision_count`.

| Code | Stage | Meaning | Typical cause | How to fix | Blocks production |
|---|---|---|---|---|---|
| `<metric>_outside_difficulty_range` | Difficulty fit | Measured count is outside preset range. | Candidate does not fit requested band. | Choose matching preset or redesign measured complexity. | Yes |
| `switch_too_many_outgoing_edges` | Difficulty fit | Switch exceeds the preset's allowed arity. | High-arity switch too early/easy. | Reduce arity or use a later preset. | Yes |
| `repeated_switch_taps_not_allowed` | Difficulty fit | Preset disallows repeated taps used by solution. | Revisit/high rotation in early band. | Redesign or use appropriate difficulty. | Yes |
| `decision_window_below_preset_minimum` | Difficulty fit | Smallest measured window is below preset minimum. | Short approach/look-ahead. | Lengthen window/approach. | Yes |
| `too_many_multiple_tap_windows` | Difficulty fit | Too many decisions require multiple taps in one window. | Excess high-arity rotations. | Reduce/reorder rotations. | Yes |
| `insufficient_strategic_decision_evidence` | Decision quality | Measured dependencies/revisits/phase changes are below preset. | Independent switch chain. | Compose consequential state/order interactions. | Yes |
| `independent_decision_ratio_above_preset_maximum` | Decision quality | Too many decisions are independent. | Choices can be preconfigured separately. | Add dependency, revisit, or package-state change. | Yes |
| `strategic_quality_rejected_before_layout` | Pre-layout quality | Recipe failed one or more strategic decision checks. | Weak decision profile. | Inspect detail codes and redesign motifs/topology. | Yes |
| `route_length_outside_difficulty_range` | Runtime difficulty | Simulated completion time is outside band. | Route too short/long. | Adjust geometry/topology or preset. | Yes |
| `quality_runtime_confidence_below_threshold` | Quality gate | Runtime solvability confidence is too low. | Failed/weak runtime evidence. | Repair replay and solver evidence. | Yes |
| `quality_switch_clarity_below_threshold` | Quality gate | Aggregate switch clarity is too low. | Ambiguous exits/arrows. | Repair ports, road shapes, and spacing. | Yes |
| `quality_similarity_above_threshold` | Quality gate | Candidate is too similar to comparisons. | Repeated topology/layout/solution. | Generate a different family/layout/decision pattern. | Yes |
| `quality_total_below_difficulty_threshold` | Quality gate | Weighted score is below requested-band minimum. | Several weak measured categories. | Use quality breakdown to improve weakest categories. | Yes |
| `large_portrait_without_puzzle_need` | Quality gate | Large canvas is not justified by route/interest. | Sparse oversized layout. | Use smaller profile or add meaningful structure. | Yes |
| `boring_topology_for_difficulty` | Quality gate | Hard/expert topology lacks strong route interest. | Simple independent chain. | Use dependency/revisit/gate/rejoin topology. | Yes |
| `route_interest_below_medium_gate` | Quality gate | Medium route-interest score is below minimum. | Too-straight/low-consequence route. | Add measured detour/dependency/failure contrast. | Yes |
| `route_interest_below_hard_gate` | Quality gate | Hard route-interest score is below minimum. | Insufficient strategic route structure. | Add stronger measured topology. | Yes |
| `route_interest_below_expert_gate` | Quality gate | Expert route-interest score is below minimum. | Insufficient expert interactions. | Add proven multi-phase/revisit/dependency behavior. | Yes |
| `candidate_too_similar_to_batch` | Candidate selection | Duplicate threshold matched another batch candidate. | Candidate pool lacks diversity. | Change seed/family/layout or pool breadth. | Yes |
| `candidate_too_similar_to_existing` | Candidate selection | Duplicate threshold matched production corpus. | Regenerated known puzzle. | Generate a more distinct candidate. | Yes |
| `same_topology_and_solution` | Similarity diagnostic | Topology and solution signatures are equal. | Structural duplicate. | Vary decision graph/solution. | When used as rejection |
| `same_topology_and_layout` | Similarity diagnostic | Topology and layout signatures are equal. | Visual/structural duplicate. | Vary topology or layout. | When used as rejection |
| `similarity_threshold` | Similarity diagnostic | Weighted similarity crossed configured threshold. | Multiple signature dimensions match. | Inspect similarity breakdown and diversify. | When used as rejection |
| `not_selected` | Portfolio selection | Valid candidate lost deterministic portfolio ranking. | Another candidate fit batch better. | None unless tuning selection. | No |
| `candidate_selection_filtered` | Candidate selection | Candidate was excluded by a selection filter. | Similarity/pacing policy. | Inspect filter detail and diversify. | Yes for that candidate |
| `candidate_selected` | Portfolio selection | Candidate won its level slot. | Highest deterministic portfolio objective. | None. | No |
| `missing_required_swift_validation` | Runtime parity | Risky candidate lacks mandatory Swift run. | Production generation omitted `--swift-tests`. | Rerun with Swift tests. | Yes |
| `switch_tap_runtime_mismatch` | Runtime parity | Swift rejected/handled taps differently. | Timing, eligibility, cooldown, or target mismatch. | Compare traces and fix both implementations/sidecar. | Yes |
| `package_order_runtime_mismatch` | Runtime parity | Swift package/goal order differs from expectation. | Availability/event-order mismatch. | Repair parity or topology. | Yes |
| `solution_sidecar_runtime_mismatch` | Runtime parity | Swift replay does not complete as sidecar declares. | Runtime divergence or stale solution. | Rerecord after parity repair. | Yes |
| `swift_runtime_parity_failed` | Runtime parity | Swift gate failed without a narrower reason. | XCTest/build/runtime failure. | Inspect Swift failure details and rerun. | Yes |
| `swift_tests_passed` | Runtime parity status | Requested Swift checks passed. | Successful gate. | None. | No |

## Layout, road geometry, and visual clarity

Generator layout errors block production. Rows marked “When error” are often
warnings in editor/live analysis, but can become hard errors in generator
readability or geometry gates.

| Code | Stage | Meaning | Typical cause | How to fix | Blocks production |
|---|---|---|---|---|---|
| `overlapping_nodes` / `layout_node_cluster` / `node_spacing_failure` | Layout | Nodes violate minimum spacing. | Dense placement/repair failure. | Move nodes apart or enlarge profile. | When error |
| `implicit_road_intersection` | Editor layout | Orthogonal roads cross without a node. | Road-shape/placement collision. | Add a real node or reroute. | No (warning) |
| `implicit_intersection_without_node` / `implicit_intersection_without_graph_node` | Layout topology | Roads intersect visually without graph connectivity. | Placement/shape collision. | Add a connected node or reroute. | Yes |
| `layout_node_out_of_bounds` | Layout bounds | Node is outside preset bounds. | Placement/repair escaped canvas. | Move inside bounds. | Yes |
| `layout_layer_missing_endpoint` | Layout planning | Layer assignment cannot find start or destination. | Invalid recipe roles. | Restore valid endpoints before layout. | Yes |
| `layout_node_too_close_to_edge` | Layout bounds | Ordinary node is too close to board edge. | Tight placement. | Move inward/enlarge profile. | Yes |
| `layout_switch_too_close_to_edge` | Layout bounds | Switch/tap target is too close to board edge. | Tight placement. | Move inward. | Yes |
| `layout_dead_end_not_readable` | Layout readability | Dead end lacks clear branch separation. | Dead end too close/aligned with parent. | Move it to read as a branch. | Yes |
| `layout_important_nodes_too_close` / `important_nodes_too_close` | Layout readability | Start/package/destination spacing is insufficient. | Important markers clustered. | Separate them. | Yes |
| `layout_package_destination_confusing` | Layout readability | Package and goal read as one area. | Markers too close. | Separate package and destination. | Yes |
| `layout_too_many_edge_crossings` | Layout readability | Crossing count exceeds preset hard limit. | Tangled layout. | Reorder layers/ports or reroute. | Yes |
| `layout_too_many_tight_edge_spacing_issues` | Layout readability | Too many roads run too close together. | Dense parallel geometry. | Increase spacing/change shapes. | Yes |
| `road_proximity_failure` | Layout readability | Nonadjacent roads violate clearance. | Dense road placement. | Reroute or move nodes. | Yes |
| `switch_exit_overlap` | Layout readability | Roads leaving one switch overlap. | Same initial segment/port. | Assign distinct ports/shapes. | Yes |
| `important_node_visibility_failure` | Layout readability | Road geometry obscures an important node. | Road passes too close. | Move marker/road. | Yes |
| `start_goal_separation_failure` | Layout readability | Start and goal do not have sufficient separation. | Compressed route. | Separate them. | Yes |
| `portrait_safety_failure` | Portrait layout | Layout violates a portrait/mobile-safe rule. | Bad bounds, margins, aspect, or vertical flow. | Use portrait planner guidance and repair. | Yes |
| `portrait_layout_has_no_height` | Portrait layout | Vertical span is zero. | All nodes share a row. | Add vertical separation. | Yes |
| `portrait_layout_too_wide` | Portrait layout | Width/aspect exceeds portrait profile. | Horizontal layout in portrait slot. | Reorient/compress width. | Yes |
| `portrait_start_not_lower` | Portrait layout | Start is not below route progression. | Reversed vertical flow. | Place start lower. | Yes |
| `portrait_destination_not_upper` | Portrait layout | Destination is not above route progression. | Reversed vertical flow. | Place destination higher. | Yes |
| `portrait_start_destination_not_vertically_separated` | Portrait layout | Start/goal vertical gap is insufficient. | Flat layout. | Increase vertical separation. | Yes |
| `zero_length_edge` | Road geometry | Road endpoints have identical coordinates. | Overlapping endpoint nodes. | Separate endpoints or remove road. | Yes |
| `unreadable_road_geometry` | Road geometry | Aggregate road-shape score is below threshold. | Multiple geometry issues. | Inspect issue list and replan shapes/layout. | Yes |
| `ambiguous_switch_exit` / `switch_choice_visual_direction_ambiguous` | Switch clarity | Exit has no unique readable direction. | Bend/short segment hides choice. | Move target or change road shape/port. | Yes |
| `conflicting_direction_bucket` / `switch_choices_same_visual_direction` | Switch clarity | Multiple choices occupy one visual direction. | Same first-segment direction. | Assign distinct first segments. | Yes |
| `insufficient_exit_separation` | Switch clarity | Exit angles are too close. | Targets/ports clustered. | Spread exits. | Yes |
| `ambiguous_active_edge_arrow` | Switch clarity | Initial active arrow is not uniquely readable. | Active road overlaps/duplicates direction. | Reorder to a clear initial road and repair geometry. | Yes |
| `active_edge_visually_hidden_under_another_road` | Switch clarity | Active road visually merges with another road. | Overlapping/parallel segment. | Reroute or change shape. | No (warning) |
| `four_way_switch_short_outgoing_edge` | Four-way clarity | Four-way exit is too short. | Target too near switch. | Lengthen exit. | No (warning) |
| `four_way_switch_ambiguous_angles` | Four-way clarity | Four-way exits have near-equal angles. | Targets clustered. | Spread toward distinct directions. | No (warning) |
| `four_way_switch_missing_clear_cardinal_options` | Four-way clarity | Four-way choice lacks four readable directional options. | Poor port assignment. | Reassign positions/ports. | Yes |
| `four_way_switch_missing_cardinal_exits` | Road-shape planning | Four-way first segments do not cover north/east/south/west buckets. | Poor shape/port assignment. | Reassign positions, ports, or road shapes. | When error |
| `switch_too_close_to_another_switch` | Mobile clarity | Switches are visually crowded. | Dense tap targets. | Increase spacing. | When error |
| `switch_tap_targets_too_close` | Mobile clarity | Touch targets are too close on phone scale. | Dense switches. | Increase spacing. | Yes |
| `road_crosses_through_unconnected_node` | Visual topology | Road passes through unrelated node. | Orthogonal segment collision. | Connect at node or reroute. | Yes |
| `unconnected_parallel_road_overlap` | Visual topology | Unconnected roads overlap collinearly. | Duplicate corridor geometry. | Separate/connect/reroute. | Yes |
| `unconnected_road_endpoint_touches_segment` | Visual topology | Endpoint touches unrelated road. | Accidental T-junction. | Add junction or move endpoint. | Yes |
| `route_crossing_near_switch` | Route clarity | Crossing competes with a switch. | Crossing placed near choice. | Move crossing/switch. | No (warning) |
| `wrong_route_crosses_required_route_near_switch` | Route clarity | Wrong and required roads cross near a choice. | Confusing false branch geometry. | Separate routes near switch. | No (warning) |
| `route_crossing_near_important_node` | Route clarity | Crossing obscures start/package/goal. | Crossing too near marker. | Move crossing. | Yes |
| `road_crossing_near_important_node` | Road-shape planning | One or more planned crossings are close to an important node. | Shape assignment routes through a marker area. | Change shapes or move nodes. | When error |
| `required_path_crossing` | Road-shape planning | A crossing involves the intended route. | Main route geometry intersects another road. | Replan shapes/layers. | No (warning) |
| `required_path_crosses_itself_too_much` | Route clarity | Intended route has excessive self-crossings. | Tangled layout. | Replan layers/shapes. | Yes |
| `required_path_self_crossing` | Route clarity | Intended route crosses itself. | Route geometry loops visually. | Simplify if not intentional. | No (warning) |
| `route_has_many_decorative_crossings` | Route clarity | Many non-required crossings add noise. | Decorative roads tangled. | Reduce/reroute extras. | No (warning) |
| `route_has_decorative_crossings` | Route clarity | At least one decorative crossing exists. | Extra route geometry. | Review; remove if confusing. | No (info) |
| `overlapping_first_segments_from_same_switch` | Road geometry | Two exits initially share geometry. | Same port/shape. | Assign different ports/shapes. | Yes |
| `same_switch_first_segments_overlap` | Road-shape planning | Two exits from one switch share their first segment. | Same direction bucket and shape. | Assign distinct ports/shapes. | Yes |
| `required_and_wrong_route_first_segments_overlap` | Road-shape planning | Required and false exits initially overlap. | Ambiguous switch geometry. | Separate their first segments. | Yes |
| `long_parallel_road_segments_visually_merge` | Road geometry | Separate roads can read as one. | Long close parallel segments. | Increase gap or change shape. | No (warning) |
| `long_parallel_road_segments` | Road-shape planning | Planner counted long close parallel segments. | Dense shape assignment. | Increase gap or change shapes. | No (warning) |
| `nodes_too_close` | Visual spacing | Noncritical nodes are crowded. | Dense layout. | Move apart. | No (warning) |
| `important_node_readability_blocked_by_road` | Mobile clarity | Unrelated road crowds an important marker. | Segment too close. | Move road/marker. | Yes |
| `road_segment_too_close_to_important_node` | Road-shape planning | Planned segment violates important-node clearance. | Shape passes near start/package/goal. | Change shape or move marker. | No (warning) |
| `important_nodes_tight_on_small_device` | Mobile clarity | Switch and important marker are tight at phone scale. | Dense placement. | Increase spacing. | No (warning) |
| `arrow_icon_may_collide_with_node_label_or_package` | Mobile clarity | Arrow artwork may overlap marker/label. | Arrow anchor too close. | Change shape/spacing. | No (warning) |
| `dead_end_looks_like_main_route` | Route flow | Wrong branch visually dominates. | Dead end is straighter/longer than intended road. | De-emphasize/move dead end. | When error |
| `return_loop_visually_unclear` | Route flow | Return loop does not read as a return. | Shape/layout hides loop. | Strengthen separated loop geometry. | When error |
| `package_off_visual_flow_without_intent` | Route flow | Package appears detached without mechanic justification. | Marker far from intended visual route. | Reposition or add measured detour intent. | When error |
| `return_loop_false_shortcut` | Route flow | Loop geometry implies an unavailable shortcut. | Segments visually touch/align. | Separate loop and shortcut-looking roads. | Yes |
| `road_visually_circles_back_on_itself` | Road geometry | One road shape folds back confusingly. | Orthogonal bend/positions create reversal. | Change road shape or endpoints. | Yes |
| `revisited_switch_corridor_too_tight` | Road geometry | Revisit approach/return corridors are too close. | Loop compressed around switch. | Widen loop. | Yes |
| `return_path_too_close_to_destination_branch` | Road geometry | Return road can be mistaken for goal branch. | Parallel/nearby corridors. | Separate return and destination paths. | Yes |
| `non_adjacent_roads_too_close` | Road geometry | Unrelated roads violate minimum clearance. | Dense geometry. | Move nodes/change shapes. | Yes |
| `solution_tap_cycles_to_visually_confusing_edge` | Switch clarity | Verified tap selects an ambiguous road. | Road order points solution at unclear exit. | Repair geometry/order, then regenerate solution. | Yes |

## Maintenance rule

Whenever code adds, renames, or removes a machine-readable validation,
simulation, parity, or candidate-rejection code, update this file in the same
change. Reuse an existing code only when stage, meaning, production severity,
and remediation are genuinely the same.
