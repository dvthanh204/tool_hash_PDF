import SwiftUI

@main
struct PDFLockApp: App {
    @StateObject private var licenseManager = LicenseManager()

    var body: some Scene {
        WindowGroup {
            if licenseManager.isActivated {
                MainView()
                    .environmentObject(licenseManager)
                    // Core Anti-Capture: Chống quay phim/chụp ảnh màn hình (AppKit)
                    .onAppear {
                        if let window = NSApplication.shared.windows.first {
                            window.sharingType = .none
                        }
                    }
            } else {
                ActivationView()
                    .environmentObject(licenseManager)
            }
        }
        .windowStyle(HiddenTitleBarWindowStyle())
    }
}
