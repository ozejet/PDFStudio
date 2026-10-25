import AppKit
import Foundation

let arguments = Array(CommandLine.arguments.dropFirst())
guard !arguments.isEmpty else { exit(EXIT_FAILURE) }

let suggestedName = arguments[0]
let suggestedFolder = arguments.count > 1 ? arguments[1] : ""
let application = NSApplication.shared
application.setActivationPolicy(.regular)
application.activate(ignoringOtherApps: true)

let panel = NSSavePanel()
panel.title = "PDF Studio - Save a copy"
panel.message = "Choose where to save the PDF Studio result."
panel.nameFieldStringValue = suggestedName
panel.canCreateDirectories = true
panel.isExtensionHidden = false
panel.allowsOtherFileTypes = true
if !suggestedFolder.isEmpty {
    panel.directoryURL = URL(fileURLWithPath: suggestedFolder, isDirectory: true)
}

if panel.runModal() == .OK, let destination = panel.url {
    print(destination.path)
}
