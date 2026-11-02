import Foundation

/// Prototype-local JSON Lines. One `attempt` row per planning/run attempt, plus
/// `quit_at_level` markers when the prototype closes or backgrounds (also from
/// the list). MV-44 can read fileURL; no completed history is retained in memory.
/// Owned by the prototype session and called only at action/dispatch boundaries.
final class MultiVanPlaytestLog {
    enum Action: String, Codable {
        case levelStarted = "level_started", planningStarted = "planning_started", retry, replay, resume, go, stop, reset
        case switchTap = "switch_tap", speedChanged = "speed_changed"
        case delivered, collision, wrongHouse = "wrong_house", allDelivered = "all_delivered"
        case completed, abandoned
    }

    struct Event: Codable, Equatable {
        let action: Action
        /// Seconds since this attempt began, from system uptime, never wall time.
        let elapsedRealSeconds: Double
        /// Engine time when the action/batch was observed. A dispatched batch can
        /// span several fixed steps; these are NOT per-delivery arrival times.
        let observedSimulationTime: Double
        let phase: String
        var nodeID: String? = nil
        var tapResult: String? = nil
        var selectedEdgeID: String? = nil
        var speedMultiplier: Double? = nil
        var vanID: String? = nil
    }

    struct Attempt: Codable, Equatable {
        var recordType = "attempt"
        var schemaVersion = 1
        let sessionID: UUID
        let levelSessionID: UUID
        let levelID: String
        let attemptNumber: Int // Per level, within this prototype session.
        let timestamp: Date // Wall-clock start, encoded as ISO 8601.
        let initialSimulationTime: Double // Nonzero only when resuming a run.
        var outcome = "unfinished"
        var failReason: String? = nil
        var endReason: String? = nil
        var planRealSeconds = 0.0
        var elapsedRealSeconds = 0.0
        var simulationEndTime = 0.0
        var changes = 0
        let par: Int
        var changesMinusPar = 0
        var stars: Int? = nil
        var fastForwardUseCount = 0
        /// Monotonic hold/toggle duration through outcome observation; not an
        /// inferred simulation duration or a human reaction-time measurement.
        var fastForwardRealSeconds = 0.0
        var fastForwardSimulationSeconds = 0.0
        var finalSwitchEdges: [String: String] = [:]
        var events: [Event] = []
        var omittedEventCount = 0
    }

    struct Quit: Encodable {
        let recordType = "quit_at_level"
        let schemaVersion = 1
        let sessionID: UUID
        let levelID: String?
        let timestamp: Date
        let reason: String
    }

    let sessionID = UUID() // New for each opening, never a device/player ID.
    let fileURL: URL
    private let store: Store
    private let uptime: () -> Double
    private let wallTime: () -> Date
    private var levelSessionID = UUID()
    private var lastLevelID: String?
    private var attemptNumbers: [String: Int] = [:]
    private var current: Attempt?
    private var activeEngineID: ObjectIdentifier?
    private var startedAt = 0.0
    private var planningSince: Double?
    private var acceleratingSince: (real: Double, simulation: Double)?
    private var suspended = false
    private(set) var lastAttempt: Attempt?

    init(fileURL: URL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        .appendingPathComponent("multi_van_playtest.jsonl"),
         uptime: @escaping () -> Double = { ProcessInfo.processInfo.systemUptime },
         wallTime: @escaping () -> Date = Date.init) {
        self.fileURL = fileURL
        self.store = Store(fileURL: fileURL)
        self.uptime = uptime
        self.wallTime = wallTime
    }

    func open(_ engine: MultiVanEngine) {
        guard current == nil else { return }
        levelSessionID = UUID()
        lastLevelID = engine.level.id
        suspended = false
        begin(engine, action: .levelStarted)
    }

    func begin(_ engine: MultiVanEngine, action: Action) {
        guard current == nil else { return }
        let number = (attemptNumbers[engine.level.id] ?? 0) + 1
        attemptNumbers[engine.level.id] = number
        activeEngineID = ObjectIdentifier(engine)
        startedAt = uptime()
        planningSince = engine.phase == .plan ? startedAt : nil
        acceleratingSince = nil
        current = Attempt(sessionID: sessionID, levelSessionID: levelSessionID,
                          levelID: engine.level.id, attemptNumber: number, timestamp: wallTime(),
                          initialSimulationTime: engine.runTime, par: engine.level.parChanges)
        record(action, engine: engine)
    }

    func go(_ engine: MultiVanEngine) {
        guard matches(engine), engine.phase == .plan else { return }
        if let planningSince { current?.planRealSeconds += max(0, uptime() - planningSince) }
        planningSince = nil
        record(.go, engine: engine)
    }

    /// Observe the authoritative result AFTER the existing single engine tap.
    func switchTapped(_ engine: MultiVanEngine, nodeID: String, result: MultiVanTapResult) {
        guard matches(engine) else { return }
        var event = event(.switchTap, engine: engine)
        event.nodeID = nodeID
        event.tapResult = switch result {
        case .accepted: "accepted"
        case .rejectedLocked: "rejected_locked"
        case .rejectedFrozen: "rejected_frozen"
        case .notASwitch: "not_a_switch"
        }
        event.selectedEdgeID = engine.runtimeGraph.nodesByID[nodeID]?.activeOutgoingEdgeID
        append(event)
    }

    /// Called by the existing dispatcher; never drains or mutates the engine.
    func observe(_ event: MultiVanEvent, engine: MultiVanEngine) {
        guard matches(engine) else { return }
        switch event {
        case let .delivered(vanID, _):
            var entry = self.event(.delivered, engine: engine)
            entry.vanID = vanID
            append(entry)
        case .crashed: record(.collision, engine: engine)
        case let .wrongHouse(vanID):
            var entry = self.event(.wrongHouse, engine: engine)
            entry.vanID = vanID
            append(entry)
        case .allDelivered: record(.allDelivered, engine: engine)
        case .go, .switchTapped, .tapRejected: break // Already captured at the action.
        }
    }

    func completed(_ engine: MultiVanEngine) {
        guard matches(engine), let outcome = engine.outcome, engine.phase == .finished else { return }
        switch outcome {
        case .win:
            current?.stars = MultiVanStars.rating(changes: engine.changeCount, par: engine.level.parChanges)
        case .failCrash: current?.failReason = "collision"
        case .failWrongHouse: current?.failReason = "wrong_house"
        case .failStuck: current?.failReason = "stuck"
        }
        finish(engine, outcome: outcome == .win ? "success" : "failure", action: .completed)
    }

    /// Must precede engine.stop(), which resets authoritative simulation time.
    func stop(_ engine: MultiVanEngine) {
        guard matches(engine), engine.phase == .run else { return }
        finish(engine, outcome: "stopped", action: .stop)
    }

    func record(_ action: Action, engine: MultiVanEngine) {
        guard matches(engine) else { return }
        append(event(action, engine: engine))
    }

    func speedChanged(_ enabled: Bool, engine: MultiVanEngine) {
        guard matches(engine), engine.phase == .run,
              enabled != (acceleratingSince != nil) else { return }
        settleAcceleration(engine)
        if enabled {
            acceleratingSince = (uptime(), engine.runTime)
            current?.fastForwardUseCount += 1
        }
        var entry = event(.speedChanged, engine: engine)
        entry.speedMultiplier = enabled ? engine.tuning.fastForwardMultiplier : 1
        append(entry)
    }

    func leaveLevel(_ engine: MultiVanEngine, reason: String) {
        completed(engine)
        guard matches(engine) else { return }
        current?.endReason = reason
        finish(engine, outcome: "abandoned", action: .abandoned)
    }

    func quit(engine: MultiVanEngine?, reason: String) {
        guard !suspended else { return }
        if let engine { leaveLevel(engine, reason: reason) }
        store.append(Quit(sessionID: sessionID, levelID: lastLevelID, timestamp: wallTime(), reason: reason))
        suspended = true
    }

    func resume(_ engine: MultiVanEngine?) {
        guard suspended else { return }
        suspended = false
        if let engine, engine.phase != .finished { begin(engine, action: .resume) }
    }

    // MV-44 may wait for queued writes before sharing, and report write errors.
    // Never call the blocking flush from a gameplay frame.
    func flush() { store.queue.sync {} }
    /// A queue barrier without blocking the caller (in particular, the UI).
    func flush() async {
        await withCheckedContinuation { continuation in
            store.queue.async { continuation.resume() }
        }
    }
    var writeError: String? { store.queue.sync { store.writeError } }

    enum ExportError: LocalizedError {
        case empty, writeFailed, unreadable, copyFailed

        var errorDescription: String? {
            switch self {
            case .empty: "No playtest data yet. Play a level, then try again."
            case .writeFailed: "Some playtest records could not be saved. Reopen the prototype and try again."
            case .unreadable: "The playtest log could not be read. Please try again later."
            case .copyFailed: "A sharing copy could not be created. Check available storage and try again."
            }
        }
    }

    struct LevelSummary: Identifiable {
        let id: String
        var attempts = 0
        var failReasons: [String: Int] = [:]
        var totalChangesMinusPar = 0
        var averageChangesMinusPar: Double { Double(totalChangesMinusPar) / Double(attempts) }
        var mostCommonFailReason: String {
            let reason = failReasons.keys.sorted().max { failReasons[$0, default: 0] < failReasons[$1, default: 0] }
            return reason?.replacingOccurrences(of: "_", with: " ") ?? "None"
        }
    }

    /// Ownership keeps the attachment alive until the activity controller has
    /// gone away, including cancellation. Cleanup uses the existing file queue.
    final class Export: Identifiable {
        let id = UUID()
        let fileURL: URL
        let summaries: [LevelSummary]

        init(fileURL: URL, summaries: [LevelSummary]) {
            self.fileURL = fileURL
            self.summaries = summaries
        }

        deinit {
            let directory = fileURL.deletingLastPathComponent()
            Store.fileQueue.async { try? FileManager.default.removeItem(at: directory) }
        }
    }

    func summary() async throws -> [LevelSummary] {
        await flush()
        return try await withCheckedThrowingContinuation { continuation in
            store.queue.async { [store] in
                continuation.resume(with: Result { try Self.summaries(in: store.readForExport()) })
            }
        }
    }

    /// Flush first, then read/check/copy on the SAME queue as appends. Later
    /// gameplay writes cannot change this snapshot or interleave with its read.
    func prepareExport(in directory: URL? = nil) async throws -> Export {
        try Task.checkCancellation()
        await flush()
        let export: Export = try await withCheckedThrowingContinuation { continuation in
            store.queue.async { [store] in
                continuation.resume(with: Result {
                    let data = try store.readForExport()
                    let summaries = try Self.summaries(in: data)
                    let folder = (directory ?? Store.exportDirectory).appendingPathComponent(UUID().uuidString)
                    let date = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
                    let file = folder.appendingPathComponent("Multi-Van-Playtest-\(date).jsonl")
                    do {
                        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
                        try data.write(to: file, options: .atomic)
                        return Export(fileURL: file, summaries: summaries)
                    } catch {
                        try? FileManager.default.removeItem(at: folder)
                        throw ExportError.copyFailed
                    }
                })
            }
        }
        try Task.checkCancellation()
        return export
    }

    private static func summaries(in data: Data) throws -> [LevelSummary] {
        struct Kind: Decodable { let recordType: String }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        var levels: [String: LevelSummary] = [:]
        do {
            for line in data.split(separator: 0x0A) {
                guard try decoder.decode(Kind.self, from: Data(line)).recordType == "attempt" else { continue }
                let attempt = try decoder.decode(Attempt.self, from: Data(line))
                var summary = levels[attempt.levelID] ?? LevelSummary(id: attempt.levelID)
                summary.attempts += 1
                summary.totalChangesMinusPar += attempt.changesMinusPar
                if let reason = attempt.failReason { summary.failReasons[reason, default: 0] += 1 }
                levels[attempt.levelID] = summary
            }
        } catch { throw ExportError.unreadable }
        return levels.values.sorted { $0.id < $1.id }
    }

    private func matches(_ engine: MultiVanEngine) -> Bool {
        current != nil && activeEngineID == ObjectIdentifier(engine)
    }

    private func event(_ action: Action, engine: MultiVanEngine) -> Event {
        Event(action: action, elapsedRealSeconds: max(0, uptime() - startedAt),
              observedSimulationTime: engine.runTime,
              phase: engine.phase == .plan ? "plan" : (engine.phase == .run ? "run" : "finished"))
    }

    private func append(_ event: Event) {
        // Bounded even if someone taps indefinitely. Summaries remain exact.
        if (current?.events.count ?? 0) < 1024 { current?.events.append(event) }
        else { current?.omittedEventCount += 1 }
    }

    private func settleAcceleration(_ engine: MultiVanEngine) {
        guard let acceleratingSince else { return }
        current?.fastForwardRealSeconds += max(0, uptime() - acceleratingSince.real)
        current?.fastForwardSimulationSeconds += max(0, engine.runTime - acceleratingSince.simulation)
        self.acceleratingSince = nil
    }

    private func finish(_ engine: MultiVanEngine, outcome: String, action: Action) {
        record(action, engine: engine)
        settleAcceleration(engine)
        if let planningSince { current?.planRealSeconds += max(0, uptime() - planningSince) }
        current?.elapsedRealSeconds = max(0, uptime() - startedAt)
        current?.simulationEndTime = engine.runTime
        current?.outcome = outcome
        current?.changes = engine.changeCount
        current?.changesMinusPar = engine.changeCount - engine.level.parChanges
        current?.finalSwitchEdges = engine.runtimeGraph.nodesByID.values.reduce(into: [:]) { edges, node in
            if node.outgoingEdgeIDs.count > 1 { edges[node.id] = node.activeOutgoingEdgeID }
        }
        if let current {
            lastAttempt = current
            store.append(current)
        }
        current = nil // Makes repeated completion/exit/render callbacks inert.
        planningSince = nil
    }

    // Mutable store state is confined to fileQueue, including export reads.
    private final class Store: @unchecked Sendable {
        static let fileQueue = DispatchQueue(label: "MultiVanPlaytestLog.file", qos: .utility)
        // First use in this process removes abandoned exports from a previous
        // launch. Live exports each own a unique subfolder and remove it on release.
        static let exportDirectory: URL = {
            let url = FileManager.default.temporaryDirectory.appendingPathComponent("MultiVanPlaytestExports")
            try? FileManager.default.removeItem(at: url)
            return url
        }()
        var queue: DispatchQueue { Self.fileQueue }
        let fileURL: URL
        var writeError: String?

        init(fileURL: URL) { self.fileURL = fileURL }

        func readForExport() throws -> Data {
            guard writeError == nil else { throw ExportError.writeFailed }
            guard FileManager.default.fileExists(atPath: fileURL.path) else { throw ExportError.empty }
            do {
                let data = try Data(contentsOf: fileURL)
                guard !data.isEmpty else { throw ExportError.empty }
                return data
            } catch let error as ExportError { throw error }
            catch { throw ExportError.unreadable }
        }

        func append<T: Encodable>(_ record: T) {
            queue.async { [self] in
                do {
                    let encoder = JSONEncoder()
                    encoder.dateEncodingStrategy = .iso8601
                    encoder.outputFormatting = [.sortedKeys]
                    var data = try encoder.encode(record)
                    data.append(0x0A)
                    if !FileManager.default.fileExists(atPath: fileURL.path) {
                        try Data().write(to: fileURL, options: .atomic)
                        var url = fileURL
                        var values = URLResourceValues()
                        values.isExcludedFromBackup = true
                        try url.setResourceValues(values)
                    }
                    let handle = try FileHandle(forWritingTo: fileURL)
                    defer { try? handle.close() }
                    try handle.seekToEnd()
                    try handle.write(contentsOf: data)
                } catch {
                    writeError = error.localizedDescription // Local, inspectable; no reporting/retries.
                }
            }
        }
    }
}
