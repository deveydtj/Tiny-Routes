import AVFoundation
import Combine

// A small seam lets native tests exercise playback without opening an audio device.
protocol MultiVanAudioVoice: AnyObject {
    var isPlaying: Bool { get }
    var volume: Float { get set }
    var currentTime: TimeInterval { get set }
    @discardableResult func play() -> Bool
    func stop()
    @discardableResult func prepareToPlay() -> Bool
}

extension AVAudioPlayer: MultiVanAudioVoice {}

enum MultiVanSound: String, CaseIterable {
    case click, dullTick = "dull_tick", vroom
    case chime1 = "chime_1", chime2 = "chime_2", chime3 = "chime_3", chime4 = "chime_4"
    case fanfare, bonk, nopeHorn = "nope_horn"

    /// Nil for events that pass in silence.
    static func sound(for event: MultiVanEvent) -> Self? {
        switch event {
        case .switchTapped: .click
        case .tapRejected: .dullTick
        case .go: .vroom
        case let .delivered(_, index): [.chime1, .chime2, .chime3, .chime4][min(max(index, 1), 4) - 1]
        case .allDelivered: .fanfare
        case .crashed: .bonk
        case .wrongHouse, .missingPackage: .nopeHorn
        // A parcel lands on the roof with the switch's soft click.
        case .pickedUp, .paused, .resumed: .click
        case .held, .released: nil
        }
    }
}

/// Plays the game's sounds. Starting one can block while the audio hardware wakes,
/// long enough to freeze the diorama's camera mid-morph, so the voices live on
/// their own queue and the main thread only hands them requests.
@MainActor
final class MultiVanSoundPlayer: ObservableObject {
    private let mixer: Mixer
    private let perform: (@escaping @Sendable () -> Void) -> Void
    private var enabled = true
    private var volume: Float = 0.85

    /// `perform` runs each request in order; tests pass one that runs it at once.
    init(
        resourceURL: (String) -> URL? = {
            Bundle.main.url(forResource: $0, withExtension: "caf", subdirectory: "PrototypeSounds")
        },
        makeVoice: @escaping (URL) throws -> any MultiVanAudioVoice = { try AVAudioPlayer(contentsOf: $0) },
        configureSession: @escaping () throws -> Void = {
            try AVAudioSession.sharedInstance().setCategory(.ambient)
        },
        activateSession: @escaping () throws -> Void = {
            try AVAudioSession.sharedInstance().setActive(true)
        },
        perform: @escaping (@escaping @Sendable () -> Void) -> Void = MultiVanSoundPlayer.onAudioQueue
    ) {
        var urls: [MultiVanSound: URL] = [:]
        for sound in MultiVanSound.allCases {
            urls[sound] = resourceURL(sound.rawValue)
        }
        let mixer = Mixer(urls: urls, makeVoice: makeVoice, activateSession: activateSession)
        self.mixer = mixer
        self.perform = perform
        perform { mixer.load(configureSession: configureSession) }
    }

    nonisolated private static let queue = DispatchQueue(label: "com.tinyroutes.app.sound", qos: .userInitiated)

    nonisolated static func onAudioQueue(_ work: @escaping @Sendable () -> Void) {
        queue.async(execute: work)
    }

    func update(settings: UserSettings) {
        enabled = settings.areSoundEffectsEnabled
        let volume = Float(settings.normalized().soundEffectsVolume)
        // Every event batch passes the settings; only a change reaches the voices.
        if volume != self.volume {
            self.volume = volume
            let mixer = mixer
            perform { mixer.setVolume(volume) }
        }
        if !enabled { stop() }
    }

    func play(_ event: MultiVanEvent) {
        guard enabled, volume > 0 else { return }
        guard let sound = MultiVanSound.sound(for: event) else { return }
        let volume = volume
        let mixer = mixer
        perform { mixer.play(sound, volume: volume) }
    }

    func stop() {
        let mixer = mixer
        perform { mixer.stop() }
    }

    /// The voices, touched only through the player's `perform`, one request at a time.
    private final class Mixer: @unchecked Sendable {
        private var voices: [MultiVanSound: [any MultiVanAudioVoice]] = [:]
        private var urls: [MultiVanSound: URL]
        private let makeVoice: (URL) throws -> any MultiVanAudioVoice
        private let activateSession: () throws -> Void
        private var sessionReady = false

        init(
            urls: [MultiVanSound: URL],
            makeVoice: @escaping (URL) throws -> any MultiVanAudioVoice,
            activateSession: @escaping () throws -> Void
        ) {
            self.urls = urls
            self.makeVoice = makeVoice
            self.activateSession = activateSession
        }

        func load(configureSession: () throws -> Void) {
            // prepareToPlay can activate the session: select mixing before warming voices.
            do { try configureSession() } catch {
                urls = [:]
                return
            }
            for (sound, url) in urls {
                // Two warm voices cover rapid taps without cutting off a previous sound.
                voices[sound] = (0..<2).compactMap { _ in
                    guard let voice = try? makeVoice(url) else { return nil }
                    voice.prepareToPlay()
                    return voice
                }
            }
        }

        func setVolume(_ volume: Float) {
            for voice in voices.values.flatMap({ $0 }) { voice.volume = volume }
        }

        func play(_ sound: MultiVanSound, volume: Float) {
            guard let url = urls[sound] else { return }
            if !sessionReady {
                do {
                    try activateSession()
                    sessionReady = true
                } catch { return }
            }
            let voice: any MultiVanAudioVoice
            if let idle = voices[sound]?.first(where: { !$0.isPlaying }) {
                voice = idle
            } else {
                // Grow only for overlapping bursts; retain voices for subsequent events.
                guard let extra = try? makeVoice(url) else { return }
                voices[sound, default: []].append(extra)
                voice = extra
            }
            voice.volume = volume
            voice.currentTime = 0
            voice.play()
        }

        func stop() {
            for voice in voices.values.flatMap({ $0 }) {
                voice.stop()
                voice.currentTime = 0
            }
        }
    }
}
