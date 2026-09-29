import Cocoa
import FlutterMacOS

@main
class AppDelegate: FlutterAppDelegate {
  private var desktopChannel: FlutterMethodChannel?
  private weak var dashboardWindow: NSWindow?
  private var statusItem: NSStatusItem?
  private let trackMenuItem = NSMenuItem(title: "Waiting for playback", action: nil, keyEquivalent: "")
  private let toggleMenuItem = NSMenuItem(title: "Pause scrobbling", action: nil, keyEquivalent: "")
  private var terminationRequested = false

  func configureDesktop(window: NSWindow, messenger: FlutterBinaryMessenger) {
    dashboardWindow = window
    let channel = FlutterMethodChannel(name: "py_scrobbler/desktop", binaryMessenger: messenger)
    desktopChannel = channel
    channel.setMethodCallHandler { [weak self] call, result in
      guard let self = self else { return result(nil) }
      switch call.method {
      case "updateStatus":
        let arguments = call.arguments as? [String: Any]
        let track = arguments?["track"] as? String ?? ""
        self.trackMenuItem.title = track.isEmpty ? "Waiting for playback" : track
        let enabled = arguments?["enabled"] as? Bool ?? true
        self.toggleMenuItem.title = enabled ? "Pause scrobbling" : "Enable scrobbling"
        let connected = arguments?["connected"] as? Bool ?? false
        let busy = arguments?["busy"] as? Bool ?? false
        self.toggleMenuItem.isEnabled = connected && !busy && !self.terminationRequested
        result(nil)
      case "quitReady":
        result(nil)
        if self.terminationRequested {
          NSApp.reply(toApplicationShouldTerminate: true)
        }
      default:
        result(FlutterMethodNotImplemented)
      }
    }
    installStatusMenu()
  }

  private func installStatusMenu() {
    let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
    item.button?.image = NSImage(systemSymbolName: "music.note", accessibilityDescription: "Scrobbler")
    item.button?.toolTip = "Scrobbler"
    let menu = NSMenu()
    menu.autoenablesItems = false
    trackMenuItem.isEnabled = false
    menu.addItem(trackMenuItem)
    menu.addItem(.separator())
    let openItem = NSMenuItem(title: "Open dashboard", action: #selector(showDashboard), keyEquivalent: "")
    openItem.target = self
    menu.addItem(openItem)
    toggleMenuItem.isEnabled = false
    toggleMenuItem.action = #selector(toggleScrobbling)
    toggleMenuItem.target = self
    menu.addItem(toggleMenuItem)
    menu.addItem(.separator())
    let quitItem = NSMenuItem(title: "Quit Scrobbler", action: #selector(requestQuit), keyEquivalent: "q")
    quitItem.target = self
    menu.addItem(quitItem)
    item.menu = menu
    statusItem = item
  }

  @objc private func showDashboard() {
    dashboardWindow?.deminiaturize(nil)
    dashboardWindow?.makeKeyAndOrderFront(nil)
    NSApp.activate(ignoringOtherApps: true)
    desktopChannel?.invokeMethod("showDashboard", arguments: nil)
  }

  @objc private func toggleScrobbling() {
    desktopChannel?.invokeMethod("toggleScrobbling", arguments: nil)
  }

  @objc private func requestQuit() {
    NSApp.terminate(nil)
  }

  override func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
    guard let channel = desktopChannel else { return .terminateNow }
    if !terminationRequested {
      terminationRequested = true
      toggleMenuItem.isEnabled = false
      // Defer delivery until AppKit has entered its deferred termination state.
      DispatchQueue.main.async {
        channel.invokeMethod("quitRequested", arguments: nil) { response in
          // Permit exit if Dart has not initialized its lifecycle handler yet.
          if let response = response as? NSObject, response == FlutterMethodNotImplemented {
            sender.reply(toApplicationShouldTerminate: true)
          }
        }
      }
    }
    return .terminateLater
  }

  override func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
    return false
  }

  override func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
    showDashboard()
    return true
  }

  override func applicationSupportsSecureRestorableState(_ app: NSApplication) -> Bool {
    return true
  }
}
