import SwiftUI

@main
struct AdminApp: App {
    var body: some Scene {
        WindowGroup {
            LicenseGeneratorView()
        }
    }
}

struct LicenseGeneratorView: View {
    var body: some View {
        Text("Admin Tool Swift (Nếu muốn xài UI Swift)")
            .padding()
        // Implement giống hệt author_app.py
    }
}
