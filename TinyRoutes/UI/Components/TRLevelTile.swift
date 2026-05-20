import SwiftUI

enum TRLevelTileState {
    case completed
    case current
    case locked
}

struct TRLevelTile: View {
    let levelNumber: Int
    let state: TRLevelTileState
    let stars: Int
    let action: () -> Void

    private let tileSize = CGSize(width: 92, height: 104)

    var body: some View {
        Button(action: action) {
            VStack(spacing: 0) {
                Spacer(minLength: 0)
                Text("\(levelNumber)")
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                    .foregroundStyle(numberColor)
                Spacer(minLength: 0)
                bottomContent
                    .frame(height: 18)
            }
            .padding(.vertical, 12)
            .frame(width: tileSize.width, height: tileSize.height)
            .background(tileFill)
            .overlay(alignment: .top) {
                if state == .completed {
                    RoundedRectangle(cornerRadius: 20, style: .continuous)
                        .fill(
                            LinearGradient(
                                colors: [Color.white.opacity(0.35), Color.white.opacity(0)],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                        .frame(height: 34)
                        .allowsHitTesting(false)
                }
            }
            .overlay(
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(Color.white, lineWidth: 2)
            )
            .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
            .shadow(
                color: state == .completed
                    ? Color(red: 0.10, green: 0.42, blue: 0.34).opacity(0.35)
                    : Color.black.opacity(0.16),
                radius: state == .completed ? 9 : 5,
                x: 0,
                y: state == .completed ? 5 : 2
            )
            .overlay(alignment: .topTrailing) {
                if state == .completed {
                    completedBadge
                        .offset(x: 8, y: -8)
                }
            }
        }
        .buttonStyle(.plain)
        .disabled(state == .locked)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Level \(levelNumber)")
        .accessibilityValue("\(accessibilityStateDescription), \(starCountDescription)")
    }

    @ViewBuilder
    private var bottomContent: some View {
        if state == .locked {
            Image(systemName: "lock.fill")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(Color(red: 0.46, green: 0.53, blue: 0.63))
        } else if state == .completed {
            HStack(spacing: 3) {
                ForEach(0..<clampedStarCount, id: \.self) { _ in
                    Image(systemName: "star.fill")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(Color(red: 1.0, green: 0.86, blue: 0.20))
                }
            }
            .accessibilityHidden(true)
        } else {
            HStack(spacing: 3) {
                ForEach(0..<3, id: \.self) { index in
                    Image(systemName: index < stars ? "star.fill" : "star")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(index < stars ? Color.yellow : Color.white.opacity(0.6))
                }
            }
        }
    }

    private var tileFill: some ShapeStyle {
        switch state {
        case .completed:
            LinearGradient(colors: [Color(red: 0.16, green: 0.72, blue: 0.60), Color(red: 0.11, green: 0.58, blue: 0.48)], startPoint: .top, endPoint: .bottom)
        case .current:
            LinearGradient(colors: [Color(red: 0.26, green: 0.58, blue: 0.98), Color(red: 0.18, green: 0.43, blue: 0.92)], startPoint: .top, endPoint: .bottom)
        case .locked:
            LinearGradient(colors: [Color(red: 0.95, green: 0.97, blue: 1.0), Color(red: 0.88, green: 0.91, blue: 0.96)], startPoint: .top, endPoint: .bottom)
        }
    }

    private var numberColor: Color {
        state == .locked ? Color(red: 0.44, green: 0.50, blue: 0.60) : .white
    }

    private var completedBadge: some View {
        ZStack {
            Circle()
                .fill(Color.white)
                .frame(width: 26, height: 26)
            Circle()
                .fill(Color(red: 0.20, green: 0.74, blue: 0.50))
                .frame(width: 21, height: 21)
            Image(systemName: "checkmark")
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(.white)
        }
        .accessibilityHidden(true)
    }

    private var accessibilityStateDescription: String {
        switch state {
        case .completed:
            "Completed"
        case .current:
            "Current"
        case .locked:
            "Locked"
        }
    }

    private var clampedStarCount: Int {
        min(max(stars, 0), 3)
    }

    private var starCountDescription: String {
        let starCount = clampedStarCount
        return starCount == 1 ? "1 star" : "\(starCount) stars"
    }
}

#Preview("Level Tile States") {
    HStack(spacing: 16) {
        TRLevelTile(levelNumber: 1, state: .completed, stars: 3, action: {})
        TRLevelTile(levelNumber: 2, state: .current, stars: 2, action: {})
        TRLevelTile(levelNumber: 3, state: .locked, stars: 0, action: {})
    }
    .padding()
    .background(Color(red: 0.93, green: 0.96, blue: 1.0))
}
