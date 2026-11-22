import SwiftUI

/**
 * SwiftUI Dynamic Student Watermark Overlay View.
 *
 * Renders repeated diagonal candidate watermarks across the examination canvas.
 */
struct MobileWatermarkView: View {
    let watermarkText: String
    var opacity: Double = 0.08
    var fontSize: CGFloat = 12
    var rotationAngle: Double = -25.0
    var spacing: CGFloat = 140.0

    var body: some View {
        GeometryReader { geometry in
            let cols = Int(geometry.size.width / (spacing * 1.5)) + 3
            let rows = Int(geometry.size.height / spacing) + 3

            VStack(spacing: spacing) {
                ForEach(0..<rows, id: \.self) { _ in
                    HStack(spacing: spacing * 1.5) {
                        ForEach(0..<cols, id: \.self) { _ in
                            Text(watermarkText)
                                .font(.system(size: fontSize, weight: .bold, design: .monospaced))
                                .foregroundColor(Color.white.opacity(opacity))
                                .rotationEffect(.degrees(rotationAngle))
                                .fixedSize()
                        }
                    }
                }
            }
            .frame(width: geometry.size.width, height: geometry.size.height, alignment: .center)
            .clipped()
            .allowsHitTesting(false)
        }
    }
}
