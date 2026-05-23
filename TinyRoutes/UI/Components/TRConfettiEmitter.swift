import SwiftUI

struct TRConfettiEmitter: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    let mode: TRConfettiMode
    var seed: UInt64 = 0xC0FFEE

    @State private var particles: [TRConfettiParticle] = []
    @State private var isActive = false

    private let factory = TRConfettiParticleFactory()

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .topLeading) {
                ForEach(particles) { particle in
                    particleView(particle)
                }
            }
            .frame(width: geometry.size.width, height: geometry.size.height)
            .onAppear {
                particles = factory.makeParticles(
                    mode: mode,
                    in: geometry.size,
                    reduceMotion: reduceMotion,
                    seed: seed
                )

                guard !reduceMotion else { return }
                isActive = false
                DispatchQueue.main.async {
                    isActive = true
                }
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }

    private func particleView(_ particle: TRConfettiParticle) -> some View {
        particleShapeView(particle)
            .frame(width: particle.size, height: particle.size)
            .rotationEffect(.degrees(reduceMotion ? particle.rotation * 0.25 : (isActive ? particle.rotation : 0)))
            .position(
                x: reduceMotion ? particle.startX : (isActive ? particle.endX : particle.startX),
                y: reduceMotion ? particle.startY : (isActive ? particle.endY : particle.startY)
            )
            .opacity(reduceMotion ? staticOpacity : (isActive ? 0 : 1))
            .scaleEffect(reduceMotion ? 1 : (isActive ? 0.80 : 1.0))
            .animation(reduceMotion ? .none : .easeOut(duration: particle.duration).delay(particle.delay), value: isActive)
    }

    @ViewBuilder
    private func particleShapeView(_ particle: TRConfettiParticle) -> some View {
        let fillColor = color(for: particle)

        switch particle.shape {
        case .rectangle:
            Rectangle()
                .fill(fillColor)
        case .circle:
            Circle()
                .fill(fillColor)
        case .diamond:
            DiamondShape()
                .fill(fillColor)
        }
    }

    private func color(for particle: TRConfettiParticle) -> Color {
        let palette = TRConfettiParticleFactory.palette(for: mode)
        guard palette.indices.contains(particle.colorIndex) else {
            return palette.first ?? TRGameplayStyle.Colors.primaryBlue
        }

        return palette[particle.colorIndex]
    }

    private var staticOpacity: Double {
        switch mode {
        case .success:
            return 0.82
        case .failure:
            return 0.36
        }
    }
}

private struct DiamondShape: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.midX, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.midY))
        path.addLine(to: CGPoint(x: rect.midX, y: rect.maxY))
        path.addLine(to: CGPoint(x: rect.minX, y: rect.midY))
        path.closeSubpath()
        return path
    }
}

#Preview("Confetti") {
    ZStack {
        TRResultScreenBackground()
        TRConfettiEmitter(mode: .success)
    }
}
