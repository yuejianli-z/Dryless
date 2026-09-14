import AppKit
import AVFoundation
import CoreImage
import CoreMedia
import DrylessCore
import Foundation
import OSLog

enum CameraFailure: Error, Equatable {
    case unknownAuthorization
    case inputUnavailable
    case outputUnavailable
    case startTimedOut
    case system(String)
    case unsupportedResolution(Int, Int)
    case resolutionMismatch(Int, Int, Int, Int)

    func detail(language: AppLanguage) -> String {
        switch (self, language) {
        case (.unsupportedResolution(let w, let h), .zh): return "摄像头不支持 \(w) × \(h)。请选择其他分辨率。"
        case (.unsupportedResolution(let w, let h), .en): return "The camera does not support \(w) × \(h). Choose another resolution."
        case (.resolutionMismatch(let w, let h, let aw, let ah), .zh): return "请求 \(w) × \(h)，摄像头实际输出 \(aw) × \(ah)。采集已停止。"
        case (.resolutionMismatch(let w, let h, let aw, let ah), .en): return "Requested \(w) × \(h), but received \(aw) × \(ah). Capture stopped."
        case (.unknownAuthorization, .zh): return "无法确认摄像头权限状态。"
        case (.inputUnavailable, .zh): return "无法连接所选摄像头。"
        case (.outputUnavailable, .zh): return "无法读取摄像头画面。"
        case (.startTimedOut, .zh): return "摄像头启动超时。请检查设备是否被其他应用占用。"
        case (.unknownAuthorization, .en): return "The camera authorization state could not be determined."
        case (.inputUnavailable, .en): return "The selected camera could not be connected."
        case (.outputUnavailable, .en): return "The camera video feed could not be read."
        case (.startTimedOut, .en): return "Camera startup timed out. Check whether another app is using the device."
        case (.system(let message), _): return message
        }
    }
}

enum CameraState: Equatable {
    case off
    case starting
    case running
    case stopping
    case suspended
    case denied
    case unavailable
    case failed(CameraFailure)

    var isRunning: Bool { self == .running }

    var canStart: Bool {
        switch self {
        case .off, .suspended, .denied, .unavailable, .failed: return true
        case .starting, .running, .stopping: return false
        }
    }

    func label(language: AppLanguage) -> String {
        switch self {
        case .off: return L10n.text("camera_off", language)
        case .starting: return L10n.text("camera_starting", language)
        case .running: return L10n.text("camera_ready", language)
        case .stopping: return L10n.text("camera_stopping", language)
        case .suspended: return L10n.text("camera_suspended", language)
        case .denied: return L10n.text("camera_denied", language)
        case .unavailable: return L10n.text("camera_missing", language)
        case .failed: return L10n.text("camera_failed", language)
        }
    }

    func failureDetail(language: AppLanguage) -> String? {
        if case .failed(let failure) = self { return failure.detail(language: language) }
        return nil
    }
}

final class CameraService: NSObject, ObservableObject {
    private static let startTimeout: TimeInterval = 8
    private let captureLogger = Logger(subsystem: "com.yuejianli.dryless.mac", category: "CaptureResolution")

    @Published private(set) var state: CameraState = .off
    @Published private(set) var previewImage: NSImage?
    @Published private(set) var actualResolution: CGSize?
    @Published private(set) var eyeLandmarks: EyeLandmarks?

    var onMeasurement: ((EyeMeasurement) -> Void)?

    private let sessionQueue = DispatchQueue(label: "dryless.camera.session")
    private let videoQueue = DispatchQueue(label: "dryless.camera.video")
    private let context = CIContext()
    private let visionDetector = VisionBlinkDetector()
    private let stateLock = NSLock()

    private var session: AVCaptureSession?
    private var lockedDevice: AVCaptureDevice?
    private var generation = 0
    private var acceptingFramesForGeneration: Int?
    private var resolutionPublishedForGeneration: Int?
    private var frameCounter = 0
    private var settings = AppSettings.default

    func start(settings: AppSettings) {
        let token = beginGeneration(settings: settings)
        publish(state: .starting, for: token)
        publishFrame(image: nil, landmarks: nil, for: token)
        publishResolution(nil, for: token)
        scheduleStartTimeout(for: token)

        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            configureAndStart(generation: token)
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                guard let self, self.isCurrent(token) else { return }
                if granted {
                    self.configureAndStart(generation: token)
                } else {
                    self.publish(state: .denied, for: token)
                }
            }
        case .denied, .restricted:
            publish(state: .denied, for: token)
        @unknown default:
            publish(state: .failed(.unknownAuthorization), for: token)
        }
    }

    func startReadmeDemo(settings: AppSettings, image: NSImage?) {
        _ = beginGeneration(settings: settings)
        state = .running
        previewImage = image
        actualResolution = CGSize(width: 1920, height: 1080)
        eyeLandmarks = image == nil ? nil : .readmeDemo
    }

    func restart(settings: AppSettings) {
        let token = beginGeneration(settings: settings)
        publish(state: .starting, for: token)
        publishFrame(image: nil, landmarks: nil, for: token)
        publishResolution(nil, for: token)
        scheduleStartTimeout(for: token)

        sessionQueue.async { [weak self] in
            guard let self else { return }
            let oldSession = self.session
            self.session = nil
            if oldSession?.isRunning == true {
                oldSession?.stopRunning()
            }
            self.releaseDeviceConfigurationLock()
            guard self.isCurrent(token) else { return }
            self.configureAndStartOnSessionQueue(generation: token)
        }
    }

    func updateSettings(_ settings: AppSettings) {
        stateLock.withLock {
            self.settings = settings
        }
    }

    func stop() {
        stop(finalState: .off)
    }

    func suspend() {
        stop(finalState: .suspended)
    }

    private func stop(finalState: CameraState) {
        let token = stateLock.withLock { () -> Int in
            generation += 1
            acceptingFramesForGeneration = nil
            resolutionPublishedForGeneration = nil
            return generation
        }
        DispatchQueue.main.async { [weak self] in
            self?.state = .stopping
            self?.previewImage = nil
            self?.actualResolution = nil
            self?.eyeLandmarks = nil
        }

        sessionQueue.async { [weak self] in
            guard let self else { return }
            let oldSession = self.session
            self.session = nil
            if oldSession?.isRunning == true {
                oldSession?.stopRunning()
            }
            self.releaseDeviceConfigurationLock()
            self.publish(state: finalState, for: token)
        }
    }

    private func beginGeneration(settings: AppSettings) -> Int {
        stateLock.withLock {
            generation += 1
            acceptingFramesForGeneration = nil
            resolutionPublishedForGeneration = nil
            self.settings = settings
            frameCounter = 0
            return generation
        }
    }

    private func configureAndStart(generation token: Int) {
        sessionQueue.async { [weak self] in
            self?.configureAndStartOnSessionQueue(generation: token)
        }
    }

    private func configureAndStartOnSessionQueue(generation token: Int) {
        guard isCurrent(token) else { return }

        let captureSession = AVCaptureSession()
        captureSession.beginConfiguration()
        let requested = settingsSnapshot()

        guard let device = selectCamera(index: requested.cameraIndex) else {
            captureSession.commitConfiguration()
            publish(state: .unavailable, for: token)
            return
        }

        do {
            let input = try AVCaptureDeviceInput(device: device)
            guard captureSession.canAddInput(input) else {
                captureSession.commitConfiguration()
                publish(state: .failed(.inputUnavailable), for: token)
                return
            }
            captureSession.addInput(input)

            let output = AVCaptureVideoDataOutput()
            output.alwaysDiscardsLateVideoFrames = true
            output.videoSettings = [
                kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
            ]
            output.setSampleBufferDelegate(self, queue: videoQueue)
            guard captureSession.canAddOutput(output) else {
                captureSession.commitConfiguration()
                publish(state: .failed(.outputUnavailable), for: token)
                return
            }
            captureSession.addOutput(output)
            try configureFormat(for: device, width: requested.cameraWidth, height: requested.cameraHeight)
            captureSession.commitConfiguration()

            guard isCurrent(token) else { return }
            session = captureSession
            captureSession.startRunning()

            guard isCurrent(token) else {
                captureSession.stopRunning()
                session = nil
                releaseDeviceConfigurationLock()
                return
            }
            stateLock.withLock {
                acceptingFramesForGeneration = token
            }
            publish(state: .running, for: token)
        } catch {
            captureSession.commitConfiguration()
            releaseDeviceConfigurationLock()
            publish(state: .failed((error as? CameraFailure) ?? .system(error.localizedDescription)), for: token)
        }
    }

    private func scheduleStartTimeout(for token: Int) {
        DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + Self.startTimeout) { [weak self] in
            guard let self else { return }
            let failureToken = self.stateLock.withLock { () -> Int? in
                guard self.generation == token, self.acceptingFramesForGeneration == nil else { return nil }
                self.generation += 1
                self.acceptingFramesForGeneration = nil
                self.resolutionPublishedForGeneration = nil
                return self.generation
            }
            guard let failureToken else { return }
            self.publish(state: .failed(.startTimedOut), for: failureToken)
        }
    }

    private func selectCamera(index: Int) -> AVCaptureDevice? {
        let discovery = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.builtInWideAngleCamera, .external],
            mediaType: .video,
            position: .unspecified
        )
        let devices = discovery.devices
        guard !devices.isEmpty else { return AVCaptureDevice.default(for: .video) }
        return devices.indices.contains(index) ? devices[index] : devices[0]
    }

    private func configureFormat(for device: AVCaptureDevice, width: Int, height: Int) throws {
        let requested = CMVideoDimensions(width: Int32(width), height: Int32(height))
        let videoFormats = device.formats.filter {
            CMFormatDescriptionGetMediaType($0.formatDescription) == kCMMediaType_Video
        }
        guard let selected = videoFormats.first(where: {
            let size = CMVideoFormatDescriptionGetDimensions($0.formatDescription)
            return size.width == requested.width && size.height == requested.height
        }) else {
            throw CameraFailure.unsupportedResolution(width, height)
        }

        try device.lockForConfiguration()
        device.activeFormat = selected
        lockedDevice = device
    }

    private func settingsSnapshot() -> AppSettings {
        stateLock.withLock { settings }
    }

    private func releaseDeviceConfigurationLock() {
        guard let lockedDevice else { return }
        lockedDevice.unlockForConfiguration()
        self.lockedDevice = nil
    }

    private func isCurrent(_ token: Int) -> Bool {
        stateLock.withLock { generation == token }
    }

    private func frameGeneration() -> Int? {
        stateLock.withLock { acceptingFramesForGeneration }
    }

    private func publish(state: CameraState, for token: Int) {
        guard isCurrent(token) else { return }
        DispatchQueue.main.async { [weak self] in
            guard let self, self.isCurrent(token) else { return }
            self.state = state
        }
    }

    private func publishPreview(_ image: NSImage?, for token: Int) {
        DispatchQueue.main.async { [weak self] in
            guard let self, self.isCurrent(token) else { return }
            self.previewImage = image
        }
    }

    private func publishFrame(image: NSImage?, landmarks: EyeLandmarks?, for token: Int) {
        DispatchQueue.main.async { [weak self] in
            guard let self, self.isCurrent(token) else { return }
            self.previewImage = image
            self.eyeLandmarks = landmarks
        }
    }

    private func publishResolution(_ size: CGSize?, for token: Int) {
        DispatchQueue.main.async { [weak self] in
            guard let self, self.isCurrent(token) else { return }
            self.actualResolution = size
        }
    }

}

extension CameraService: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard let token = frameGeneration(), isCurrent(token) else { return }
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }

        let localSettings = settingsSnapshot()
        let count = stateLock.withLock { () -> Int in
            frameCounter += 1
            return frameCounter
        }
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        if count == 1 || count % 60 == 0 {
            captureLogger.notice("generation=\(token) frame=\(count) requested=\(localSettings.cameraWidth)x\(localSettings.cameraHeight) actual=\(width)x\(height)")
        }
        guard width == localSettings.cameraWidth, height == localSettings.cameraHeight else {
            captureLogger.error("Resolution mismatch: requested=\(localSettings.cameraWidth)x\(localSettings.cameraHeight) actual=\(width)x\(height)")
            stop(finalState: .failed(.resolutionMismatch(localSettings.cameraWidth, localSettings.cameraHeight, width, height)))
            return
        }

        let measurement = visionDetector.measure(pixelBuffer: pixelBuffer)
        guard frameGeneration() == token, isCurrent(token) else { return }
        publishPreview(
            pixelBuffer: pixelBuffer,
            landmarks: measurement.landmarks,
            generation: token,
            visible: localSettings.previewVisible
        )
        onMeasurement?(measurement.eyeMeasurement)
        let shouldPublishResolution = stateLock.withLock { () -> Bool in
            guard acceptingFramesForGeneration == token, resolutionPublishedForGeneration != token else { return false }
            resolutionPublishedForGeneration = token
            return true
        }
        if shouldPublishResolution {
            publishResolution(
                CGSize(width: CVPixelBufferGetWidth(pixelBuffer), height: CVPixelBufferGetHeight(pixelBuffer)),
                for: token
            )
        }
    }

    private func publishPreview(
        pixelBuffer: CVPixelBuffer,
        landmarks: EyeLandmarks?,
        generation token: Int,
        visible: Bool
    ) {
        guard visible else {
            publishFrame(image: nil, landmarks: nil, for: token)
            return
        }
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else { return }
        let image = NSImage(cgImage: cgImage, size: NSSize(width: cgImage.width, height: cgImage.height))
        publishFrame(image: image, landmarks: landmarks, for: token)
    }
}

private extension NSLock {
    func withLock<T>(_ action: () -> T) -> T {
        lock()
        defer { unlock() }
        return action()
    }
}
