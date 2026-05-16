import SwiftUI

struct SwitchNodeView: View {
    let activeDirectionAngle: Double
    let size: CGFloat

    var body: some View {
        Circle()
            .fill(Color.white)
            .overlay(
                Circle()
                    .stroke(Color.blue, lineWidth: 2)
            )
            .overlay(
                Image(systemName: "arrowtriangle.up.fill")
                    .font(.system(size: size * 0.45, weight: .bold))
                    .foregroundStyle(Color.blue)
                    .rotationEffect(.radians(activeDirectionAngle + (.pi / 2)))
            )
            .frame(width: size, height: size)
    }
}

#Preview {
    SwitchNodeView(activeDirectionAngle: 0, size: 22)
}
