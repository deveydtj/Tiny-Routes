// Run with: xcrun swift scripts/verify_multivan_bundle.swift /path/to/TinyRoutes.app
import Foundation
import AVFoundation
import ImageIO

let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
guard CommandLine.arguments.count == 2,
      let bundle = Bundle(path: CommandLine.arguments[1]) else {
    fatalError("Pass the produced TinyRoutes.app path")
}
let app = bundle.bundleURL
let resources = root.appendingPathComponent("TinyRoutes/Resources")
let manager = FileManager.default

func files(_ directory: URL, extension suffix: String) throws -> [URL] {
    try manager.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        .filter { $0.pathExtension == suffix }.sorted { $0.lastPathComponent < $1.lastPathComponent }
}

func sameBytes(_ source: URL, _ destination: URL) throws {
    let original = try Data(contentsOf: source)
    let packaged = try Data(contentsOf: destination)
    precondition(original == packaged, "Resource mismatch: \(destination.path)")
}

let expectedIDs = try files(resources.appendingPathComponent("PrototypeLevels"), extension: "json")
    .map { $0.deletingPathExtension().lastPathComponent }
precondition(!expectedIDs.isEmpty, "Source gameplay levels are missing")
let levels = bundle.urls(forResourcesWithExtension: "json", subdirectory: "PrototypeLevels") ?? []
precondition(levels.map { $0.deletingPathExtension().lastPathComponent }.sorted() == expectedIDs)
for level in levels {
    try sameBytes(resources.appendingPathComponent("PrototypeLevels/\(level.lastPathComponent)"), level)
    let json = try JSONSerialization.jsonObject(with: Data(contentsOf: level)) as! [String: Any]
    precondition(json["id"] as? String == level.deletingPathExtension().lastPathComponent)
}
// The retired single-dot levels were bundled at the app root; none may remain.
let rootJSONs = try files(app, extension: "json")
precondition(rootJSONs.isEmpty, "Retired root-level JSONs remain: \(rootJSONs.map(\.lastPathComponent))")

let sounds = ["click", "dull_tick", "vroom", "chime_1", "chime_2", "chime_3", "chime_4", "fanfare", "bonk", "nope_horn"]
for name in sounds {
    guard let url = bundle.url(forResource: name, withExtension: "caf", subdirectory: "PrototypeSounds") else {
        fatalError("Missing sound: \(name)")
    }
    try sameBytes(resources.appendingPathComponent("PrototypeSounds/\(name).caf"), url)
    let player = try AVAudioPlayer(contentsOf: url)
    precondition(player.duration > 0 && player.numberOfChannels > 0)
}
let sprites = try files(resources.appendingPathComponent("Sprites"), extension: "png")
// Xcode recompresses PNGs, so validate decoding and dimensions instead of bytes.
for sprite in sprites {
    let packaged = app.appendingPathComponent(sprite.lastPathComponent)
    guard let originalSource = CGImageSourceCreateWithURL(sprite as CFURL, nil),
          let packagedSource = CGImageSourceCreateWithURL(packaged as CFURL, nil),
          let original = CGImageSourceCreateImageAtIndex(originalSource, 0, nil),
          let image = CGImageSourceCreateImageAtIndex(packagedSource, 0, nil) else {
        fatalError("Artwork failed to decode: \(sprite.lastPathComponent)")
    }
    precondition(image.width == original.width && image.height == original.height)
}
try sameBytes(resources.appendingPathComponent("LevelCompleteConfetti.sks"), app.appendingPathComponent("LevelCompleteConfetti.sks"))
precondition(manager.fileExists(atPath: app.appendingPathComponent("Assets.car").path))
let packaged = manager.enumerator(at: app, includingPropertiesForKeys: nil)!.allObjects as! [URL]
print("GAMEPLAY RESOURCES PASSED: \(expectedIDs.count) multi-van level JSONs, no retired level JSONs, 10 decodable CAFs, \(sprites.count) sprites, confetti and asset catalog")
print("Identity: \(bundle.bundleIdentifier ?? "missing"), \(bundle.object(forInfoDictionaryKey: "CFBundleShortVersionString") ?? "missing") (\(bundle.object(forInfoDictionaryKey: "CFBundleVersion") ?? "missing"))")
// Help shows one step of a level's recorded solution, so the app carries those
// scripts: one per bundled level, byte for byte what the tests prove, and
// nothing else from the test tree.
let solutionSource = root.appendingPathComponent("TinyRoutesTests/Resources/PrototypeSolutions")
let solutionFolder = app.appendingPathComponent("PrototypeSolutions").standardizedFileURL
var allowed = Set([solutionFolder.path])
for id in expectedIDs {
    let name = "\(id).solution.json"
    let bundled = solutionFolder.appendingPathComponent(name)
    guard manager.fileExists(atPath: bundled.path) else {
        print("BLOCKED: level \(id) has no bundled solution for help to read: \(name)")
        exit(1)
    }
    try sameBytes(solutionSource.appendingPathComponent(name), bundled)
    allowed.insert(bundled.path)
}
let unwanted = packaged.filter { url in
    if allowed.contains(url.standardizedFileURL.path) { return false }
    return url.path.contains("PrototypeSolutions") || url.lastPathComponent.hasSuffix(".solution.json") || ["md", "xctest"].contains(url.pathExtension)
}
for url in unwanted { print("BLOCKED: unexpected bundled authoring/test file: \(url.path)") }
let privacy = app.appendingPathComponent("PrivacyInfo.xcprivacy")
guard manager.fileExists(atPath: privacy.path) else {
    print("BLOCKED: PrivacyInfo.xcprivacy is absent. Rebuild the archive from the final resource configuration.")
    exit(1)
}
try sameBytes(resources.appendingPathComponent("PrivacyInfo.xcprivacy"), privacy)
guard unwanted.isEmpty else { exit(1) }
print("FINAL PACKAGING PASSED: privacy manifest matches; \(expectedIDs.count) help solutions match their levels; no stray solutions/tests/docs")
