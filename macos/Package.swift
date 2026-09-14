// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "DrylessMac",
    defaultLocalization: "en",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .library(name: "DrylessCore", targets: ["DrylessCore"]),
        .executable(name: "DrylessMac", targets: ["DrylessMac"]),
        .executable(name: "DrylessCoreChecks", targets: ["DrylessCoreChecks"])
    ],
    targets: [
        .target(
            name: "DrylessCore",
            path: "Sources/DrylessCore"
        ),
        .executableTarget(
            name: "DrylessMac",
            dependencies: ["DrylessCore"],
            path: "Sources/DrylessMac",
            resources: [
                .copy("Resources/Sounds"),
                .copy("Resources/Icons"),
                .copy("Resources/Licenses"),
                .copy("Resources/README.md")
            ]
        ),
        .executableTarget(
            name: "DrylessCoreChecks",
            dependencies: ["DrylessCore"],
            path: "Tests/DrylessCoreChecks"
        )
    ]
)
