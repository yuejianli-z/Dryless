import Foundation

enum AppResources {
    static let bundle: Bundle = {
        if let resourceURL = Bundle.main.resourceURL,
           let packagedBundle = Bundle(url: resourceURL.appendingPathComponent("DrylessMac_DrylessMac.bundle")) {
            return packagedBundle
        }

        #if DEBUG
        return .module
        #else
        fatalError("Dryless resource bundle is missing. Reinstall the complete app.")
        #endif
    }()
}
