#if DEBUG || MULTIVAN_INTERNAL
import QuartzCore
import SceneKit
import UIKit

/// Frame and device numbers for an autoplay run, for devices Instruments can't
/// reach: `devicectl` copies `Documents/multi_van_performance.jsonl` over Wi-Fi.
/// It runs only with autoplay and starts a fresh file on each launch.
///
/// Every 10 s, and whenever the board or phase changes, it writes one `frames` row
/// per clock: `main` is a display link on the main thread, so it shows SwiftUI and
/// engine stalls on both boards; `scenekit` is the diorama's own render callback.
/// SceneKit only draws when something moves, so its gaps aren't all drops. Every
/// 30 s it writes a `device` row with the thermal state and battery level.
final class MultiVanPerformanceMeter: NSObject, SCNSceneRendererDelegate, @unchecked Sendable {
    static let shared: MultiVanPerformanceMeter? = MultiVanAutoplay.launchConfiguration == nil
        ? nil : MultiVanPerformanceMeter()
    static let fileName = "multi_van_performance.jsonl"
    static let window = 10.0
    static let deviceInterval = 30.0

    /// Intervals between frames on one clock.
    struct FrameStats: Equatable {
        private(set) var intervals: [Double] = []

        mutating func add(_ interval: Double) {
            guard interval > 0, interval.isFinite else { return }
            intervals.append(interval)
        }

        var frames: Int { intervals.count }
        var seconds: Double { intervals.reduce(0, +) }
        var framesPerSecond: Double { seconds > 0 ? Double(frames) / seconds : 0 }

        /// Frames that arrived more than one and a half refreshes after the last.
        func hitches(refresh: Double) -> Int {
            intervals.filter { $0 > refresh * 1.5 }.count
        }

        /// Nearest-rank percentile, in seconds; 0 with no frames.
        func percentile(_ fraction: Double) -> Double {
            guard !intervals.isEmpty else { return 0 }
            let sorted = intervals.sorted()
            let rank = Int((fraction * Double(sorted.count)).rounded(.up)) - 1
            return sorted[min(max(rank, 0), sorted.count - 1)]
        }
    }

    struct FramesRow: Encodable, Equatable {
        var recordType = "frames"
        let source: String
        let label: String
        let uptime: Double
        let seconds: Double
        let frames: Int
        let fps: Double
        let hitches: Int
        let p50Milliseconds: Double
        let p95Milliseconds: Double
        let maxMilliseconds: Double

        init(source: String, label: String, uptime: Double, stats: FrameStats, refresh: Double) {
            self.source = source
            self.label = label
            self.uptime = uptime
            seconds = stats.seconds
            frames = stats.frames
            fps = stats.framesPerSecond
            hitches = stats.hitches(refresh: refresh)
            p50Milliseconds = stats.percentile(0.5) * 1000
            p95Milliseconds = stats.percentile(0.95) * 1000
            maxMilliseconds = stats.percentile(1) * 1000
        }
    }

    /// What autoplay is doing, written only when it changes.
    struct AutoplayRow: Encodable {
        var recordType = "autoplay"
        let label: String
        let uptime: Double
        let status: String
    }

    struct DeviceRow: Encodable {
        var recordType = "device"
        let label: String
        let uptime: Double
        let thermalState: String
        let batteryLevel: Float
        let batteryState: String
        let isLowPowerMode: Bool
        /// Shows whether something covered or backgrounded the app mid-run.
        let applicationState: String
    }

    let fileURL: URL
    private let queue = DispatchQueue(label: "MultiVanPerformanceMeter.file", qos: .utility)
    // Main thread only.
    private var displayLink: CADisplayLink?
    private var lastTick: CFTimeInterval?
    private var refresh = 1.0 / 60
    private var main = FrameStats()
    private var label = "starting"
    private var windowStart = 0.0
    private var lastDeviceRow = -Double.infinity
    private var lastAutoplayStatus: String?
    // SceneKit's render thread writes these; the main thread reads them under the lock.
    private let lock = NSLock()
    private var scene = FrameStats()
    private var lastRender: TimeInterval?

    init(fileURL: URL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        .appendingPathComponent(MultiVanPerformanceMeter.fileName)) {
        self.fileURL = fileURL
    }

    /// Starts a fresh file and the main-thread clock. Calling it again does nothing.
    @MainActor
    func start() {
        guard displayLink == nil else { return }
        queue.async { [fileURL] in try? Data().write(to: fileURL, options: .atomic) }
        UIDevice.current.isBatteryMonitoringEnabled = true
        windowStart = CACurrentMediaTime()
        let link = CADisplayLink(target: self, selector: #selector(tick(_:)))
        link.add(to: .main, forMode: .common)
        displayLink = link
    }

    /// The board and phase on screen, such as "diorama run". A change closes the
    /// current window so no row mixes two of them.
    @MainActor
    func mark(_ label: String) {
        guard label != self.label else { return }
        flush(at: CACurrentMediaTime())
        self.label = label
        lock.withLock { lastRender = nil }
        lastTick = nil
    }

    /// Autoplay's presses, every one, and why it's waiting when that changes, so a
    /// stalled run explains itself.
    @MainActor
    func autoplay(_ status: String, isPress: Bool = false) {
        guard isPress || status != lastAutoplayStatus else { return }
        lastAutoplayStatus = status
        append(AutoplayRow(label: label, uptime: CACurrentMediaTime(), status: status))
    }

    @MainActor @objc private func tick(_ link: CADisplayLink) {
        if let lastTick { main.add(link.timestamp - lastTick) }
        lastTick = link.timestamp
        if link.duration > 0 { refresh = link.duration }
        let now = CACurrentMediaTime()
        if now - lastDeviceRow >= Self.deviceInterval {
            lastDeviceRow = now
            writeDeviceRow(at: now)
        }
        if now - windowStart >= Self.window { flush(at: now) }
    }

    nonisolated func renderer(_ renderer: SCNSceneRenderer, didRenderScene scene: SCNScene, atTime time: TimeInterval) {
        lock.withLock {
            if let lastRender { self.scene.add(time - lastRender) }
            lastRender = time
        }
    }

    @MainActor
    private func flush(at now: Double) {
        let scene = lock.withLock {
            defer { self.scene = FrameStats() }
            return self.scene
        }
        var rows: [FramesRow] = []
        if main.frames > 0 { rows.append(FramesRow(source: "main", label: label, uptime: now, stats: main, refresh: refresh)) }
        if scene.frames > 0 { rows.append(FramesRow(source: "scenekit", label: label, uptime: now, stats: scene, refresh: refresh)) }
        main = FrameStats()
        windowStart = now
        rows.forEach(append)
    }

    @MainActor
    private func writeDeviceRow(at now: Double) {
        let device = UIDevice.current
        let thermalState: String = switch ProcessInfo.processInfo.thermalState {
        case .nominal: "nominal"
        case .fair: "fair"
        case .serious: "serious"
        case .critical: "critical"
        @unknown default: "unknown"
        }
        let batteryState: String = switch device.batteryState {
        case .unplugged: "unplugged"
        case .charging: "charging"
        case .full: "full"
        case .unknown: "unknown"
        @unknown default: "unknown"
        }
        let applicationState = switch UIApplication.shared.applicationState {
        case .active: "active"
        case .inactive: "inactive"
        case .background: "background"
        @unknown default: "unknown"
        }
        append(DeviceRow(
            label: label, uptime: now, thermalState: thermalState, batteryLevel: device.batteryLevel,
            batteryState: batteryState, isLowPowerMode: ProcessInfo.processInfo.isLowPowerModeEnabled,
            applicationState: applicationState
        ))
    }

    private func append<Row: Encodable>(_ row: Row) {
        guard var data = try? JSONEncoder().encode(row) else { return }
        data.append(0x0A)
        queue.async { [fileURL] in
            guard let handle = try? FileHandle(forWritingTo: fileURL) else { return }
            defer { try? handle.close() }
            _ = try? handle.seekToEnd()
            try? handle.write(contentsOf: data)
        }
    }
}
#endif
