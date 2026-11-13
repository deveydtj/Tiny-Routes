#!/bin/zsh
# Double-click in Finder, or run from a terminal.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "${0:A:h}"
finish() {
  local result=$?
  if (( result != 0 )); then print '\nExternal TestFlight release failed. See the error above.'; fi
  if [[ -t 0 ]]; then read '?Press Return to close this window…'; fi
  return $result
}
trap finish EXIT
command -v fastlane >/dev/null || { print 'Install fastlane: brew install fastlane'; exit 1; }
export FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_USAGE=1 FASTLANE_HIDE_CHANGELOG=1 FASTLANE_SKIP_DOCS=1
fastlane external "$@"
