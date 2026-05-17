import SwiftUI

struct SpriteImage: View {
    let name: String

    var body: some View {
        if let image = Self.loadImage(named: name) {
            Image(uiImage: image)
                .resizable()
        } else {
            Color.clear
        }
    }

    private static func loadImage(named name: String) -> UIImage? {
        if let image = UIImage(named: "\(name).png") ?? UIImage(named: name) {
            return image
        }

        let imageURLs = ["png", "jpg"].flatMap { fileExtension in
            [
                Bundle.main.url(forResource: name, withExtension: fileExtension),
                Bundle.main.url(forResource: name, withExtension: fileExtension, subdirectory: "Sprites"),
                Bundle.main.url(forResource: name, withExtension: fileExtension, subdirectory: "Resources/Sprites")
            ]
        }

        return imageURLs
            .compactMap { $0 }
            .lazy
            .compactMap { UIImage(contentsOfFile: $0.path) }
            .first
    }
}

struct SwitchNodeView: View {
    let activeDirectionAngle: Double
    let spriteSize: CGFloat
    let ringSize: CGFloat

    private var arrowTransform: DirectionalArrowTransform {
        DirectionalArrowTransform(angle: activeDirectionAngle)
    }

    var body: some View {
        ZStack {
            Circle()
                .fill(Color.white)
                .frame(width: ringSize, height: ringSize)
                .overlay(
                    Circle()
                        .stroke(Color.blue, lineWidth: 2)
                )

            SpriteImage(name: "right_arrow")
                .scaledToFit()
                .frame(width: spriteSize, height: spriteSize)
                .scaleEffect(x: arrowTransform.xScale, y: 1)
                .rotationEffect(.radians(arrowTransform.rotationAngle))
        }
        .frame(width: max(spriteSize, ringSize), height: max(spriteSize, ringSize))
    }
}

struct DirectionalArrowTransform {
    let rotationAngle: Double
    let xScale: CGFloat

    init(angle: Double) {
        let normalizedAngle = Self.normalizedAngle(angle)
        if cos(normalizedAngle) < 0 {
            rotationAngle = Self.normalizedAngle(normalizedAngle - .pi)
            xScale = -1
        } else {
            rotationAngle = normalizedAngle
            xScale = 1
        }
    }

    private static func normalizedAngle(_ angle: Double) -> Double {
        var normalizedAngle = angle
        while normalizedAngle <= -.pi {
            normalizedAngle += 2 * .pi
        }
        while normalizedAngle > .pi {
            normalizedAngle -= 2 * .pi
        }
        return normalizedAngle
    }
}

struct SwitchNodeView_Previews: PreviewProvider {
    static var previews: some View {
        SwitchNodeView(activeDirectionAngle: 0, spriteSize: 52, ringSize: 28)
    }
}
