import AVFoundation
import XCTest
@testable import TinyRoutes

@MainActor
final class MultiVanSoundPlayerTests: XCTestCase {
    private final class Voice: MultiVanAudioVoice {
        let name: String
        var isPlaying = false
        var volume: Float = 1
        var currentTime: TimeInterval = 0
        var plays = 0
        var onPlay: ((String) -> Void)?
        init(_ name: String) { self.name = name }
        func prepareToPlay() -> Bool { true }
        func play() -> Bool {
            isPlaying = true
            plays += 1
            onPlay?(name)
            return true
        }
        func stop() { isPlaying = false }
    }

    @MainActor private final class Rig {
        var voices: [Voice] = []
        var played: [String] = []
        var activations = 0
        lazy var player = MultiVanSoundPlayer(
            resourceURL: { URL(fileURLWithPath: "/\($0).caf") },
            makeVoice: { url in
                let voice = Voice(url.deletingPathExtension().lastPathComponent)
                voice.onPlay = { self.played.append($0) }
                self.voices.append(voice)
                return voice
            },
            configureSession: {}, activateSession: { self.activations += 1 }
        )
    }

    func testEveryEventMapsToExpectedSound() {
        let cases: [(MultiVanEvent, MultiVanSound)] = [
            (.switchTapped, .click), (.tapRejected(nodeID: "s"), .dullTick), (.go, .vroom),
            (.delivered(vanID: "v", comboIndex: 1), .chime1), (.allDelivered, .fanfare),
            (.crashed(point: RoadPoint(x: 0, y: 0)), .bonk), (.wrongHouse(vanID: "v"), .nopeHorn)
        ]
        for (event, sound) in cases { XCTAssertEqual(MultiVanSound.sound(for: event), sound) }
    }

    func testChimesAndClamping() {
        let indices = [Int.min, 0, 1, 2, 3, 4, 5, Int.max]
        let expected: [MultiVanSound] = [.chime1, .chime1, .chime1, .chime2, .chime3, .chime4, .chime4, .chime4]
        for (index, sound) in zip(indices, expected) {
            XCTAssertEqual(MultiVanSound.sound(for: .delivered(vanID: "v", comboIndex: index)), sound)
        }
    }

    func testMissingAndUnreadableResourcesAreSilent() {
        var attempts = 0
        let missing = MultiVanSoundPlayer(resourceURL: { _ in nil }, makeVoice: { _ in
            attempts += 1
            throw CocoaError(.fileReadNoSuchFile)
        }, configureSession: {}, activateSession: { XCTFail("Missing assets must not activate audio") })
        missing.play(.go)
        XCTAssertEqual(attempts, 0)
        let unreadable = MultiVanSoundPlayer(resourceURL: { URL(fileURLWithPath: "/\($0).caf") }, makeVoice: { _ in
            throw CocoaError(.fileReadCorruptFile)
        }, configureSession: {}, activateSession: {})
        unreadable.play(.allDelivered)
    }

    func testSettingsApplyImmediatelyAndHapticsStayIndependent() {
        let rig = Rig()
        var settings = UserSettings(areSoundEffectsEnabled: false)
        var haptics: [MultiVanHaptic] = []
        MultiVanFeedback.process(drainEvents: { [.go] }, settings: settings, soundPlayer: rig.player,
                                 playHaptic: { haptics.append($0) })
        XCTAssertEqual(haptics, [.mediumImpact])
        XCTAssertTrue(rig.played.isEmpty)
        XCTAssertEqual(rig.activations, 0)
        settings.areSoundEffectsEnabled = true
        settings.soundEffectsVolume = 0.3
        settings.areHapticsEnabled = false
        MultiVanFeedback.process(drainEvents: { [.go] }, settings: settings, soundPlayer: rig.player,
                                 playHaptic: { _ in XCTFail("Haptics disabled") })
        XCTAssertEqual(rig.played, ["vroom"])
        XCTAssertEqual(rig.voices.first(where: { $0.isPlaying })?.volume, 0.3)
        settings.soundEffectsVolume = 0.7
        rig.player.update(settings: settings)
        XCTAssertTrue(rig.voices.allSatisfy { $0.volume == 0.7 })
        settings.areSoundEffectsEnabled = false
        rig.player.update(settings: settings)
        XCTAssertFalse(rig.voices.contains { $0.isPlaying })
        rig.player.play(.allDelivered)
        XCTAssertEqual(rig.played, ["vroom"])
    }

    func testSameFrameOrderSingleDrainAndNoReplay() {
        let rig = Rig()
        var pending: [MultiVanEvent] = [.go, .delivered(vanID: "a", comboIndex: 1),
            .delivered(vanID: "b", comboIndex: 2), .allDelivered]
        var drains = 0
        var haptics: [MultiVanHaptic] = []
        let expected = pending
        var visuals: [MultiVanEvent] = []
        let drain = { drains += 1; let result = pending; pending.removeAll(); return result }
        MultiVanFeedback.process(drainEvents: drain, settings: UserSettings(), soundPlayer: rig.player,
                                 playHaptic: { haptics.append($0) }, reactVisually: { event in
            XCTAssertEqual(rig.played.count, visuals.count + 1, "Sound dispatch precedes each visual")
            visuals.append(event)
        })
        XCTAssertEqual(drains, 1)
        XCTAssertEqual(visuals, expected)
        XCTAssertEqual(rig.played, ["vroom", "chime_1", "chime_2", "fanfare"])
        XCTAssertEqual(haptics, [.mediumImpact, .success, .success, .success])
        rig.player.stop() // Stop/Retry silence current voices; an empty cycle cannot replay them.
        MultiVanFeedback.process(drainEvents: drain, settings: UserSettings(), soundPlayer: rig.player,
                                 playHaptic: { _ in XCTFail("No old haptics") },
                                 reactVisually: { _ in XCTFail("No old visuals") })
        XCTAssertEqual(drains, 2)
        XCTAssertEqual(rig.played.count, 4)
        XCTAssertFalse(rig.voices.contains { $0.isPlaying })
    }

    func testOverlapPreservesPlayingVoicesAndReusesPool() {
        let rig = Rig()
        let player = rig.player
        let preloaded = rig.voices.count
        for _ in 0..<4 { player.play(.allDelivered) }
        XCTAssertEqual(rig.played, Array(repeating: "fanfare", count: 4))
        XCTAssertEqual(rig.voices.filter { $0.isPlaying }.count, 4)
        XCTAssertEqual(rig.voices.count, preloaded + 2)
        XCTAssertEqual(rig.activations, 1)
        player.stop()
        player.play(.allDelivered)
        XCTAssertEqual(rig.voices.count, preloaded + 2)
    }

    func testCrashEffectsShareSingleDrainWithBonkAndHaptic() throws {
        let rig = Rig()
        let point = RoadPoint(x: 1.25, y: 2.5)
        var pending: [MultiVanEvent] = [.crashed(point: point)]
        var effects = MultiVanCrashEffects()
        var drains = 0
        var haptics: [MultiVanHaptic] = []
        func dispatch() {
            MultiVanFeedback.process(drainEvents: {
                drains += 1
                defer { pending.removeAll() }
                return pending
            }, settings: UserSettings(), soundPlayer: rig.player,
            playHaptic: { haptics.append($0) },
            reactVisually: { effects.process($0, reduceMotion: false) })
        }
        dispatch()
        let impact = try XCTUnwrap(effects.impact)
        XCTAssertEqual(impact.point, point)
        XCTAssertEqual(drains, 1)
        XCTAssertEqual(rig.played, ["bonk"])
        XCTAssertEqual(haptics, [.error])
        dispatch()
        XCTAssertEqual(drains, 2)
        XCTAssertEqual(effects.impact?.id, impact.id)
        XCTAssertEqual(rig.played, ["bonk"])
        XCTAssertEqual(haptics, [.error])
    }

    func testSessionFailureIsGraceful() {
        let player = MultiVanSoundPlayer(resourceURL: { URL(fileURLWithPath: "/\($0).caf") },
            makeVoice: { Voice($0.lastPathComponent) },
            configureSession: {},
            activateSession: { throw CocoaError(.featureUnsupported) })
        player.play(.go)
    }

    func testBundledAssetsDecode() throws {
        for sound in MultiVanSound.allCases {
            let url = try XCTUnwrap(Bundle.main.url(forResource: sound.rawValue, withExtension: "caf",
                                                   subdirectory: "PrototypeSounds"))
            let file = try AVAudioFile(forReading: url)
            XCTAssertEqual(file.processingFormat.channelCount, 1)
            XCTAssertEqual(file.processingFormat.sampleRate, 22050)
            XCTAssertGreaterThan(file.length, 0)
            XCTAssertLessThanOrEqual(Double(file.length) / file.processingFormat.sampleRate, 0.85)
        }
    }
}
