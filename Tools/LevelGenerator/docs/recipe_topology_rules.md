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

These rules do not change generation behavior yet. They make recipe intent explicit so later validators can reject graph structures that appear accidentally.

## Declared vs. Accidental Cycles

A declared cycle is part of the selected recipe's intended mechanic, such as a return path that revisits a switch or a ring route with a deliberate loop. An accidental cycle is any loop-like graph structure created by a recipe that did not declare permission for it. Generator V2 should treat those differently: declared cycles can continue to later solver and readability validation, while accidental cycles should be rejected once topology validation is implemented.

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
