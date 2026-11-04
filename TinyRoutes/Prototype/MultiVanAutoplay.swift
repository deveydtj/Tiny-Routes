#if DEBUG || MULTIVAN_INTERNAL
import Foundation

/// A launch option for profiling: opens one level on one board and plays it on a
/// loop with no touches, so both boards can be measured on a device under the
/// same workload. Internal builds only, and only when launched with
/// `-MultiVanAutoplay '<json>'`, for example from `scripts/profile_multivan_boards.sh`:
///
///     {"levelID": "level_012", "board": "diorama",
///      "planTaps": ["red_switch"], "liveTaps": [{"atTime": 5.25, "nodeID": "split_switch"}]}
///
/// The taps use the solution scripts' format, so a looped level is won every time.
/// The player's saved settings are never changed, and a normal launch never sees it.
struct MultiVanAutoplay: Decodable, Equatable {
    struct LiveTap: Decodable, Equatable {
        let atTime: Double
        let nodeID: String
    }

    let levelID: String
    let board: MultiVanBoardStyle
    var planTaps: [String] = []
    var liveTaps: [LiveTap] = []
    /// Time spent planning before Go, with the plan taps spread across it.
    var planSeconds = 4.0
    /// Time on the result before trying again, long enough for the win stars.
    var resultSeconds = 4.0

    static let launchArgument = "MultiVanAutoplay"

    /// The launch option, read once from the process's own arguments: the
    /// `UserDefaults` argument domain parses a value starting with `{` as a
    /// property list and drops JSON.
    static let launchConfiguration: MultiVanAutoplay? = configuration(arguments: ProcessInfo.processInfo.arguments)

    static func configuration(arguments: [String]) -> MultiVanAutoplay? {
        guard let flag = arguments.firstIndex(of: "-" + launchArgument), flag + 1 < arguments.count else { return nil }
        return configuration(from: arguments[flag + 1])
    }

    static func configuration(from json: String?) -> MultiVanAutoplay? {
        guard let data = json?.data(using: .utf8) else { return nil }
        return try? JSONDecoder().decode(MultiVanAutoplay.self, from: data)
    }

    private enum CodingKeys: String, CodingKey {
        case levelID, board, planTaps, liveTaps, planSeconds, resultSeconds
    }

    init(levelID: String, board: MultiVanBoardStyle, planTaps: [String] = [], liveTaps: [LiveTap] = [],
         planSeconds: Double = 4, resultSeconds: Double = 4) {
        self.levelID = levelID
        self.board = board
        self.planTaps = planTaps
        self.liveTaps = liveTaps
        self.planSeconds = planSeconds
        self.resultSeconds = resultSeconds
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        levelID = try container.decode(String.self, forKey: .levelID)
        board = try container.decode(MultiVanBoardStyle.self, forKey: .board)
        planTaps = try container.decodeIfPresent([String].self, forKey: .planTaps) ?? []
        liveTaps = try container.decodeIfPresent([LiveTap].self, forKey: .liveTaps) ?? []
        planSeconds = try container.decodeIfPresent(Double.self, forKey: .planSeconds) ?? 4
        resultSeconds = try container.decodeIfPresent(Double.self, forKey: .resultSeconds) ?? 4
    }

    /// The settings the board switcher sees: this board, whatever Low Power Mode says.
    func settings(from settings: UserSettings) -> UserSettings {
        var settings = settings
        settings.boardStyle = board
        settings.usesFlatBoardInLowPowerMode = false
        return settings
    }
}

/// Decides the autoplay's next press from the engine and the clock. The gameplay
/// screen carries each one out through the same paths as the player's own taps.
final class MultiVanAutoplayDriver {
    enum Press: Equatable {
        case resetSwitches, tap(String), go, retry
    }

    let autoplay: MultiVanAutoplay
    private var phase: MultiVanEngine.Phase?
    private var engineID: ObjectIdentifier?
    private var phaseStartedAt = 0.0
    private var pressedReset = false
    private var nextPlanTap = 0
    private var nextLiveTap = 0

    init(_ autoplay: MultiVanAutoplay) {
        self.autoplay = autoplay
    }

    /// Call often: in the plan and result phases from a timer, and in the run
    /// phase after every frame advances the engine, so live taps land on time.
    func nextPress(engine: MultiVanEngine, now: Double) -> Press? {
        if engine.phase != phase || ObjectIdentifier(engine) != engineID {
            phase = engine.phase
            engineID = ObjectIdentifier(engine)
            phaseStartedAt = now
            pressedReset = false
            nextPlanTap = 0
            nextLiveTap = 0
        }
        let elapsed = now - phaseStartedAt
        switch engine.phase {
        case .plan:
            // A retry keeps the last run's switches, live taps included.
            guard pressedReset else {
                pressedReset = true
                return .resetSwitches
            }
            let spacing = autoplay.planSeconds / Double(autoplay.planTaps.count + 1)
            if nextPlanTap < autoplay.planTaps.count {
                guard elapsed >= spacing * Double(nextPlanTap + 1) else { return nil }
                nextPlanTap += 1
                return .tap(autoplay.planTaps[nextPlanTap - 1])
            }
            return elapsed >= autoplay.planSeconds ? .go : nil
        case .run:
            guard nextLiveTap < autoplay.liveTaps.count,
                  engine.runTime >= autoplay.liveTaps[nextLiveTap].atTime else { return nil }
            nextLiveTap += 1
            return .tap(autoplay.liveTaps[nextLiveTap - 1].nodeID)
        case .finished:
            return elapsed >= autoplay.resultSeconds ? .retry : nil
        }
    }
}
#endif
