# TinyRoutes — Future Roadmap V3 (stub)

**Idea collection · 2026-11-11 · Not approved; nothing here is scheduled**

V3 is where **biome-specific mechanics** live: biomes that bring their own new challenge, not just a new look. It follows [Roadmap V2](multi_van_future_roadmap_v2.md), which already treats chapters as visual biomes with no new rules (§8, "Biomes as chapter themes").

## Implementation status (2026-11-12)

Two candidates are prototyped, each as one internal board with a matching control board, as "Before any V3 work starts" asks. They were picked because they reuse systems V2 now has. The owner confirmed both on 2026-11-12; neither has been playtested.

| Candidate | Boards | Reuses | Rule as built |
|---|---|---|---|
| Harbor drawbridge | `experiment_drawbridge_a` (Bridge Up), `experiment_drawbridge_c` (Bridge Down) | The V2 signal: one group on a fixed tick schedule. | A van waits at the stop line while the bridge is up, then crosses. |
| Snowy village ice | `experiment_ice_a` (Slippery Corner), `experiment_ice_c` (Clear Road) | Live-switch locks. | The live switch at the end of an icy road stays locked from the moment a van drives onto the ice. |

The other six candidates are untouched. Tests are in [MultiVanSignalTests.swift](TinyRoutesTests/Prototype/MultiVanSignalTests.swift).

## Why this waits for V2

- V2's principle is "rules stay small; relationships deepen." One new mechanic per biome would stack rules chapter after chapter, which is the steep, almost-unsolvable difficulty playtesters warned against.
- Several of these ideas are things V2 deliberately deferred (§14): van speed differences, dynamic closures, and timed hazards.
- V2's experiments tell us what V3 can safely build on: package pickups (§4–5), pause / inspect / resume (§6), the single traffic-light trial (§7), and escalating hints (§3). A biome mechanic that reuses a proven system is much cheaper and safer than a new one.

## Rules for any biome mechanic

1. **At most one new rule per biome**, introduced on a calm board, and then combined only with rules players already know.
2. **Reuse a proven V2 system where possible.** Say which one it extends.
3. **Visible and predictable.** The player can read the mechanic's state before pressing Go, and the preview reflects it. No hidden randomness.
4. **No timing pressure on the required path** unless V2's deliberate-play controls have made it usable (V2 §6).
5. **Assistance works there too.** Hints and nudges (V2 §3) must be able to explain the mechanic.
6. **Can be dropped.** If a mechanic fails its trial, the biome ships as a visual theme with existing rules.

## Candidate biomes and mechanics

All candidates; none are designed, validated or approved.

| Biome | Possible mechanic | Builds on | Main risks |
|---|---|---|---|
| Harbor / canal | **Drawbridge** that raises and lowers on a fixed, visible cycle. | Traffic-light timing (V2 §7). | Waiting downtime; needs pause controls for fairness. |
| Island / lake | **Ferry**: a van waits at a dock and is carried across. | Signal-style holding; committed edges. | New vehicle-on-vehicle state; collision rules at docks. |
| Snowy village | **Slippery corner**: a van can't stop or switch on an icy stretch, so switch choices must be set before it arrives. | Existing live-switch locks. | Must be clearly shown; can feel unfair if not previewed. |
| Countryside / farm | **Gate** a van opens once as it passes, changing a route for later vans. | Dynamic closures (V2 §14, deferred). | Needs a real per-traversal edge state, which isn't implemented. |
| Construction district | **Roadworks** that close one road after a set number of passes. | Same as gates. | Same as gates; plus counting burden. |
| Mountain / hill town | **Steep road** where vans travel slower uphill. | Van speed differences (V2 §14, deferred). | Changes every timing margin and live-switch window. |
| Night town | **Lit lanterns**: only lit roads are shown in the preview until a van passes nearby. | Preview scope rules (V2 principle 9). | Conflicts with "the plan belongs to the player"; probably reject unless it stays fully plannable. |
| Market / festival | **Busy street** with a one-van-at-a-time zone. | Single signal group, occupancy (V2 §7). | Queue behavior, which V2 rules out. |

## Rewards

Biomes and their mechanics are campaign content, never shop items. Finishing a biome can grant a themed cosmetic from the V2 reward catalog (V2 §9, "Rewards and coin unlocks").

## Before any V3 work starts

- V2's cargo and deliberate-play experiments have a keep/drop decision.
- Biome theming (V2 §8) exists for at least two chapters, so V3 is adding rules to a working presentation layer.
- The owner picks one or two candidates to prototype, each as a single internal board with a matching control board, in the style of V2's A/B/C experiment.
