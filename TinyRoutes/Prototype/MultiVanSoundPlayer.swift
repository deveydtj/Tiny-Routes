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

    static func sound(for event: MultiVanEvent) -> Self {
        switch event {
        case .switchTapped: .click
        case .tapRejected: .dullTick
        case .go: .vroom
        case let .delivered(_, index): [.chime1, .chime2, .chime3, .chime4][min(max(index, 1), 4) - 1]
        case .allDelivered: .fanfare
        case .crashed: .bonk
        case .wrongHouse: .nopeHorn
        }
    }
}

@MainActor
final class MultiVanSoundPlayer: ObservableObject {
    private var voices: [MultiVanSound: [any MultiVanAudioVoice]] = [:]
    private var urls: [MultiVanSound: URL] = [:]
    private let makeVoice: (URL) throws -> any MultiVanAudioVoice
    private let activateSession: () throws -> Void
    private var sessionReady = false
    private var enabled = true
    private var volume: Float = 0.85

    init(
        resourceURL: (String) -> URL? = {
            Bundle.main.url(forResource: $0, withExtension: "caf", subdirectory: "PrototypeSounds")
        },
        makeVoice: @escaping (URL) throws -> any MultiVanAudioVoice = { try AVAudioPlayer(contentsOf: $0) },
        configureSession: () throws -> Void = {
            try AVAudioSession.sharedInstance().setCategory(.ambient)
        },
        activateSession: @escaping () throws -> Void = {
            try AVAudioSession.sharedInstance().setActive(true)
        }
    ) {
        self.makeVoice = makeVoice
        self.activateSession = activateSession
        // prepareToPlay can activate the session: select mixing before warming voices.
        do { try configureSession() } catch { return }
        for sound in MultiVanSound.allCases {
            guard let url = resourceURL(sound.rawValue) else { continue }
            urls[sound] = url
            // Two warm voices cover rapid taps without cutting off a previous sound.
            voices[sound] = (0..<2).compactMap { _ in
                guard let voice = try? makeVoice(url) else { return nil }
                voice.prepareToPlay()
                return voice
            }
        }
    }

    func update(settings: UserSettings) {
        enabled = settings.areSoundEffectsEnabled
        volume = Float(settings.normalized().soundEffectsVolume)
        for voice in voices.values.flatMap({ $0 }) { voice.volume = volume }
        if !enabled { stop() }
    }

    func play(_ event: MultiVanEvent) {
        guard enabled, volume > 0 else { return }
        let sound = MultiVanSound.sound(for: event)
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
