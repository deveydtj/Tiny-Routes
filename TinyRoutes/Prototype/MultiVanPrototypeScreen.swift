#if DEBUG || MULTIVAN_INTERNAL
import SwiftUI
import UIKit

struct MultiVanPrototypeScreen: View {
    @ObservedObject var settingsService: UserSettingsService
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var scenePhase
    @State private var levels: [MultiVanLevel] = []
    // Autoplay's robot attempts go to their own log, away from playtesters'.
    @State private var session = MultiVanAutoplay.launchConfiguration == nil
        ? MultiVanPrototypeSession()
        : MultiVanPrototypeSession(playtestLog: MultiVanPlaytestLog(
            fileURL: FileManager.default.temporaryDirectory.appendingPathComponent("multi_van_autoplay.jsonl")))
    #if DEBUG
    @State private var tuning = MultiVanPrototypeTuning().tuning
    #endif
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                if let engine = session.engine {
                    VStack(spacing: 0) {
                        #if DEBUG
                        Text(MultiVanPrototypeTuning.isDefault(engine.tuning) ? "Default tuning" : "Experimental tuning")
                            .font(.caption.bold())
                            .padding(.vertical, 4)
                        #else
                        Text("Default tuning · Speed 1.50 · Collision 0.35 · Lock 0.40")
                            .font(.caption.bold())
                            .multilineTextAlignment(.center)
                            .padding(.vertical, 4)
                        #endif
                        MultiVanGameplayScreen(engine: engine, settingsService: settingsService, onNext: {
                            perform { try session.next(in: levels) }
                        }, playtestLog: session.playtestLog, autoplay: MultiVanAutoplay.launchConfiguration)
                    }
                    // Reset all view-local state as well as the engine on Next.
                    .id(ObjectIdentifier(engine))
                } else {
                    List {
                        #if DEBUG
                        NavigationLink {
                            MultiVanTuningScreen(store: session.tuningOverrides, tuning: $tuning)
                        } label: {
                            Label(MultiVanPrototypeTuning.isDefault(tuning) ? "Tuning · Defaults" : "Tuning · Experimental", systemImage: "gearshape")
                        }
                        #else
                        Text("Default tuning · Speed 1.50 · Collision 0.35 · Lock 0.40")
                            .font(.caption)
                        #endif
                        NavigationLink {
                            MultiVanPlaytestLogScreen(log: session.playtestLog)
                        } label: {
                            Label("Playtest log", systemImage: "doc.text")
                        }
                        if let errorMessage {
                            Text("Could not open prototype: \(errorMessage)")
                        } else if levels.isEmpty {
                            Text("No prototype levels are available in this build.")
                        }
                        ForEach(levels, id: \.id) { level in
                            Button {
                                perform { try session.open(level) }
                            } label: {
                                VStack(alignment: .leading) {
                                    Text(level.name)
                                        .font(.headline)
                                    Text(level.id)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                .frame(minHeight: 44)
                            }
                            .accessibilityElement(children: .ignore)
                            .accessibilityLabel("Level \((levels.firstIndex { $0.id == level.id } ?? 0) + 1): \(level.name)")
                            .accessibilityHint("Open level for planning")
                        }
                    }
                }
            }
            .navigationTitle("Multi-Van Prototype")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if session.engine != nil {
                        Button("Levels") { session.returnToList() }
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") {
                        session.playtestLog.quit(engine: session.engine, reason: "prototype_closed")
                        dismiss()
                    }
                }
            }
        }
        // The presenting menu uses black text; native prototype screens must
        // adapt their labels and controls to the device's appearance instead.
        .foregroundColor(.primary)
        .tint(.blue)
        .task {
            perform { levels = try MultiVanLevelRepository().loadAllLevels() }
            if let autoplay = MultiVanAutoplay.launchConfiguration {
                guard let level = levels.first(where: { $0.id == autoplay.levelID }) else {
                    errorMessage = "Autoplay level \(autoplay.levelID) isn't in this build."
                    return
                }
                // A profiling run outlasts the auto-lock.
                UIApplication.shared.isIdleTimerDisabled = true
                MultiVanPerformanceMeter.shared?.start()
                perform { try session.open(level) }
            }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background {
                session.playtestLog.quit(engine: session.engine, reason: "background")
            } else if phase == .active {
                session.playtestLog.resume(session.engine)
            }
        }
        .onDisappear {
            session.playtestLog.quit(engine: session.engine, reason: "prototype_dismissed")
            UIApplication.shared.isIdleTimerDisabled = false
        }
    }

    private func perform(_ action: () throws -> Void) {
        do {
            try action()
            errorMessage = nil
        } catch {
            session.returnToList()
            errorMessage = error.localizedDescription
        }
    }
}

#if DEBUG
private struct MultiVanTuningScreen: View {
    let store: MultiVanPrototypeTuning
    @Binding var tuning: MultiVanTuning

    var body: some View {
        Form {
            Section {
                Text(MultiVanPrototypeTuning.isDefault(tuning) ? "Default configuration" : "Experimental configuration")
                    .font(.headline)
            } footer: {
                Text("Saved on this device. Changes apply the next time a level opens, including Next. Retry and Replay keep that level's configuration. Fast-forward stays at 2×.")
            }
            Section("Gameplay tuning") {
                ForEach(MultiVanPrototypeTuning.Parameter.allCases, id: \.self) { parameter in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(parameter.label).font(.headline)
                        Text("\(tuning[keyPath: parameter.keyPath], specifier: "%.2f") \(parameter.units)")
                            .monospacedDigit()
                        Slider(value: Binding(
                            get: { tuning[keyPath: parameter.keyPath] },
                            set: { value in
                                store.set(value, for: parameter)
                                tuning = store.tuning
                            }
                        ), in: parameter.range, step: parameter.step)
                        .accessibilityLabel(parameter.label)
                        .accessibilityValue("\(tuning[keyPath: parameter.keyPath], specifier: "%.2f") \(parameter.units)")
                        Text("Default: \(parameter.defaultValue, specifier: "%.2f") · Range: \(parameter.range.lowerBound, specifier: "%.2f")–\(parameter.range.upperBound, specifier: "%.2f") \(parameter.units)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 4)
                }
            }
            Section {
                Button("Reset to defaults") {
                    store.reset()
                    tuning = store.tuning
                }
                .accessibilityHint("Restore all three tuning values for the next level opened")
            } footer: {
                Text("Experimental tuning is not included in the playtest log. Record the configuration separately when comparing playtests.")
            }
        }
        .navigationTitle("Prototype tuning")
    }
}
#endif

private struct MultiVanPlaytestLogScreen: View {
    let log: MultiVanPlaytestLog
    @State private var summaries: [MultiVanPlaytestLog.LevelSummary] = []
    @State private var boards: [MultiVanPlaytestLog.BoardSummary] = []
    @State private var summaryMessage: String?
    @State private var isLoading = true
    @State private var isPreparing = false
    @State private var export: MultiVanPlaytestLog.Export?
    @State private var errorMessage: String?

    var body: some View {
        List {
            Section {
                Button {
                    guard !isPreparing, export == nil else { return }
                    isPreparing = true
                } label: {
                    Label("Share Playtest Log", systemImage: "square.and.arrow.up")
                }
                .accessibilityLabel("Share Playtest Log")
                .accessibilityHint("Choose where to share a copy of your local playtest log")
                .disabled(isLoading || isPreparing || export != nil)
                if isLoading || isPreparing {
                    ProgressView(isPreparing ? "Preparing log…" : "Reading log…")
                }
            } footer: {
                Text("Logs stay on this iPhone until you choose to share them. The attachment is a JSON Lines (.jsonl) file.")
            }
            if !boards.isEmpty {
                Section {
                    ForEach(boards) { board in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(board.id == MultiVanBoardStyle.diorama.rawValue ? "3D Diorama" : "2D Map").font(.headline)
                            Text("Attempts: \(board.attempts), wins: \(board.wins)")
                            if let median = board.medianSecondsToFirstGo {
                                Text("Median time to first Go: \(median, specifier: "%.1f") s over \(board.secondsToFirstGo.count) levels")
                            }
                        }
                    }
                } header: {
                    Text("Per-board summary")
                } footer: {
                    Text("Time to first Go counts a level's first attempt when the board didn't change before Go. Levels differ, so compare boards on the same levels using the shared log.")
                }
            }
            Section("Per-level summary") {
                if let summaryMessage { Text(summaryMessage) }
                ForEach(summaries) { summary in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(summary.id).font(.headline)
                        Text("Attempts: \(summary.attempts)")
                        Text("Most common fail reason: \(summary.mostCommonFailReason)")
                        Text("Average changes vs par: \(summary.averageChangesMinusPar, specifier: "%+.1f")")
                    }
                }
            }
        }
        .navigationTitle("Playtest log")
        .task {
            isLoading = true
            defer { isLoading = false }
            do {
                let result = try await log.summary()
                let boardResult = try await log.boardSummary()
                try Task.checkCancellation()
                summaries = result
                boards = boardResult
                summaryMessage = result.isEmpty ? "No level attempts recorded yet." : nil
            } catch is CancellationError {
                return
            } catch {
                summaryMessage = error.localizedDescription
            }
        }
        // SwiftUI cancels preparation when this screen disappears. A cancelled
        // result releases its temporary file without presenting a share sheet.
        .task(id: isPreparing) {
            guard isPreparing else { return }
            defer { isPreparing = false }
            do {
                let prepared = try await log.prepareExport()
                try Task.checkCancellation()
                summaries = prepared.summaries
                summaryMessage = prepared.summaries.isEmpty ? "No level attempts recorded yet." : nil
                export = prepared
            } catch is CancellationError {
                return
            } catch {
                errorMessage = error.localizedDescription
            }
        }
        .sheet(item: $export) { prepared in
            MultiVanPlaytestActivitySheet(export: prepared)
        }
        .alert("Playtest log", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
    }
}

private struct MultiVanPlaytestActivitySheet: UIViewControllerRepresentable {
    let export: MultiVanPlaytestLog.Export
    @Environment(\.dismiss) private var dismiss

    // Retain the file for the full activity-controller lifetime, even if the
    // presenting SwiftUI screen disappears. Completion/cancellation is normal;
    // neither reports success nor changes the logger.
    final class Coordinator {
        let export: MultiVanPlaytestLog.Export
        init(export: MultiVanPlaytestLog.Export) { self.export = export }
    }

    func makeCoordinator() -> Coordinator { Coordinator(export: export) }

    func makeUIViewController(context: Context) -> UIActivityViewController {
        let controller = UIActivityViewController(activityItems: [export.fileURL], applicationActivities: nil)
        controller.completionWithItemsHandler = { [dismiss] _, _, _, _ in
            DispatchQueue.main.async { dismiss() }
        }
        return controller
    }

    func updateUIViewController(_ controller: UIActivityViewController, context: Context) {}
}

/// Presentation-local state; no production navigation or saved progress.
struct MultiVanPrototypeSession {
    private(set) var engine: MultiVanEngine?
    let playtestLog: MultiVanPlaytestLog
    #if DEBUG
    let tuningOverrides: MultiVanPrototypeTuning

    init(playtestLog: MultiVanPlaytestLog = MultiVanPlaytestLog(), tuningOverrides: MultiVanPrototypeTuning = MultiVanPrototypeTuning()) {
        self.playtestLog = playtestLog
        self.tuningOverrides = tuningOverrides
    }
    #else
    init(playtestLog: MultiVanPlaytestLog = MultiVanPlaytestLog()) {
        self.playtestLog = playtestLog
    }
    #endif

    mutating func open(_ level: MultiVanLevel) throws {
        #if DEBUG
        let nextEngine = try MultiVanEngine(level: level, tuning: tuningOverrides.tuning)
        #else
        let nextEngine = try MultiVanEngine(level: level, tuning: .default)
        #endif
        if let engine { playtestLog.leaveLevel(engine, reason: "level_changed") }
        engine = nextEngine
        playtestLog.open(nextEngine)
    }

    /// Levels come from the repository in ID order. Replace, rather than stack,
    /// gameplay so Back always returns directly to the list.
    mutating func next(in levels: [MultiVanLevel]) throws {
        guard let engine,
              let index = levels.firstIndex(where: { $0.id == engine.level.id }),
              index + 1 < levels.count else {
            returnToList()
            return
        }
        try open(levels[index + 1])
    }

    mutating func returnToList() {
        if let engine { playtestLog.leaveLevel(engine, reason: "level_list") }
        engine = nil
    }
}
#endif
