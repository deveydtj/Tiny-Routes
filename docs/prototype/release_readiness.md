# MV-48 — Multi-Van release readiness

## External TestFlight upload — 2026-11-06

The owner requested distribution of the current working tree to the existing
**Family and friends** external group. Added `Build External TestFlight.command`
and its fastlane lane, using the production `TinyRoutes` / `Release` scheme.
The lane authenticates, verifies the exact external group, allocates a build
number, checks packaged resources, uploads, waits for processing, submits beta
review and enables tester notifications. Its IPA retry pins the exact version
and build and skips re-upload. The offline submission checks passed.

The shared packaging verifier now compares bundled levels against the source
directory instead of the obsolete twelve-level list. A fresh signed Release
archive passed verification with **14 levels**, ten CAFs, thirteen sprites,
confetti, asset catalog and privacy manifest, with no bundled solutions or tests.

Fastlane had no configured Apple ID/session or API key, so automatic group
submission stopped before making changes. Using Xcode's existing credentials,
uploaded that verified archive with `testFlightInternalTestingOnly=false` and
Xcode-managed build numbering. Xcode reported **Upload succeeded** and
**EXPORT SUCCEEDED** at 06:47 local time. Content Delivery metadata identifies
the uploaded version as **1.0 (7)**. Apple processing, external group
assignment, beta review submission/approval, notification and installation are
**not verified**. Group submission remains pending an App Store Connect action
on the owner's iPhone or the first fastlane sign-in.

Archive, export options and build/upload log:
`.local/testflight/external-current/` (ignored). The following sections are
historical evidence and do not describe the current app navigation or level count.

## TestFlight upload follow-up — 2026-11-03

The owner authorized uploading Tiny Routes to TestFlight. Added the root
`Build TestFlight.command`, adapted from Node's double-click uploader for native
Xcode archiving, existing bundle verification, and internal-only TestFlight upload.
The signed archive and resource verification passed. After the owner signed into
Xcode, App Store Connect reported no app record for `com.tinyroutes.app`.
Xcode Organizer's attempt to create that record also failed
(`IDEDistribution.DistributionAppRecordProviderError`, missing app).
After browser sign-in, the Tiny Routes app record was present (Apple ID
`6829948652`). Retried export/upload of the verified signed archive: Xcode reported
`Upload succeeded`, `Uploaded MultiVanInternal`, and `EXPORT SUCCEEDED` (exit 0).
Apple processed version **1.0 (1)**. Answered the encryption question with
**None of the algorithms mentioned above**, after checking that the app source
contains no custom encryption or networking implementation. App Store Connect
then showed **Ready to Test**. Created the **Internal Testing** group with
automatic distribution disabled, added the owner's existing account as its sole
tester, and assigned build 1 to it. Device installation and human playtest
acceptance remain unverified.
Signed candidate and logs: `.local/testflight/20261102-165408/` (ignored).
The successful retry is recorded in `upload-success.log` in that directory.

The preparation checklist below records the earlier state; its unsigned-only
archive and missing-upload-authorization entries are superseded by this follow-up.

## Earlier engineering preparation

2026-11-02 · **Engineering preparation complete — awaiting human acceptance and authorized distribution.**
No build was uploaded, submitted, distributed or installed through TestFlight.
No human playtest or team approval is claimed. MV-48's original completion
condition (someone outside the team installs from TestFlight and reaches Level 1)
remains open. Requirements: [MV-48](multi_van_tasks.md#mv-48--testflight-build),
[source plan](multi_van_prototype_plan.md), [playtest kit](playtest_kit.md),
[unchanged tuning baseline](mv46_tuning_assessment.md).

## Build and access

Use the shared **MultiVanInternal** scheme and **InternalTestFlight** configuration.
This is a Release configuration (`-O`, whole-module compilation, no `DEBUG`),
with `MULTIVAN_INTERNAL` defined only for the app in that configuration. It uses
the plan's settings-toggle entry, without archiving a Debug build.

In the internal build: **Settings → About → Multi-Van Prototype** (initially off),
then return Home → **Prototype**. The list exposes Levels 1–12 and **Playtest log**.
Ordinary Release compiles neither the toggle nor the prototype entry/session UI;
even a retained enabled preference cannot reveal them. Debug retains its existing
button and tuning panel. The flag is a build boundary, not tester authentication:
the owner must restrict the uploaded build's TestFlight access and must never
select this scheme for a public production release.

Existing Debug/Release build settings were compared before/after generation and
are identical; the production scheme is byte-identical. `project.yml` now records
the already-existing team, signing identity and app-icon settings so generation
preserves them. No identifier, account, certificate, capability or signing policy
was changed. Same application identity: **com.tinyroutes.app**, **Tiny Routes**,
version **1.0**, build **1**. This is not a separate app/container. Minimum iOS
**17.0**, iPhone only, portrait, arm64. The archive contains the AppIcon catalog
and generated icon files. No custom entitlements were found.

## Evidence and checklist

States are evidence-specific; a source check does not establish device usability.

| Area | Item | State | Evidence / remaining work |
|---|---|---|---|
| Engineering | Native regression | Passed, reused | Earlier MV-48 evidence: 271 executed, **268 passed, 3 platform skips**, zero failures; **51,070 assertions**. Harness retained in `scripts/run_multivan_native_tests.py`; broad suite not rerun in this packaging follow-up. |
| Engineering | Standard iOS test-target compilation | Passed, reused | Earlier unsigned generic-iOS `build-for-testing` succeeded after the test-class rename; no runtime or test-source changes in this follow-up. |
| Engineering | Standard simulator tests | Passed, reused | Earlier iPhone 16 Pro / iOS 18.5: **725 executed, 721 passed, 4 existing skips**, zero failures; not rerun in this follow-up. |
| Engineering | Release compilation and SwiftUI macros | Passed, fresh | One fresh unsigned archive attempt from the final source/resource configuration: **ARCHIVE SUCCEEDED**, exit 0. `MultiVanInternal` / `InternalTestFlight`, generic iOS, optimized arm64, whole-module compilation, no `DEBUG`. |
| Engineering | Twelve levels and original solutions | Passed | All twelve validate and win at original par; default tuple remains **(1.50, 0.35, 0.40)**. No geometry, scoring, engine, solution or production gameplay change. |
| Engineering | Determinism and gameplay regression | Passed | Existing tests cover fixed steps, collisions/precedence, live acceptance/rejection, equivalent playback budgets, stars/change counts, ordered feedback, retry/next and production/prototype discovery isolation. |
| Engineering | Archived gameplay resources | Passed, fresh | New archive inspected: 12 JSONs in `PrototypeLevels`, exactly 27 production JSONs at root, exactly 10 CAFs decoded by AVAudioPlayer, 13 decoded sprites with matching dimensions, confetti scene and Assets.car. JSON/audio/scene bytes match source. No solutions or test bundle found. |
| Engineering | Final resource packaging | Passed, fresh | `verify_multivan_bundle.swift` exited **0**: `FINAL PACKAGING PASSED: privacy manifest matches; no solutions/tests/docs`. App-root `PrivacyInfo.xcprivacy` matches source byte-for-byte; `PrototypeSounds/README.md` and all Markdown are absent. |
| Engineering | Required-API privacy declarations | Source and packaging passed | Manifest unchanged; plist lint passed, app-target registration and fresh archive inclusion verified. App-only UserDefaults and elapsed in-app timing match declared reasons. Apple's privacy report/validation remains an owner gate. |
| Engineering | Logging and default-only internal session | Passed, fresh smoke | Reran the existing runner's optimized `MULTIVAN_INTERNAL`, non-DEBUG smoke only: experimental overrides ignored; all twelve solutions at original par; recording, reopening/export, and distinct anonymous sessions passed. Broad logger/export tests reused. |
| Engineering | Release access isolation | Passed, fresh checks | Two existing entry/share source tests passed in a temporary host harness. Effective Release flags empty; internal flags only `MULTIVAN_INTERNAL`; both `-O`/wholemodule. Fresh dSYM includes prototype/session/log UI and excludes Debug tuning panel/override types. |
| Engineering | Archive/signing readiness | Awaiting authorized signing | Fresh unsigned archive and matching arm64 dSYM exist; no signature or embedded provisioning. A distributable signed archive/export requires the existing team's authorized signing/account access. No engineering packaging issue remains. |
| Physical device | Launch and Levels 1–12 gameplay | Not tested | On the final internal iPhone build: enable toggle, open list, play, Stop, Retry/Replay, fast-forward, delivery/failure feedback, Next, return to Levels, Close. |
| Physical device | Touch handling | Not tested | Check 44-point targets, live timing/lock cues, hold/release of 2×, and smallest intended screen. |
| Physical device | Audio and haptics | Not tested | Decode checks do not establish speaker quality, latency, mixing, mute behavior or physical haptics. |
| Physical device | Accessibility | Not tested | VoiceOver operation/focus, lock and route state, fast-forward toggle, result cards, larger Dynamic Type, system Reduce Motion and app reduced-animation preference, decorative focus exclusion. |
| Physical device | Share-sheet export and persistence | Not tested | Save/AirDrop a nonempty readable JSONL; return to gameplay; relaunch and confirm old records remain. Verify errors/cancellation. |
| Human acceptance | Two independent P1/P2 sessions | Requires human signoff | Use the kit; neither session has been performed. |
| Human acceptance | Exported logs and analysis | Requires human signoff | Associate each participant with session boundaries, build and actual tuning; no participant logs supplied. |
| Human acceptance | Follow-up usability retests | Requires human signoff | Identify from observations; run where necessary. Not waived. |
| Human acceptance | Five-person acceptance thresholds | Requires human signoff | See exact criteria below; two participants cannot establish these thresholds. |
| Human acceptance | Team approval / milestone exits | Requires human signoff | Agree that level ideas, Level 7 crash/fix readability and Go/sound payoff work; MV-46's team agreement remains open. |
| Distribution | TestFlight build configuration | Passed | Dedicated shared scheme/configuration and gated settings entry; archive flags and dSYM confirm prototype/session present and Debug tuning types absent. |
| Distribution | Final archive availability | Passed, unsigned candidate | Fresh final-resource `MultiVanInternal.xcarchive` is available and packaging-verified at the evidence path below. Signing, Apple validation and distribution are not complete. |
| Distribution | Apple-account and metadata readiness | Not tested | Owner must confirm App Store Connect app/team access, available build number, signing/provisioning, beta metadata/privacy answers and export compliance. |
| Distribution | Upload authorization | Requires human signoff | Not authorized; no upload attempted. |
| Distribution | Tester access / outside-team Level 1 | Blocked | No uploaded build or tester access. After approval, developer first verifies the actual TestFlight install on iPhone; owner controls any later tester invitations and required beta review. |

The three native skips are iOS gameplay-view construction and two actual app-bundle
checks; those tests **passed on the simulator**. The four simulator skips concern
three pre-existing legacy production solver sweeps and an external generated-level
test with no requested IDs. Simulator output has existing Combine import warnings
and view-construction Environment warnings; no test failures.

## Resource and privacy follow-up

The archive inspection caught an unnecessarily bundled sound-authoring document.
Its full source/licence notes are preserved at [prototype_sounds.md](prototype_sounds.md),
outside the copied sound folder. Only the ten CAF runtime files remain there.
Prototype van/house artwork is SwiftUI rendering; icons use system symbols, and
basic accessibility labels need no separate asset bundle. Existing UI components
and accessibility code compile in the non-Debug archive.

Added `PrivacyInfo.xcprivacy` declares app-only UserDefaults (`CA92.1`) and elapsed
in-app timing (`35F9.1`) for the APIs actually used. The log stores elapsed
durations, not raw system uptime. These uses match Apple's
[required-reason API documentation](https://developer.apple.com/documentation/bundleresources/app-privacy-configuration/nsprivacyaccessedapitypes/nsprivacyaccessedapitype).
The manifest does not replace App Store Connect privacy answers or a final privacy
report review. `ITSAppUsesNonExemptEncryption` is absent from the existing Info.plist;
the owner must answer Apple's export-compliance questions for the complete app
before distribution. No exemption answer was invented.

The fresh unsigned archive now passes final-resource packaging verification.
Do not distribute an unsigned archive. The owner must still produce the signed
distribution candidate using existing authorized signing assets and review
Organizer validation/privacy results before any authorized upload.
Confirm whether build 1 is unused in App Store Connect; assign an owner-approved
unused build number if needed. No signing/account changes were attempted here.

## Logging, tuning and acceptance boundaries

The session writes append-style JSONL to the app's **Documents/multi_van_playtest.jsonl**,
excluded from backup when created. Ordinary relaunches retain it; temporary export
copies are cleaned separately. The in-app log screen reads summaries and opens a
native share sheet explicitly. No development console, network upload, analytics
SDK or automatic collection was added. Each prototype opening gets a random UUID;
it is not a participant/device identity. Export after each session and keep the
kit's anonymous participant/boundary notes. Unfinished activity is recorded at
normal navigation/background boundaries; forced termination is not a flush guarantee.

InternalTestFlight always injects `.default`, ignoring persisted
`multiVanPrototype.*` tuning overrides. It has no tuning panel or override type.
The list and gameplay display the baseline tuple; record it with build identity
before each participant. Debug retains validated persistent tuning/reset and
per-level snapshots. Retry/Replay retain the engine snapshot. Neither settings
path connects to production RouteEngine, ProgressService or the economy.
JSONL still has no tuning or participant metadata; do not infer either from it.

Source wiring and tests preserve MV-41: switch labels expose route/lock state,
VoiceOver fast-forward toggles the existing speed action, layouts respond to
Dynamic Type, system/app Reduce Motion suppress extra effects, result cards name
outcomes and move focus, and decorative board effects are hidden from accessibility.
These checks do not establish physical VoiceOver focus order or timing usability.

The broader plan requires **at least five new players**, ideally two who rarely
play games: **4 of 5** press Go without help by Level 2; Levels 7–12 average
**1–3 attempts**; **3 of 5** finish all twelve or ask for more; players watch
**most runs** rather than fast-forwarding every time. Observe Levels 1–3 silently.
The P1/P2 kit is preliminary evidence only. No threshold, independent completion,
usability retest, physical-device check or team agreement has been marked passed.

## Reproduction and local evidence

From the repository root, the durable native runner includes a separate optimized
non-DEBUG session/logging smoke. It extracts existing platform-independent helpers
verbatim into disposable host support, stubs hardware calls, and instruments only
temporary test copies for assertion counting. It does not replace the iOS suite.

Broad-suite reproduction commands (earlier evidence reused, not rerun in this follow-up):

```sh
python3 scripts/run_multivan_native_tests.py
python3 scripts/run_swift_tests.py --result-bundle /tmp/mv48-next-tests.xcresult
xcodebuild build-for-testing -project TinyRoutes.xcodeproj -scheme TinyRoutes -configuration Debug -destination 'generic/platform=iOS' -derivedDataPath /tmp/mv48-next-test-build CODE_SIGNING_ALLOWED=NO
```

Executed once in this follow-up, without cache cleanup or project regeneration:

```sh
MV48_EVIDENCE=/var/folders/1n/3_py7fbs2fg88lvf2sl7dntc0000gn/T/mv48-final-l5azxni0
xcodebuild archive -project TinyRoutes.xcodeproj -scheme MultiVanInternal -configuration InternalTestFlight -destination 'generic/platform=iOS' -derivedDataPath "$MV48_EVIDENCE/DerivedData" -archivePath "$MV48_EVIDENCE/MultiVanInternal.xcarchive" CODE_SIGNING_ALLOWED=NO
xcrun swift scripts/verify_multivan_bundle.swift "$MV48_EVIDENCE/MultiVanInternal.xcarchive/Products/Applications/TinyRoutes.app"
```

Unsigned success verifies compilation/packaging only, not signing, Apple validation
or TestFlight delivery. The new archive, rather than the earlier stale archive,
is the evidence for final resource readiness. Exact verifier output (exit 0):

```text
GAMEPLAY RESOURCES PASSED: 12 prototype JSONs, 27 isolated production JSONs, 10 decodable CAFs, 13 sprites, confetti and asset catalog
Identity: com.tinyroutes.app, 1.0 (1)
FINAL PACKAGING PASSED: privacy manifest matches; no solutions/tests/docs
```

Fresh focused execution used the unchanged `run_multivan_native_tests.py` helper,
resource-link, compiler-setup and `InternalSmoke` sections in memory, omitting
the broad regression section. It printed `INTERNAL SMOKE PASSED: 12 default
solutions at par, overrides ignored, local log reopened/exported, anonymous
sessions distinct`. Its disposable host artifacts are at
`/var/folders/1n/3_py7fbs2fg88lvf2sl7dntc0000gn/T/multivan-native-w1926d3v`.
The existing `testDistributionEntryRequiresInternalBuildAndSettingsOptIn` and
`testShareUIIsInternalOnlyAccessibleAndOutsideGameplay` methods were copied
verbatim into a temporary XCTest host harness: **2 executed, 0 failures**.
An initial temporary extraction included an extra closing brace; correcting that
harness resolved its compilation diagnostic without any repository code change.

`archive-inspection.log` records exact file counts, matching executable/dSYM UUID
`E2CAEEE5-6FC1-3B95-9FCF-18CED1C9CA53`, and executable SHA-256
`fb3b688b478bf737078750ceb9446c4ddb358e169f90acce2e7e1ca17fd1d362`.
The app target's InternalTestFlight settings match Release except for the internal
compilation condition; no signing/identity difference was introduced. Input
SHA-256 checks confirm all app source/resources, project/schemes and validation
scripts stayed unchanged during this follow-up. Ordinary Release access is
established by source gates and effective configuration, not a second archive.
Production discovery continues to use its existing repository, with all 27
production JSONs isolated from the prototype folder; prior regression evidence
remains applicable.

Fresh local evidence lives under `$MV48_EVIDENCE`: `release-archive.log`,
`packaging.log`, `archive-inspection.log`, `internal-smoke.log`, `source-smoke.log`,
`source-smoke-initial-diagnostic.log`, `release-build-settings.json`,
`internal-build-settings.json`, `internal-symbols.txt`, `input-sha256.json`, and
`MultiVanInternal.xcarchive`. The archive succeeded with existing Combine import
warnings in `GameplayScreen.swift` and an AppIntents metadata-skipped warning;
no build errors. These are not packaging blockers. No broader suite was rerun,
and no validation script change was required.

Earlier broad-suite evidence reused: `/tmp/mv48/native.log`, `standard-tests.log`,
`simulator-tests.log`, `simulator-summary.json`, and `SimulatorTests.xcresult`.
Native artifact location is printed in `native.log`. The earlier archive and its
packaging results are historical only and are not evidence for this follow-up.
Temporary evidence is not a repository resource.

Original MV-48 scope (preexisting this follow-up): configuration/scheme and generated project; Home/Settings entry;
conditional prototype session/panel; decoding-suite rename and entry/log UI tests;
privacy manifest; sound-note relocation; playtest-kit entry instructions; two
validation scripts and this checklist. This follow-up changed only this readiness
checklist. No gameplay/engine/levels/tuning, manifest declarations, validation
scripts, shared production scheme or signing settings changed. No Git commands,
staging, commits, worktrees, signing/account changes or distribution actions were
performed. Existing edits remain unstaged and uncommitted.
