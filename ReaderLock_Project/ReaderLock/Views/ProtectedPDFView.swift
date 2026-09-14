import SwiftUI
import PDFKit

// Ép vô hiệu hóa hoàn toàn Text Selection / Right Click menu
class SecurePDFView: PDFView {
    override func copy(_ sender: Any?) { } // Huỷ lệnh copy phím tắt
    override func menu(for event: NSEvent) -> NSMenu? { return nil } // Huỷ Right Click Options Menu
    override var acceptsFirstResponder: Bool { return false } // Không cho trỏ chuột Text
}

struct ProtectedPDFViewer: NSViewRepresentable {
    let pdfData: Data
    
    func makeNSView(context: Context) -> SecurePDFView {
        let pdfView = SecurePDFView()
        pdfView.autoScales = true
        pdfView.displayMode = .singlePageContinuous
        if let doc = PDFDocument(data: pdfData) {
            pdfView.document = doc
        }
        return pdfView
    }
    
    func updateNSView(_ nsView: SecurePDFView, context: Context) {
        if let doc = PDFDocument(data: pdfData) {
            nsView.document = doc
        }
    }
}
