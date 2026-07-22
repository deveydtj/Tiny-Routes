# Transactional Generation

Production generation has an all-or-nothing contract: it promotes the full
requested campaign or leaves every production level, solution, manifest, and
project resource unchanged.

## Workspace lifecycle

`ProductionStagingService` creates one run workspace with restrictive ownership
metadata, a configuration/seed snapshot, and a run manifest. Selected levels,
solutions, the rebuilt production manifest, reports, hashes, and reproduction
bundle are written there. Production paths are not touched during candidate
search or staged validation.

The staged-corpus validator verifies artifact hashes, schema and graph rules,
solution replay, candidate proof linkage, corpus/manifest synchronization, and
required Swift parity against the staged directories. A failed validation marks
the run `failed_no_changes` and retains diagnostic evidence.

## Promotion and rollback

Promotion acquires the exclusive generation lock, rechecks target collisions,
backs up every overwritten target, installs staged files with same-filesystem
replacement, updates resources, and runs a lightweight final validation. The
lock includes an ownership token so a process cannot remove another run's lock.

Any write, resource-update, validation, or interruption failure restores all
overwritten files, removes newly introduced targets and temporary artifacts,
records `rolled_back`, and releases only the lock owned by that run. A target
that appeared after preflight fails before production writes begin.

## Operation and recovery

- A successful terminal status is `promoted` with the complete requested count.
- `failed_no_changes` means promotion never changed production.
- `rolled_back` means promotion began and the original snapshot was restored.
- Lock contention is actionable; inspect the recorded owner before removing a
  demonstrably stale lock. Never delete a live lock to force a second run.
- Re-run a failure from its retained `reproduce.sh` in an isolated output tree.
  Reproduction must not target production directories.

Run the dedicated failure suite with:

```bash
python -m pytest Tools/LevelGenerator/tests/test_transactional_generation.py
```

The final release wrapper includes this suite through `--transaction-tests`.
