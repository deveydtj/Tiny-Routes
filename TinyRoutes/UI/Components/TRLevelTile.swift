import SwiftUI

enum TRLevelTileState {
    case completed
    case current
    case locked
}

/// A level's badge on the map: a chunky tile standing on its own darker base, green
/// with a tick once done, glowing blue for the level to play next, grey and locked
/// beyond that.
struct TRLevelTile: View {
    static let size = CGSize(width: 56, height: 56)

    let levelNumber: Int
    let state: TRLevelTileState
    let stars: Int
    let action: () -> Void

    private static let cornerRadius: CGFloat = 15
    private static let lipDepth: CGFloat = 4

    var body: some View {
        Button(action: action) {
            VStack(spacing: 1) {
                Text("\(levelNumber)")
                    .font(.system(size: 24, weight: .black, design: .rounded))
                    .foregroundStyle(numberColor)
                    .shadow(color: state == .locked ? .clear : inkColor.opacity(0.55), radius: 0, x: 0, y: 1.5)
                    .minimumScaleFactor(0.6)
                    .lineLimit(1)
                bottomContent
                    .frame(height: 11)
            }
            .padding(.horizontal, 4)
            .frame(width: Self.size.width, height: Self.size.height - Self.lipDepth)
            .background { face }
            .background {
                tileShape
                    .fill(lipColor)
                    .offset(y: Self.lipDepth)
                    .shadow(color: glowColor, radius: state == .current ? 12 : 5, x: 0, y: state == .current ? 2 : 4)
            }
            .padding(.bottom, Self.lipDepth)
            .overlay(alignment: .topTrailing) {
                if state == .completed {
                    completedBadge
                        .offset(x: 7, y: -7)
                }
            }
            .overlay(alignment: .top) {
                if state == .current {
                    sparkle
                        .offset(y: -15)
                }
            }
            .contentShape(tileShape)
        }
        .buttonStyle(TRLevelTilePressStyle())
        .disabled(state == .locked)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("Level \(levelNumber)"))
        .accessibilityValue(Text(accessibilityValueDescription))
        .accessibilityAddTraits(.isButton)
    }

    private var tileShape: RoundedRectangle {
        RoundedRectangle(cornerRadius: Self.cornerRadius, style: .continuous)
    }

    private var face: some View {
        tileShape
            .fill(LinearGradient(colors: faceColors, startPoint: .top, endPoint: .bottom))
            .overlay(alignment: .top) {
                // A soft gloss across the top half.
                tileShape
                    .fill(LinearGradient(colors: [.white.opacity(state == .locked ? 0.5 : 0.3), .clear], startPoint: .top, endPoint: .center))
            }
            .overlay { tileShape.strokeBorder(.white.opacity(state == .locked ? 0.95 : 0.85), lineWidth: 2.5) }
    }

    @ViewBuilder
    private var bottomContent: some View {
        if state == .locked {
            Image(systemName: "lock.fill")
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(Color(red: 0.47, green: 0.53, blue: 0.62))
        } else {
            HStack(spacing: 1.5) {
                ForEach(0..<3, id: \.self) { index in
                    Image(systemName: "star.fill")
                        .font(.system(size: 9, weight: .black))
                        .foregroundStyle(index < clampedStarCount
                            ? Color(red: 1.0, green: 0.82, blue: 0.16)
                            : Color.white.opacity(0.4))
                        .shadow(color: index < clampedStarCount ? inkColor.opacity(0.45) : .clear, radius: 0, x: 0, y: 1)
                }
            }
            .accessibilityHidden(true)
        }
    }

    private var faceColors: [Color] {
        switch state {
        case .completed: [Color(red: 0.27, green: 0.74, blue: 0.42), Color(red: 0.13, green: 0.58, blue: 0.33)]
        case .current: [Color(red: 0.30, green: 0.62, blue: 1.0), Color(red: 0.11, green: 0.43, blue: 0.93)]
        case .locked: [Color(red: 0.88, green: 0.91, blue: 0.95), Color(red: 0.74, green: 0.79, blue: 0.86)]
        }
    }

    /// The darker base the tile stands on.
    private var lipColor: Color {
        switch state {
        case .completed: Color(red: 0.07, green: 0.40, blue: 0.22)
        case .current: Color(red: 0.06, green: 0.28, blue: 0.70)
        case .locked: Color(red: 0.55, green: 0.60, blue: 0.68)
        }
    }

    /// The number's and stars' drop shadow.
    private var inkColor: Color {
        state == .current ? Color(red: 0.04, green: 0.20, blue: 0.55) : Color(red: 0.04, green: 0.30, blue: 0.16)
    }

    private var glowColor: Color {
        switch state {
        case .completed: Color(red: 0.06, green: 0.30, blue: 0.16).opacity(0.35)
        case .current: Color(red: 0.36, green: 0.66, blue: 1.0).opacity(0.85)
        case .locked: Color.black.opacity(0.16)
        }
    }

    private var numberColor: Color {
        state == .locked ? Color(red: 0.44, green: 0.50, blue: 0.60) : .white
    }

    private var completedBadge: some View {
        ZStack {
            Circle()
                .fill(Color.white)
                .frame(width: 22, height: 22)
            Circle()
                .fill(Color(red: 0.20, green: 0.70, blue: 0.40))
                .frame(width: 17, height: 17)
            Image(systemName: "checkmark")
                .font(.system(size: 9, weight: .black))
                .foregroundStyle(.white)
        }
        .shadow(color: .black.opacity(0.15), radius: 2, x: 0, y: 1)
        .accessibilityHidden(true)
    }

    /// Little golden rays over the level to play next.
    private var sparkle: some View {
        HStack(alignment: .bottom, spacing: 7) {
            ray.rotationEffect(.degrees(-28)).offset(y: 3)
            ray
            ray.rotationEffect(.degrees(28)).offset(y: 3)
        }
        .accessibilityHidden(true)
    }

    private var ray: some View {
        Capsule()
            .fill(Color(red: 1.0, green: 0.80, blue: 0.20))
            .frame(width: 3.5, height: 10)
            .shadow(color: Color(red: 0.70, green: 0.45, blue: 0.0).opacity(0.3), radius: 0, x: 0, y: 1)
    }

    private var clampedStarCount: Int {
        min(max(stars, 0), 3)
    }

    private var accessibilityValueDescription: String {
        Self.accessibilityValue(state: state, stars: stars)
    }

    /// What VoiceOver reads after a tile's level, here or on the 3D map's signs.
    static func accessibilityValue(state: TRLevelTileState, stars: Int) -> String {
        let stateDescription = switch state {
        case .completed: "Completed"
        case .current: "Current"
        case .locked: "Locked"
        }
        guard state != .locked else { return stateDescription }
        let starCount = min(max(stars, 0), 3)
        return "\(stateDescription), \(starCount == 1 ? "1 star" : "\(starCount) stars")"
    }
}

/// The tile presses down onto its base.
private struct TRLevelTilePressStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.94 : 1)
            .animation(.spring(response: 0.2, dampingFraction: 0.65), value: configuration.isPressed)
    }
}

#Preview("Level Tile States") {
    HStack(spacing: 20) {
        TRLevelTile(levelNumber: 1, state: .completed, stars: 3, action: {})
        TRLevelTile(levelNumber: 2, state: .current, stars: 0, action: {})
        TRLevelTile(levelNumber: 3, state: .locked, stars: 0, action: {})
    }
    .padding(30)
    .background(Color(red: 0.56, green: 0.78, blue: 0.40))
}
