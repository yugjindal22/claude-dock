// Original geometric icons. No Anthropic artwork is distributed.
import AppKit

let args = CommandLine.arguments
guard args.count >= 3 else { exit(2) }
if args[1] == "focus" {
    guard let pid = Int32(args[2]), let app = NSRunningApplication(processIdentifier: pid) else { exit(3) }
    app.activate(options: [.activateAllWindows])
    exit(0)
}
if args[1] == "seticon" {
    guard args.count == 4, let image = NSImage(contentsOfFile: args[2]) else { exit(2) }
    exit(NSWorkspace.shared.setIcon(image, forFile: args[3], options: []) ? 0 : 3)
}
guard args[1] == "icon", args.count == 5 else { exit(2) }
let colors: [String: NSColor] = ["blue": .systemBlue, "purple": .systemPurple,
    "green": .systemGreen, "orange": .systemOrange, "pink": .systemPink, "teal": .systemTeal]
guard let color = colors[args[2]] else { exit(2) }
let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".iconset")
do {
    try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: dir) }
    for size in [16, 32, 128, 256, 512] {
        for scale in [1, 2] {
            let px = size * scale
            guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px,
                bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0),
                let context = NSGraphicsContext(bitmapImageRep: bitmap) else { exit(3) }
            NSGraphicsContext.saveGraphicsState()
            NSGraphicsContext.current = context
            let side = CGFloat(px)
            color.setFill()
            NSBezierPath(roundedRect: NSRect(x: side * 0.06, y: side * 0.06, width: side * 0.88,
                height: side * 0.88), xRadius: side * 0.2, yRadius: side * 0.2).fill()
            let attributes: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: side * 0.38, weight: .bold),
                .foregroundColor: NSColor.white]
            let label = NSAttributedString(string: args[3], attributes: attributes)
            let bounds = label.size()
            label.draw(at: NSPoint(x: (side - bounds.width) / 2, y: (side - bounds.height) / 2))
            NSGraphicsContext.restoreGraphicsState()
            let suffix = scale == 2 ? "@2x" : ""
            guard let png = bitmap.representation(using: .png, properties: [:]) else { exit(3) }
            try png.write(to: dir.appendingPathComponent("icon_\(size)x\(size)\(suffix).png"))
        }
    }
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/iconutil")
    process.arguments = ["-c", "icns", dir.path, "-o", args[4]]
    try process.run()
    process.waitUntilExit()
    if process.terminationStatus != 0 { exit(process.terminationStatus) }
} catch {
    fputs("\(error)\n", stderr)
    exit(1)
}
