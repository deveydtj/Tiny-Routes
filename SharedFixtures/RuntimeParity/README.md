# Runtime Parity Fixtures

Each case contains the same three language-neutral inputs: `level.json`, `events.json`, and `expected.json`. The event stream uses absolute tap times plus deterministic elapsed-time increments. Expected files state the terminal outcome, rejection reason, tap count, collection state, and optional cycle safety limit. Schema-3 cases can additionally assert completed objective order, objective-gated edge usage, and the normalized final switch state.

Both test targets discover cases through `manifest.json`; do not maintain separate Swift and Python copies.
