# Recipe Topology Rules

`RecipeTopologyRules` is metadata attached to recipe-first generation variants. It declares which graph structures a recipe is allowed to produce before later Generator V2 validation work inspects the graph itself.

The current fields are:

- `allowsCycles`
- `allowsRejoin`
- `allowsRevisit`
- `allowsReturnPath`
- `allowsRing`
- `allowedCycleCount`
- `requiresPackageGate`
- `requiresUniqueSolution`
- `requiresSwiftRuntimeValidation`

These rules now drive abstract graph cycle validation. They make recipe intent explicit so validators can reject graph structures that appear accidentally before layout, solving, scoring, or runtime validation.

## Declared vs. Accidental Cycles

A declared cycle is part of the selected recipe's intended mechanic, such as a return path that revisits a switch or a ring route with a deliberate loop. It must be allowed by the recipe's `RecipeTopologyRules` and mirrored in the recipe mechanic metadata under `topologyRules`.

An accidental cycle is any loop-like graph structure created by a recipe that did not declare permission for it. Generator V2 treats these differently: declared cycles can continue to later solver and readability validation, while accidental cycles are rejected by topology validation.

Unknown or partially migrated recipes are not treated as cycle-safe. If a graph contains a directed cycle and no `RecipeTopologyRules` are attached, validation fails instead of inferring that the cycle is acceptable from a recipe name.

Phase 2 validation replaces the old blanket "all cycles are bad" rule with two graph recipe checks:

- `validateNoUndeclaredCycles()` detects directed cycles in the abstract recipe graph. If `allowsCycles` is false, every cycle is rejected. If `allowsCycles` is true, each cycle must match the recipe's declared topology.
- `validateDeclaredLoops()` validates the declared loop layer. It checks the detected cycle count against `allowedCycleCount`, verifies that ring/return/revisit permissions match the recipe topology metadata, requires each loop to touch the intended route, and checks basic metadata consistency.

This phase does not prove that a declared loop preserves a unique solution, avoids all shortcuts, prevents every package bypass, handles route rejoin edge cases, guarantees readable layout, or matches Swift runtime behavior. Those checks belong to later solver, readability, and runtime validation phases. Phase 2 only establishes the topology-rule-driven gate that decides whether a cycle is allowed to proceed.

## Topology-Rule-Driven Validation

Cycle validation uses the `RecipeTopologyRules` attached to the `GraphRecipe`:

- Recipes with `allowsCycles == false` keep the existing strict behavior: any directed cycle fails validation.
- Recipes with `allowsCycles == true` may contain cycles only when the recipe also declares an intended loop topology, such as a return path/revisit or a ring.
- Recipes with `allowsCycles == true` must include `mechanicMetadata.topologyRules`; missing loop metadata is a validation error even before deeper solver validation runs.
- Return/revisit loops are expected to be declared by return/revisit topology metadata and touch the intended route.
- Ring loops are expected to be declared by ring topology metadata.
- Loops that are disconnected from the required route are rejected as accidental topology.
- Recipe mechanic metadata must agree with the attached topology rules for cycle permission and allowed cycle count.

Cycle validation errors include a context suffix with the recipe family/variant, `allowsCycles`, `allowedCycleCount`, actual detected cycle count, and the declared cycle count from metadata when available. This is intentional: Phase 2 errors should point at the incorrect recipe declaration, not just the first edge in the graph.

## Current Declarations

Recipes that currently allow cycles/revisits/return paths:

- `return_loop`
- `return_loop_with_gate`
- `multi_switch_revisit`
- `package_inside_loop`
- `four_way_intro`
- `controlled_repeated_taps`
- `late_route_reversal`

Recipes that currently allow rings:

- `ring_route`
- `four_way_ring`

Recipes that currently allow rejoins without cycles:

- `split_path_rejoin`
- `hub_choice`
- `long_detour_gate`
- `two_phase_route`
- `four_way_package_gate`
- `multi_four_way_route`

## Known Name/Topology Mismatches

Some recipe names describe future or intended mechanics more strongly than the current graph builder actually creates:

- `return_loop_intro` currently delegates to a two-switch linear route, so it does not declare cycles, revisits, or return paths yet.
- `ring_route_gate` currently delegates to a three-switch linear chain, so it does not declare ring or cycle permissions yet.
- `branch_then_rejoin_with_wrong_order` currently has a node named `rejoin`, but the graph does not create a true split/rejoin with multiple incoming paths.

These mismatches are documented instead of granting permissions the current implementation does not actually support.
