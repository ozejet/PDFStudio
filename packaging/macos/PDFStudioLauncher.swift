import AppKit
import Darwin
import Foundation

final class PDFStudioDelegate: NSObject, NSApplicationDelegate {
    private var backend: Process?
    private var outputPipe: Pipe?
    private var outputBuffer = Data()
    private var serviceURL: URL?
    private var dataDirectory: URL?
    private var terminating = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        installMenu()
        startBackend()
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if let url = serviceURL {
            openInSafari(url)
        } else if backend == nil || backend?.isRunning == false {
            startBackend()
        }
        return true
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if let process = backend, process.isRunning {
            terminating = true
            closeSafariTabs()
            stopBackend()
            removeRuntimeState()
            return .terminateLater
        }
        terminating = true
        closeSafariTabs()
        removeRuntimeState()
        return .terminateNow
    }

    private func installMenu() {
        let menu = NSMenu()
        let applicationItem = NSMenuItem()
        menu.addItem(applicationItem)
        let applicationMenu = NSMenu()
        applicationMenu.addItem(withTitle: "Quit PDF Studio", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        applicationItem.submenu = applicationMenu
        NSApp.mainMenu = menu
    }

    private func startBackend() {
        guard backend == nil || backend?.isRunning == false else { return }
        let resources = Bundle.main.resourceURL!
        let runtime = resources.appendingPathComponent("runtime/PDFStudioBackend", isDirectory: true)
        let executable = runtime.appendingPathComponent("PDFStudioBackend")
        guard FileManager.default.isExecutableFile(atPath: executable.path) else {
            fail("The bundled PDF Studio engine is missing or cannot run.")
            return
        }

        var arguments = Array(CommandLine.arguments.dropFirst())
        if let position = arguments.firstIndex(of: "--data-dir"), position + 1 < arguments.count {
            dataDirectory = URL(fileURLWithPath: arguments[position + 1], isDirectory: true)
        } else {
            let applicationSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
            dataDirectory = applicationSupport.appendingPathComponent("PDFStudio", isDirectory: true)
            arguments = ["--data-dir", dataDirectory!.path] + arguments
        }
        try? FileManager.default.createDirectory(at: dataDirectory!, withIntermediateDirectories: true)
        removeRuntimeState()

        let process = Process()
        let pipe = Pipe()
        process.executableURL = executable
        process.currentDirectoryURL = runtime
        process.arguments = ["--no-browser"] + arguments
        process.standardOutput = pipe
        process.standardError = pipe
        process.terminationHandler = { [weak self] finished in
            DispatchQueue.main.async {
                guard let self else { return }
                self.outputPipe?.fileHandleForReading.readabilityHandler = nil
                self.backend = nil
                self.outputPipe = nil
                self.removeRuntimeState()
                if self.terminating {
                    NSApp.reply(toApplicationShouldTerminate: true)
                    Darwin.exit(EXIT_SUCCESS)
                } else {
                    self.closeSafariTabs()
                    if finished.terminationStatus != 0 {
                        self.fail("The local PDF Studio engine stopped unexpectedly (status \(finished.terminationStatus)).")
                    }
                    Darwin.exit(finished.terminationStatus == 0 ? EXIT_SUCCESS : EXIT_FAILURE)
                }
            }
        }
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            DispatchQueue.main.async { self?.consume(data) }
        }

        do {
            try process.run()
            backend = process
            outputPipe = pipe
        } catch {
            fail("The local PDF Studio engine could not start: \(error.localizedDescription)")
        }
    }

    private func consume(_ data: Data) {
        outputBuffer.append(data)
        while let newline = outputBuffer.firstIndex(of: 0x0a) {
            let lineData = outputBuffer[..<newline]
            outputBuffer.removeSubrange(...newline)
            guard let line = String(data: lineData, encoding: .utf8) else { continue }
            let prefix = "PDF Studio is ready: "
            if line.hasPrefix(prefix), let url = URL(string: String(line.dropFirst(prefix.count))) {
                serviceURL = url
                writeRuntimeState(url)
                openInSafari(url)
            }
        }
    }

    private func openInSafari(_ url: URL) {
        if activateExistingSafariTab(url) { return }
        guard let safari = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.Safari") else {
            fail("Safari is not available. PDF Studio is running at \(url.absoluteString)")
            return
        }
        NSWorkspace.shared.open([url], withApplicationAt: safari, configuration: NSWorkspace.OpenConfiguration()) { _, error in
            if let error { self.fail("Safari could not open PDF Studio: \(error.localizedDescription)") }
        }
    }

    private func activateExistingSafariTab(_ url: URL) -> Bool {
        let script = #"""
on run argv
    set targetURL to item 1 of argv
    tell application "Safari"
        repeat with w in every window
            repeat with t in every tab of w
                if URL of t is targetURL then
                    set current tab of w to t
                    set index of w to 1
                    activate
                    return "found"
                end if
            end repeat
        end repeat
    end tell
    return ""
end run
"""#
        guard let result = runAppleScript(script, arguments: [url.absoluteString]) else { return false }
        return result.status == 0 && result.output.trimmingCharacters(in: .whitespacesAndNewlines) == "found"
    }

    private func stopBackend() {
        guard let process = backend, process.isRunning else { return }
        kill(process.processIdentifier, SIGINT)
    }

    private func closeSafariTabs() {
        guard let url = serviceURL?.absoluteString else { return }
        let script = #"""
on run argv
    set targetURL to item 1 of argv
    tell application "Safari"
        repeat with w in every window
            repeat with t in every tab of w
                if URL of t is targetURL then close t
            end repeat
        end repeat
    end tell
end run
"""#
        _ = runAppleScript(script, arguments: [url])
    }

    private func runAppleScript(_ script: String, arguments: [String], timeout: TimeInterval = 2.0) -> (status: Int32, output: String)? {
        let process = Process()
        let pipe = Pipe()
        let finished = DispatchSemaphore(value: 0)
        process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
        process.arguments = ["-e", script] + arguments
        process.standardOutput = pipe
        process.standardError = Pipe()
        process.terminationHandler = { _ in finished.signal() }
        do {
            try process.run()
        } catch {
            return nil
        }
        if finished.wait(timeout: .now() + timeout) == .timedOut {
            process.terminate()
            if finished.wait(timeout: .now() + 0.5) == .timedOut {
                kill(process.processIdentifier, SIGKILL)
                _ = finished.wait(timeout: .now() + 0.5)
            }
        }
        guard !process.isRunning else { return nil }
        let output = pipe.fileHandleForReading.readDataToEndOfFile()
        return (process.terminationStatus, String(data: output, encoding: .utf8) ?? "")
    }

    private func runtimeStateURL() -> URL? {
        dataDirectory?.appendingPathComponent("runtime.json")
    }

    private func writeRuntimeState(_ url: URL) {
        guard let destination = runtimeStateURL(), let process = backend else { return }
        let record: [String: Any] = [
            "pid": process.processIdentifier,
            "url": url.absoluteString,
            "version": Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? ""
        ]
        if let data = try? JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: destination, options: .atomic)
        }
    }

    private func removeRuntimeState() {
        guard let destination = runtimeStateURL() else { return }
        try? FileManager.default.removeItem(at: destination)
    }

    private func fail(_ message: String) {
        let alert = NSAlert()
        alert.alertStyle = .critical
        alert.messageText = "PDF Studio"
        alert.informativeText = message
        alert.runModal()
    }
}

let application = NSApplication.shared
let delegate = PDFStudioDelegate()
application.delegate = delegate
application.setActivationPolicy(.regular)
application.run()
