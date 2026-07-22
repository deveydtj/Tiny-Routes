# Production V3 Quality Gates

Quality is fail-closed. Hard strategic, runtime, and readability requirements
run before weighted ranking, so presentation cannot compensate for a trivial or
unproved puzzle.

## Protected hard gates

The checked-in quality profile requires at least two meaningful decisions, one
planning decision, one adaptive decision after a state change, no equivalent
choice counted as difficulty, no successful static routing policy, and a proven
unique optimum. Difficulty targets add objective count, dependency depth,
revisit, recovery, agent-separation, timing-window, rapid-tap, visibility, and
layout requirements.

Candidates also fail when strategy search is uncertain, a tap is illegal,
jitter replay fails, a state change is not visible before a required choice, a
road condition is hidden/unsafe, or any objective-state layout is unreadable.
Stable rejection codes identify the responsible stage.

## Ranking and portfolio selection

Candidates that pass all hard gates are ranked using profile weights for agent
separation, planning depth, recovery balance, route diversity, runtime comfort,
and visual readability. Portfolio selection then enforces campaign difficulty,
archetype/mechanic diversity, behavior uniqueness, and separation from shipped
content. It selects the complete batch as one portfolio; it never lowers a hard
threshold to fill a slot.

## Updating quality profiles

Profiles live in `config/quality_profiles` and use semantic versions. A tuning
change must:

1. create a higher version rather than editing historical evidence in place;
2. retain or strengthen every protected invariant;
3. reference new blinded-playtest evidence;
4. reference a new fixed-seed comparison;
5. update expected archetype frequencies and difficulty targets together;
6. pass fixed seeds, positive/adversarial suites, production smoke, nightly
   campaign, and the final release wrapper.

Normal generation does not wait for human review. Blinded playtests calibrate a
profile during release QA; they are not per-candidate approval.
