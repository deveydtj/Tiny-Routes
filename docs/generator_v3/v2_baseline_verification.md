# V2 Baseline Verification

**Verification date:** 2026-07-17

**Verification target:** `ebe09a6978b79bc20652de1c3d2569dd6e566183` (`main`, clean before verification)

**V3 audit reference:** `54c6516f64781ac3a259a8715605d27673005035`

**Overall result:** **FAIL — V3 implementation remains blocked on baseline repair**

This report records the first execution of the V3 Phase 0 release-equivalent
baseline. It does not replace `scripts/run_all_checks.py`, relax a gate, or
reinterpret a failed command as a pass.

## Configuration

- Host: Apple Silicon (`arm64`), macOS 26.5.2 (25F84).
- Supported Python used for the auditable run: CPython 3.11.13 with pytest
  9.1.1 and `tiny-routes-core` 0.1.0.
- Swift toolchain available locally: Xcode 26.5 (17F42).
- Simulator destination: `platform=iOS Simulator,name=iPhone 16 Pro,OS=18.5`.
- Production writes: none. The smoke and fixed-seed suites ran in dry-run or
  report-only modes.

The documented wrapper was invoked with its supported interpreter override so
that the repository's installed Python 3.11 dependencies were used:

```bash
python3 scripts/run_all_checks.py \
  --python /opt/homebrew/bin/python3.11 \
  --swift-tests \
  --destination 'platform=iOS Simulator,name=iPhone 16 Pro,OS=18.5' \
  --reports-dir /tmp/tiny-routes-v2-baseline
```

An initial invocation without `--python` selected Homebrew Python 3.14.5,
which did not have pytest or the editable shared core installed. That
environment-only failure is not counted as the repository result. The Python
3.11 rerun confirmed the repository failures below.

## Gate results

| Gate | Result | Evidence |
| --- | --- | --- |
| Shared Python core | PASS | 41 passed |
| Level Generator Python suite | FAIL | 61 failed, 362 passed, 3 skipped |
| Level Editor Python suite | PASS | 320 passed |
| Deterministic generator smoke | PASS | Two easy levels accepted in dry-run mode |
| Fixed-seed regressions | PASS | 9/9 suites; 46/46 requested levels accepted |
| Production corpus, non-Swift | PASS | 27/27 levels; corpus, manifest, sidecars, Python replay, and visual gates passed |
| Swift Xcode suite | FAIL | 429 tests executed, 1 skipped, 120 assertion failures in `LevelRepositoryTests.testBundledLevelsHaveReplayableRouteEngineSolutions()` |
| Release wrapper | FAIL | Correct nonzero exit because required sub-gates failed |

The generator failures cluster around strict recipe topology/readability
validation versus older recipe/template acceptance tests. The Swift failures
cluster in the bundled-level RouteEngine replay test. Those are baseline
repair inputs, not V3 behavior changes, and must be fixed and committed
separately before Phase 0 can exit.

## Deterministic fixed-seed outputs

| Suite | Seed | Accepted | SHA-256 output hash |
| --- | ---: | ---: | --- |
| tutorial | 1803001 | 2/2 | `be5c3e1021750393ab27f2b37d7e6c75b9a1374affb28537d712f23e583f1d19` |
| easy | 1803002 | 2/2 | `d8f1ed8b978214eb783ab45ee3d8d5adb45b7da9bd9a3892a8a2db307532a5cf` |
| medium | 1803003 | 2/2 | `c0e6396258fe6a8f168ea18cb614f08326fda3084f4dbb96af231b03a6a306f5` |
| hard | 1803004 | 2/2 | `45d159b88800dd880a121c8839f292029f3f7df50699ebaa8ed21a92b3445bd5` |
| expert | 1803005 | 2/2 | `3903000f869bfec2ad0342703cf0d116bc3a250b3de1fc47becc80a21e93dc35` |
| mixed 30-level campaign | 1803030 | 30/30 | `eb6a2e6620f39755d20b640c58b4c9e46b3255d9379292a4962bd264b122fc36` |
| revisit-heavy | 1803041 | 2/2 | `5896674f6ff0423ea3dd41c19bc7916299ed99cf4bf374336d80fa07cc94d19c` |
| three-/four-way switches | 1803042 | 2/2 | `d9e17bec2e228e06b040e6eba274ee9f333d0bca81bcbf0fe07bb4a5094815a9` |
| conditional roads | 1803043 | 2/2 | `b4706353fd2e1c547e80aee126277bc1bc1d3900dadc55b166d52e50db9d0c9e` |

Retained report hashes from the configured run:

- `fixed_seed_regressions.json`:
  `d22ae356a6b99472d491d6c2a336387609e59d11fa5e94ba864e47877e099350`
- `production_corpus_verification.json`:
  `4c931f60b29d71156ffdfeef550877dc76d9ca9e543d417b69f3bd6d96b84ed3`
- `production_corpus_verification.md`:
  `aa8cb1ac8a02fc1f1050a591863f4141cabfc102347e4276aad555414a9ee6d1`

The machine-readable companion report contains the same configuration,
counts, output hashes, and failure classification.
