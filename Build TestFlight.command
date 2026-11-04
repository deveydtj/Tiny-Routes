#!/bin/zsh
# Adapted from node-platform/Build TestFlight.command. Double-click in Finder.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "${0:A:h}"
finish() {
  local result=$?
  if (( result != 0 )); then print '\nTestFlight build/upload failed. See the error above.'; fi
  if [[ -t 0 ]]; then read '?Press Return to close this window…'; fi
  return $result
}
trap finish EXIT
print 'Building Tiny Routes locally with the MultiVanInternal TestFlight scheme.'
print 'Uses the Apple account in Xcode Settings → Accounts for signing and upload.'
print 'Upload is restricted to internal TestFlight testing. Xcode manages the upload build number.'
xcodebuild -version >/dev/null || { print 'Install Xcode and select it with xcode-select.'; exit 1; }
artifact_dir="$PWD/.local/testflight/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$artifact_dir"
print "Build artifacts and logs: $artifact_dir"
exec > >(tee "$artifact_dir/build-upload.log") 2>&1
archive_path="$artifact_dir/TinyRoutes.xcarchive"
xcodebuild archive -project TinyRoutes.xcodeproj -scheme MultiVanInternal \
  -configuration InternalTestFlight -destination 'generic/platform=iOS' \
  -derivedDataPath "$PWD/.local/testflight/DerivedData" \
  -archivePath "$archive_path" -allowProvisioningUpdates
xcrun swift scripts/verify_multivan_bundle.swift "$archive_path/Products/Applications/TinyRoutes.app"
cat > "$artifact_dir/ExportOptions.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>method</key><string>app-store-connect</string>
  <key>destination</key><string>upload</string>
  <key>signingStyle</key><string>automatic</string>
  <key>teamID</key><string>JM23Z9GG95</string>
  <key>manageAppVersionAndBuildNumber</key><true/>
  <key>testFlightInternalTestingOnly</key><true/>
  <key>uploadSymbols</key><true/>
</dict></plist>
PLIST
xcodebuild -exportArchive -archivePath "$archive_path" \
  -exportPath "$artifact_dir/export" -exportOptionsPlist "$artifact_dir/ExportOptions.plist" \
  -allowProvisioningUpdates
print 'Upload succeeded. Wait for Apple processing, then check App Store Connect → Tiny Routes → TestFlight.'
print 'On iPhone: Settings → About → Multi-Van Prototype, then Home → Prototype.'
