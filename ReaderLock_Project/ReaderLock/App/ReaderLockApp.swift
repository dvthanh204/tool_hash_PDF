import SwiftUI

@main
struct ReaderLockApp: App {
    @State private var isActivated: Bool = false
    
    var body: some Scene {
        WindowGroup {
            if isActivated {
                MainView()
                    .onAppear {
                        // Kỹ thuật Anti-Screen Capture (Chống quay phim / chụp ảnh)
                        if let window = NSApplication.shared.windows.first {
                            window.sharingType = .none
                        }
                    }
            } else {
                ActivationView(isActivated: $isActivated)
                    .onAppear {
                        // Kiểm tra License xem đã có trong UserDefaults chưa
                        if let key = UserDefaults.standard.string(forKey: "LicenseKey"),
                           CryptoManager.verifyLicense(key: key) {
                            self.isActivated = true
                        }
                    }
            }
        }
        // Vô hiệu hóa một số tính năng trong Menu hệ thống
        .commands {
            CommandGroup(replacing: .printItem) { }     // No Print
            CommandGroup(replacing: .saveItem) { }      // No Export / Save
        }
    }
}
