import AVFoundation
import CoreVideo
import DrylessCore
import ImageIO
import Vision

struct EyeLandmarks: Equatable {
    let left: [CGPoint]
    let right: [CGPoint]

    static let readmeDemo = EyeLandmarks(
        left: [
            CGPoint(x: 0.3655, y: 0.3846), CGPoint(x: 0.3806, y: 0.3686),
            CGPoint(x: 0.4033, y: 0.3730), CGPoint(x: 0.4168, y: 0.3930),
            CGPoint(x: 0.4011, y: 0.3933), CGPoint(x: 0.3802, y: 0.3931)
        ],
        right: [
            CGPoint(x: 0.5331, y: 0.3905), CGPoint(x: 0.5189, y: 0.3730),
            CGPoint(x: 0.4970, y: 0.3761), CGPoint(x: 0.4841, y: 0.3959),
            CGPoint(x: 0.4990, y: 0.3973), CGPoint(x: 0.5191, y: 0.3983)
        ]
    )
}

struct VisionMeasurement {
    let eyeMeasurement: EyeMeasurement
    let landmarks: EyeLandmarks?
}

final class VisionBlinkDetector {
    private let request = VNDetectFaceLandmarksRequest()

    func measure(pixelBuffer: CVPixelBuffer) -> VisionMeasurement {
        let handler = VNImageRequestHandler(
            cvPixelBuffer: pixelBuffer,
            orientation: .up,
            options: [:]
        )

        do {
            try handler.perform([request])
        } catch {
            return VisionMeasurement(
                eyeMeasurement: EyeMeasurement(faceDetected: false, leftOpenness: 0, rightOpenness: 0),
                landmarks: nil
            )
        }

        guard
            let face = request.results?.first as? VNFaceObservation,
            let landmarks = face.landmarks,
            let leftEye = landmarks.leftEye,
            let rightEye = landmarks.rightEye
        else {
            return VisionMeasurement(
                eyeMeasurement: EyeMeasurement(faceDetected: false, leftOpenness: 0, rightOpenness: 0),
                landmarks: nil
            )
        }

        return VisionMeasurement(
            eyeMeasurement: EyeMeasurement(
                faceDetected: true,
                leftOpenness: openness(for: leftEye),
                rightOpenness: openness(for: rightEye)
            ),
            landmarks: EyeLandmarks(
                left: normalizedPoints(for: leftEye, in: face),
                right: normalizedPoints(for: rightEye, in: face)
            )
        )
    }

    private func openness(for region: VNFaceLandmarkRegion2D) -> Double {
        let points = region.normalizedPoints
        // Vision returns the eye contour clockwise: corner, upper lid points,
        // opposite corner, then lower lid points. EAR keeps the reading relative
        // to the eye itself rather than the camera's pixel scale.
        if points.count >= 6 {
            let width = distance(points[0], points[3])
            guard width > 0.000_001 else { return 0 }
            let lidGap = (distance(points[1], points[5]) + distance(points[2], points[4])) / 2
            return max(0, lidGap / width)
        }

        guard points.count >= 4 else { return 0 }

        let minX = points.map(\.x).min() ?? 0
        let maxX = points.map(\.x).max() ?? 0
        let minY = points.map(\.y).min() ?? 0
        let maxY = points.map(\.y).max() ?? 0
        let width = max(Double(maxX - minX), 0.000_001)
        return max(0, Double(maxY - minY) / width)
    }

    private func distance(_ lhs: CGPoint, _ rhs: CGPoint) -> Double {
        let dx = Double(lhs.x - rhs.x)
        let dy = Double(lhs.y - rhs.y)
        return hypot(dx, dy)
    }

    private func normalizedPoints(for region: VNFaceLandmarkRegion2D, in face: VNFaceObservation) -> [CGPoint] {
        region.normalizedPoints.map { point in
            let x = face.boundingBox.minX + point.x * face.boundingBox.width
            let y = face.boundingBox.minY + point.y * face.boundingBox.height
            // Vision uses a lower-left origin; SwiftUI's drawing space starts at the top-left.
            return CGPoint(x: x, y: 1 - y)
        }
    }
}
