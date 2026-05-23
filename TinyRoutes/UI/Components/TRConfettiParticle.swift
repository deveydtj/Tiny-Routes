import SwiftUI

enum TRConfettiMode {
    case success
    case failure
}

struct TRConfettiParticle: Identifiable, Equatable {
    enum ShapeKind: CaseIterable, Equatable {
        case rectangle
        case circle
        case diamond
    }

    let id: UUID
    let startX: CGFloat
    let startY: CGFloat
    let endX: CGFloat
    let endY: CGFloat
    let size: CGFloat
    let rotation: Double
    let colorIndex: Int
    let shape: ShapeKind
    let delay: Double
    let duration: Double
}

struct TRConfettiParticleFactory {
    func makeParticles(
        mode: TRConfettiMode,
        in containerSize: CGSize,
        reduceMotion: Bool = false,
        seed: UInt64 = 0xC0FFEE
    ) -> [TRConfettiParticle] {
        var random = TRSeededRandom(seed: seed)
        let count = particleCount(mode: mode, reduceMotion: reduceMotion)
        let paletteCount = Self.palette(for: mode).count
        let width = max(containerSize.width, 1)
        let height = max(containerSize.height, 1)

        return (0..<count).map { index in
            let start = startPoint(mode: mode, width: width, height: height, random: &random)
            let end = reduceMotion
                ? start
                : endPoint(mode: mode, start: start, width: width, height: height, random: &random)
            let size = random.next(in: sizeRange(mode: mode, reduceMotion: reduceMotion))
            let rotation = random.next(in: -180...360)
            let colorIndex = random.nextInt(upperBound: paletteCount)
            let shapeIndex = random.nextInt(upperBound: TRConfettiParticle.ShapeKind.allCases.count)
            let timing = timing(mode: mode, reduceMotion: reduceMotion, random: &random)

            return TRConfettiParticle(
                id: deterministicUUID(seed: seed, index: index),
                startX: start.x,
                startY: start.y,
                endX: end.x,
                endY: end.y,
                size: size,
                rotation: Double(rotation),
                colorIndex: colorIndex,
                shape: TRConfettiParticle.ShapeKind.allCases[shapeIndex],
                delay: timing.delay,
                duration: timing.duration
            )
        }
    }

    static func palette(for mode: TRConfettiMode) -> [Color] {
        switch mode {
        case .success:
            return [
                TRGameplayStyle.Colors.primaryBlue,
                Color(red: 0.16, green: 0.75, blue: 0.68),
                TRGameplayStyle.Colors.resultGold,
                TRGameplayStyle.Colors.resultWarningOrange,
                Color(red: 0.53, green: 0.36, blue: 0.96),
                TRGameplayStyle.Colors.successGreen
            ]
        case .failure:
            return [
                TRGameplayStyle.Colors.resultWarningOrange,
                Color(red: 0.44, green: 0.58, blue: 0.74),
                Color(red: 0.92, green: 0.94, blue: 0.98)
            ]
        }
    }

    private func particleCount(mode: TRConfettiMode, reduceMotion: Bool) -> Int {
        if reduceMotion {
            switch mode {
            case .success:
                return 7
            case .failure:
                return 1
            }
        }

        switch mode {
        case .success:
            return 48
        case .failure:
            return 12
        }
    }

    private func startPoint(
        mode: TRConfettiMode,
        width: CGFloat,
        height: CGFloat,
        random: inout TRSeededRandom
    ) -> CGPoint {
        switch mode {
        case .success:
            return CGPoint(
                x: random.next(in: (width * 0.08)...(width * 0.92)),
                y: random.next(in: (height * 0.08)...(height * 0.32))
            )
        case .failure:
            return CGPoint(
                x: random.next(in: (width * 0.38)...(width * 0.62)),
                y: random.next(in: (height * 0.12)...(height * 0.24))
            )
        }
    }

    private func endPoint(
        mode: TRConfettiMode,
        start: CGPoint,
        width: CGFloat,
        height: CGFloat,
        random: inout TRSeededRandom
    ) -> CGPoint {
        switch mode {
        case .success:
            return CGPoint(
                x: clamp(start.x + random.next(in: (-width * 0.32)...(width * 0.32)), min: -24, max: width + 24),
                y: clamp(start.y + random.next(in: (height * 0.24)...(height * 0.54)), min: 0, max: height + 40)
            )
        case .failure:
            return CGPoint(
                x: clamp(start.x + random.next(in: (-width * 0.10)...(width * 0.10)), min: 0, max: width),
                y: clamp(start.y + random.next(in: (height * 0.05)...(height * 0.16)), min: 0, max: height)
            )
        }
    }

    private func sizeRange(mode: TRConfettiMode, reduceMotion: Bool) -> ClosedRange<CGFloat> {
        if reduceMotion {
            return 5...8
        }

        switch mode {
        case .success:
            return 6...13
        case .failure:
            return 5...9
        }
    }

    private func timing(
        mode: TRConfettiMode,
        reduceMotion: Bool,
        random: inout TRSeededRandom
    ) -> (delay: Double, duration: Double) {
        if reduceMotion {
            return (0, 0)
        }

        switch mode {
        case .success:
            return (
                Double(random.next(in: 0...0.22)),
                Double(random.next(in: 1.20...1.80))
            )
        case .failure:
            return (
                Double(random.next(in: 0...0.12)),
                Double(random.next(in: 0.80...1.20))
            )
        }
    }

    private func clamp(_ value: CGFloat, min minimum: CGFloat, max maximum: CGFloat) -> CGFloat {
        Swift.min(Swift.max(value, minimum), maximum)
    }

    private func deterministicUUID(seed: UInt64, index: Int) -> UUID {
        let seedPart = UInt64(index) ^ seed
        let groupA = UInt16(truncatingIfNeeded: seedPart >> 16)
        let groupB = UInt16(truncatingIfNeeded: index)
        let tail = seedPart & 0x0000_FFFF_FFFF_FFFF
        let uuidString = String(format: "00000000-0000-%04X-%04X-%012llX", groupA, groupB, CUnsignedLongLong(tail))
        return UUID(uuidString: uuidString) ?? UUID()
    }
}

private struct TRSeededRandom {
    private var state: UInt64

    init(seed: UInt64) {
        self.state = seed == 0 ? 0xD1CE_BA5E : seed
    }

    mutating func next(in range: ClosedRange<CGFloat>) -> CGFloat {
        let lowerBound = min(range.lowerBound, range.upperBound)
        let upperBound = max(range.lowerBound, range.upperBound)
        return lowerBound + ((upperBound - lowerBound) * nextUnit())
    }

    mutating func nextInt(upperBound: Int) -> Int {
        guard upperBound > 0 else { return 0 }
        return Int(nextUnit() * CGFloat(upperBound)).clamped(to: 0...(upperBound - 1))
    }

    private mutating func nextUnit() -> CGFloat {
        state = state &* 2862933555777941757 &+ 3037000493
        let value = Double(UInt32(truncatingIfNeeded: state >> 16)) / Double(UInt32.max)
        return CGFloat(value)
    }
}

private extension Comparable {
    func clamped(to range: ClosedRange<Self>) -> Self {
        min(max(self, range.lowerBound), range.upperBound)
    }
}
