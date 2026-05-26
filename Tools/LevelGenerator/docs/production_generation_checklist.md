# Production Generation Checklist

## Dry Run

- Run a deterministic dry run with the intended start, count, difficulty, template, and seed.
- Confirm accepted candidates print in the CLI or appear in the GUI.
- Open the markdown and JSON reports.
- Review rejection counts, especially duplicate/similarity rejections.
- Do not commit any dry-run report churn unless the report itself is the artifact under review.

## Scratch Folder

- Write candidates to temporary level and solution directories.
- Keep `--no-xcodegen` enabled for scratch output.
- Confirm each `level_###.json` has a matching `level_###.solution.json`.
- Open a few scratch levels in the Level Editor before writing production resources.

## Production Folder

- Write only after dry-run and scratch review look acceptable.
- Never commit a generated level without its matching solution file.
- Use `--overwrite` only when intentionally replacing existing generated files.
- Keep the generation report with the reviewed batch when useful for audit.

## Level Editor Review

- Confirm start, package, destination, switches, and dead ends are visually readable.
- Confirm routes do not overlap or cross in confusing ways.
- Confirm the intended tap sequence is understandable.
- Reject levels that look like obvious clones of nearby campaign levels.

## Swift Tests

- Run Swift solvability tests before production commits when Xcode is available.
- Treat Python validation as fast local protection, not a replacement for Swift confidence.
- Investigate any Swift failure before committing generated files.

## Simulator Playtest

- Play each production candidate in the simulator.
- Confirm the route can complete within the time limit.
- Confirm tap timing feels fair for the intended difficulty.
- Confirm dead ends feel intentional rather than misleading JSON mistakes.

## Xcode Resource Cleanup

- Run XcodeGen or confirm resource references after adding, overwriting, or deleting generated levels.
- If writing to default production folders, the generator runs XcodeGen unless `--no-xcodegen` is passed.
- After manual deletion, run `xcodegen generate` so stale `.xcodeproj` resource references are removed.

## Commit

- Include level JSON, solution JSON, and intentional report/doc changes.
- Exclude scratch output and incidental `last_generation_report.*` churn unless requested.
- Include the seed, template mode, difficulty, and validation commands in the commit or PR notes.
