import SwiftUI

struct ActivationView: View {
    @EnvironmentObject var licenseManager: LicenseManager
    @State private var licenseKey: String = ""
    @State private var showError = false
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "lock.shield")
                .resizable()
                .frame(width: 80, height: 80)
                .foregroundColor(.blue)
            
            Text("PDFLock DRM Kích Hoạt (Bản Swift macOS)")
                .font(.largeTitle)
                .bold()
            
            Text("Machine ID Apple của bạn:")
            Text(MachineID.get())
                .font(.title2)
                .bold()
                .foregroundColor(.red)
                .textSelection(.enabled) // Cho phép copy cái ID này để dán
            
            SecureField("Nhập License Key", text: $licenseKey)
                .textFieldStyle(RoundedBorderTextFieldStyle())
                .frame(width: 400)
                .padding(.top, 10)
            
            Button("KÍCH HOẠT") {
                if !licenseManager.activate(with: licenseKey.trimmingCharacters(in: .whitespacesAndNewlines)) {
                    showError = true
                }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .alert("Lỗi", isPresented: $showError) {
                Button("OK", role: .cancel) { }
            } message: {
                Text("License Key không hợp lệ, không đúng thiết bị hoặc đã hết hạn!")
            }
        }
        .frame(width: 600, height: 400)
    }
}
