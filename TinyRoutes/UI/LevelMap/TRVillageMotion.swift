import Foundation

/// Moves the village map's camera: straight from a finger's drag, eased along the
/// road on a drive to a house, or settling into a house on a critically damped
/// spring after a flick. The page reads it every frame while it moves, and the
/// van's speed is measured from those reads.
final class TRVillageMotion {
    private enum Move {
        case none
        case ease(from: Double, to: Double, start: TimeInterval, duration: TimeInterval)
        case spring(from: Double, velocity: Double, to: Double, start: TimeInterval)
    }

    /// The spring's natural frequency, a second.
    static let springRate = 9.0
    /// Long enough for the spring to come to rest from the fastest flick.
    static let springDuration = 1.5

    private var move = Move.none
    private var resting: Double
    private var lastRead: (time: TimeInterval, vanY: Double)?
    /// The van's speed along the road, units a second, smoothed.
    private(set) var vanSpeed = 0.0
    /// How much of the Drive chip shows, easing in and out.
    private(set) var chip = 0.0
    /// Whether the van was last going back down the road, for a replay.
    private(set) var isReversing = false
    private var showsChip = false
    private var slowSince: TimeInterval?

    /// Above this speed the chip comes up, and the van's direction counts.
    static let chipShowSpeed = 110.0
    /// Below this speed for `chipHoldTime`, the chip goes. Between the two it
    /// stays as it was, so a slow, uneven drag doesn't flick it on and off.
    static let chipHideSpeed = 40.0
    static let chipHoldTime = 0.3

    init(camera: Double) {
        resting = camera
    }

    /// Where the camera is at `time`.
    func camera(at time: TimeInterval) -> Double {
        switch move {
        case .none:
            return resting
        case let .ease(from, to, start, duration):
            let t = min(max((time - start) / duration, 0), 1)
            let eased = t < 0.5 ? 4 * t * t * t : 1 - pow(-2 * t + 2, 3) / 2
            if t >= 1 { settle(at: to) }
            return from + (to - from) * eased
        case let .spring(from, velocity, to, start):
            let t = max(time - start, 0)
            let rate = Self.springRate
            let offset = from - to
            if t >= Self.springDuration {
                settle(at: to)
                return to
            }
            return to + (offset + (velocity + rate * offset) * t) * exp(-rate * t)
        }
    }

    /// Where the camera is headed.
    var target: Double {
        switch move {
        case .none: resting
        case let .ease(_, to, _, _): to
        case let .spring(_, _, to, _): to
        }
    }

    /// Holds the camera at `camera`, stopping any move.
    func hold(at camera: Double) {
        settle(at: camera)
    }

    /// Drives along the road to `camera` over `duration` seconds.
    func ease(to camera: Double, at time: TimeInterval, duration: TimeInterval) {
        let from = self.camera(at: time)
        guard duration > 0, abs(camera - from) > 0.01 else { return settle(at: camera) }
        move = .ease(from: from, to: camera, start: time, duration: duration)
    }

    /// Lets the camera, going `velocity` units a second, spring into `camera`.
    func spring(to camera: Double, velocity: Double, at time: TimeInterval) {
        let from = self.camera(at: time)
        move = .spring(from: from, velocity: velocity, to: camera, start: time)
    }

    /// Notes where the van was drawn at `time`, for its speed and the chip.
    func noteVan(atY vanY: Double, time: TimeInterval) {
        defer { lastRead = (time, vanY) }
        guard let lastRead else { return }
        let dt = time - lastRead.time
        guard dt > 0.0005 else { return }
        // Smoothed over about a tenth of a second, whatever the frame rate.
        let blend = 1 - exp(-dt / 0.1)
        vanSpeed += ((vanY - lastRead.vanY) / dt - vanSpeed) * blend
        if abs(vanSpeed) < 2 { vanSpeed = 0 }

        let speed = abs(vanSpeed)
        if speed > Self.chipShowSpeed {
            showsChip = true
            isReversing = vanSpeed < 0
            slowSince = nil
        } else if speed < Self.chipHideSpeed {
            let since = slowSince ?? time
            slowSince = since
            if time - since >= Self.chipHoldTime { showsChip = false }
        } else {
            slowSince = nil
        }
        // In quickly, out gently.
        let step = min(dt, 0.1)
        chip = showsChip ? min(1, chip + step / 0.15) : max(0, chip - step / 0.3)
    }

    /// Forgets the van's speed, once the map has stopped drawing frames.
    func park() {
        vanSpeed = 0
        chip = 0
        showsChip = false
        slowSince = nil
        lastRead = nil
    }

    private func settle(at camera: Double) {
        move = .none
        resting = camera
    }
}
