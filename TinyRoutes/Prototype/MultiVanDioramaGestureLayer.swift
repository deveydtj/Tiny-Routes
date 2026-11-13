import SwiftUI
import UIKit

/// Reads the player's fingers over the diorama the way Apple and Google Maps do,
/// and writes the result into `orbit`:
///
/// - One finger, zoomed in: pans, and glides on after a flick.
/// - One finger at the full view: turns the table, as before (nothing to pan to).
/// - Two fingers: pinch zooms towards them while their midpoint pans; a twist
///   turns the table; sliding both up or down tilts it.
/// - Double tap: straightens the table. Two-finger tap: zooms out.
/// - A tap that moves nothing reports a miss, for the tutorial.
///
/// SwiftUI's gestures can't follow a pinch's midpoint or tell a tilt from a
/// pinch, so this is UIKit. One pan recognizer takes one or two fingers and
/// starts afresh whenever a finger lands or lifts, so moving between one and two
/// fingers never jumps. The switch buttons sit above it and keep their taps.
struct MultiVanDioramaGestureLayer: UIViewRepresentable {
    @Binding var orbit: MultiVanDioramaOrbit
    var animates = true
    /// A single tap, or a double tap on a table that's already straight.
    var onMissedTap: (() -> Void)? = nil

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIView(context: Context) -> TouchView {
        let view = TouchView()
        view.backgroundColor = .clear
        view.isMultipleTouchEnabled = true
        view.accessibilityElementsHidden = true
        let coordinator = context.coordinator
        view.onTouchDown = { [weak coordinator] in coordinator?.stopGliding() }

        let pan = UIPanGestureRecognizer(target: coordinator, action: #selector(Coordinator.pan(_:)))
        pan.minimumNumberOfTouches = 1
        pan.maximumNumberOfTouches = 2
        view.addGestureRecognizer(pan)

        let doubleTap = UITapGestureRecognizer(target: coordinator, action: #selector(Coordinator.doubleTap(_:)))
        doubleTap.numberOfTapsRequired = 2
        view.addGestureRecognizer(doubleTap)

        let tap = UITapGestureRecognizer(target: coordinator, action: #selector(Coordinator.tap(_:)))
        tap.require(toFail: doubleTap)
        view.addGestureRecognizer(tap)

        let twoFingerTap = UITapGestureRecognizer(target: coordinator, action: #selector(Coordinator.twoFingerTap(_:)))
        twoFingerTap.numberOfTouchesRequired = 2
        view.addGestureRecognizer(twoFingerTap)
        return view
    }

    func updateUIView(_ view: TouchView, context: Context) {
        context.coordinator.layer = self
    }

    static func dismantleUIView(_ view: TouchView, coordinator: Coordinator) {
        coordinator.stopGliding()
    }

    /// Tells the coordinator the moment a finger lands, before the pan
    /// recognizer has seen enough movement to begin, so a glide stops under it.
    final class TouchView: UIView {
        var onTouchDown: () -> Void = {}

        override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
            onTouchDown()
            super.touchesBegan(touches, with: event)
        }
    }

    @MainActor
    final class Coordinator: NSObject {
        var layer: MultiVanDioramaGestureLayer

        /// Points two fingers travel before they count as a pinch, twist or tilt.
        static let decisionDistance: CGFloat = 10
        /// A twist under this many radians is taken as part of a pinch, as in Maps.
        static let twistThreshold = 0.17
        /// The share of a glide's speed left after a millisecond; UIScrollView's normal rate.
        static let glideDecay = 0.998
        /// Points per second below which a glide stops.
        static let glideStopSpeed = 12.0

        private enum OneFinger { case pan, turn }
        private enum TwoFingers { case undecided, transform, tilt }

        private var oneFinger = OneFinger.turn
        private var twoFingers = TwoFingers.undecided
        /// Where the fingers were at the last step, and when the current count of them landed.
        private var last: [CGPoint] = []
        private var start: [CGPoint] = []
        private var twist = 0.0
        private var twistEngaged = false

        private var glide: CADisplayLink?
        private var glideVelocity = CGVector.zero
        private var glideSize = CGSize.zero
        private var glideTimestamp: CFTimeInterval?

        init(_ layer: MultiVanDioramaGestureLayer) {
            self.layer = layer
        }

        private var orbit: MultiVanDioramaOrbit {
            get { layer.orbit }
            set { if newValue != layer.orbit { layer.orbit = newValue } }
        }

        // MARK: Pan, pinch, twist, tilt

        @objc func pan(_ recognizer: UIPanGestureRecognizer) {
            guard let view = recognizer.view else { return }
            switch recognizer.state {
            case .began:
                stopGliding()
                restart(recognizer, in: view)
            case .changed:
                let touches = Self.touches(of: recognizer, in: view)
                guard touches.count == last.count else {
                    restart(recognizer, in: view)
                    return
                }
                switch touches.count {
                case 1: stepOneFinger(to: touches[0], size: view.bounds.size)
                case 2: stepTwoFingers(to: touches, size: view.bounds.size)
                default: break
                }
            case .ended:
                if last.count == 1, oneFinger == .pan, orbit.isZoomedIn, layer.animates {
                    let velocity = recognizer.velocity(in: view)
                    startGliding(CGVector(dx: velocity.x, dy: velocity.y), size: view.bounds.size)
                }
                last = []
            default:
                last = []
            }
        }

        /// Starts reading afresh from where the fingers are now.
        private func restart(_ recognizer: UIPanGestureRecognizer, in view: UIView) {
            last = Self.touches(of: recognizer, in: view)
            start = last
            oneFinger = orbit.isZoomedIn ? .pan : .turn
            twoFingers = .undecided
            twist = 0
            twistEngaged = false
        }

        private func stepOneFinger(to touch: CGPoint, size: CGSize) {
            let delta = CGSize(width: touch.x - last[0].x, height: touch.y - last[0].y)
            last = [touch]
            orbit = oneFinger == .pan ? orbit.panned(by: delta, in: size) : orbit.dragged(by: delta)
        }

        private func stepTwoFingers(to touches: [CGPoint], size: CGSize) {
            if twoFingers == .undecided {
                // Hold the movement back until it's clear what the fingers mean,
                // then play all of it, so nothing is lost to the decision.
                guard let mode = Self.decide(from: start, to: touches) else { return }
                twoFingers = mode
            }
            let (a0, b0) = (last[0], last[1])
            let (a1, b1) = (touches[0], touches[1])
            last = touches
            var next = orbit
            switch twoFingers {
            case .tilt:
                next = next.tilted(by: ((a1.y - a0.y) + (b1.y - b0.y)) / 2)
            case .transform:
                let before = Self.midpoint(a0, b0), after = Self.midpoint(a1, b1)
                // Carry the spot under the fingers along with them, then zoom about it.
                next = next.panned(by: CGSize(width: after.x - before.x, height: after.y - before.y), in: size)
                let spread0 = Self.distance(a0, b0), spread1 = Self.distance(a1, b1)
                if spread0 > 1, spread1 > 1, size.width > 0, size.height > 0 {
                    let anchor = CGPoint(x: after.x / size.width, y: after.y / size.height)
                    next = next.pinched(by: spread1 / spread0, anchor: anchor, in: size)
                }
                let turn = Self.angleBetween(Self.angle(a0, b0), Self.angle(a1, b1))
                twist += turn
                if twistEngaged {
                    next = next.twisted(by: turn)
                } else if abs(twist) > Self.twistThreshold {
                    twistEngaged = true
                    next = next.twisted(by: twist - Self.twistThreshold * (twist > 0 ? 1 : -1))
                }
            case .undecided:
                break
            }
            orbit = next
        }

        /// A tilt is both fingers sliding the same way up or down, mostly
        /// vertically, without spreading; anything else pinches, pans and twists.
        /// Nil until the fingers have moved far enough to tell.
        private static func decide(from start: [CGPoint], to touches: [CGPoint]) -> TwoFingers? {
            guard start.count == 2, touches.count == 2 else { return nil }
            let a = CGVector(dx: touches[0].x - start[0].x, dy: touches[0].y - start[0].y)
            let b = CGVector(dx: touches[1].x - start[1].x, dy: touches[1].y - start[1].y)
            guard max(hypot(a.dx, a.dy), hypot(b.dx, b.dy)) >= decisionDistance else { return nil }
            let spreadChange = abs(distance(touches[0], touches[1]) - distance(start[0], start[1]))
            let together = a.dy * b.dy > 0
            let vertical = abs(a.dx) < abs(a.dy) * 0.7 && abs(b.dx) < abs(b.dy) * 0.7
            let steady = spreadChange < decisionDistance
            return together && vertical && steady ? .tilt : .transform
        }

        // MARK: Taps

        @objc func tap(_ recognizer: UITapGestureRecognizer) {
            layer.onMissedTap?()
        }

        @objc func doubleTap(_ recognizer: UITapGestureRecognizer) {
            stopGliding()
            guard orbit != .resting else {
                layer.onMissedTap?()
                return
            }
            withAnimation(layer.animates ? .smooth(duration: 0.45) : nil) { orbit = .resting }
        }

        @objc func twoFingerTap(_ recognizer: UITapGestureRecognizer) {
            guard let view = recognizer.view, view.bounds.width > 0, view.bounds.height > 0 else { return }
            stopGliding()
            let point = recognizer.location(in: view)
            let anchor = CGPoint(x: point.x / view.bounds.width, y: point.y / view.bounds.height)
            let zoomedOut = orbit.pinched(by: 0.5, anchor: anchor, in: view.bounds.size)
            withAnimation(layer.animates ? .smooth(duration: 0.35) : nil) { orbit = zoomedOut }
        }

        // MARK: Glide

        private func startGliding(_ velocity: CGVector, size: CGSize) {
            stopGliding()
            guard hypot(velocity.dx, velocity.dy) > Self.glideStopSpeed else { return }
            glideVelocity = velocity
            glideSize = size
            glideTimestamp = nil
            let link = CADisplayLink(target: self, selector: #selector(stepGlide(_:)))
            link.add(to: .main, forMode: .common)
            glide = link
        }

        func stopGliding() {
            glide?.invalidate()
            glide = nil
        }

        @objc private func stepGlide(_ link: CADisplayLink) {
            defer { glideTimestamp = link.timestamp }
            guard let previous = glideTimestamp else { return }
            let elapsed = min(link.timestamp - previous, 0.05)
            let delta = CGSize(width: glideVelocity.dx * elapsed, height: glideVelocity.dy * elapsed)
            let before = orbit
            let after = before.panned(by: delta, in: glideSize)
            orbit = after
            // An edge stops the glide along it.
            if after.zoomCentre.x == before.zoomCentre.x { glideVelocity.dx = 0 }
            if after.zoomCentre.y == before.zoomCentre.y { glideVelocity.dy = 0 }
            let decay = pow(Self.glideDecay, elapsed * 1000)
            glideVelocity = CGVector(dx: glideVelocity.dx * decay, dy: glideVelocity.dy * decay)
            if hypot(glideVelocity.dx, glideVelocity.dy) < Self.glideStopSpeed || !after.isZoomedIn {
                stopGliding()
            }
        }

        // MARK: Geometry

        private static func touches(of recognizer: UIPanGestureRecognizer, in view: UIView) -> [CGPoint] {
            (0..<min(recognizer.numberOfTouches, 2)).map { recognizer.location(ofTouch: $0, in: view) }
        }

        static func midpoint(_ a: CGPoint, _ b: CGPoint) -> CGPoint {
            CGPoint(x: (a.x + b.x) / 2, y: (a.y + b.y) / 2)
        }

        static func distance(_ a: CGPoint, _ b: CGPoint) -> CGFloat {
            hypot(b.x - a.x, b.y - a.y)
        }

        /// The line from `a` to `b`, in radians clockwise from the right, as UIKit's y runs down.
        static func angle(_ a: CGPoint, _ b: CGPoint) -> Double {
            atan2(Double(b.y - a.y), Double(b.x - a.x))
        }

        /// The turn from `from` to `to`, the short way round.
        static func angleBetween(_ from: Double, _ to: Double) -> Double {
            var turn = to - from
            while turn > .pi { turn -= 2 * .pi }
            while turn < -.pi { turn += 2 * .pi }
            return turn
        }
    }
}
