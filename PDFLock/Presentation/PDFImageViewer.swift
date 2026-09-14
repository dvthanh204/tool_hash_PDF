import SwiftUI
import PDFKit

struct PDFImageViewer: View {
    let pdfData: Data
    @State private var images: [NSImage] = []
    
    var body: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(0..<images.count, id: \.self) { index in
                    Image(nsImage: images[index])
                        .resizable()
                        .scaledToFit()
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                        .shadow(radius: 4)
                        .padding(.horizontal)
                        // Anti-copying is naturally enforced because it's rendered to NSImage!
                }
            }
            .padding(.vertical)
        }
        .onAppear {
            renderPDF()
        }
    }
    
    func renderPDF() {
        // Vẽ toàn bộ PDF thành NSImage nằm chết trên RAM. Không thể copy text!
        guard let document = PDFDocument(data: pdfData) else { return }
        var tempImages: [NSImage] = []
        
        for i in 0..<document.pageCount {
            if let page = document.page(at: i) {
                let pageRect = page.bounds(for: .mediaBox)
                let scale: CGFloat = 2.0 // Render 2x phân giải để nét
                let scaledRect = CGRect(x: 0, y: 0, width: pageRect.width * scale, height: pageRect.height * scale)
                
                let nsImage = NSImage(size: scaledRect.size)
                nsImage.lockFocus()
                if let context = NSGraphicsContext.current?.cgContext {
                    context.setFillColor(NSColor.white.cgColor)
                    context.fill(scaledRect)
                    
                    context.saveGState()
                    context.translateBy(x: 0.0, y: scaledRect.size.height)
                    context.scaleBy(x: scale, y: -scale)
                    page.draw(with: .mediaBox, to: context)
                    context.restoreGState()
                }
                nsImage.unlockFocus()
                tempImages.append(nsImage)
            }
        }
        self.images = tempImages
    }
}
