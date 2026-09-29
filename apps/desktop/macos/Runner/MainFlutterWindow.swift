import Cocoa
import FlutterMacOS

class MainFlutterWindow: NSWindow, NSWindowDelegate {
  override func awakeFromNib() {
    let flutterViewController = FlutterViewController()
    let windowFrame = self.frame
    self.contentViewController = flutterViewController
    self.setFrame(windowFrame, display: true)
    self.isReleasedWhenClosed = false
    self.delegate = self

    RegisterGeneratedPlugins(registry: flutterViewController)

    super.awakeFromNib()

    (NSApp.delegate as? AppDelegate)?.configureDesktop(
      window: self,
      messenger: flutterViewController.engine.binaryMessenger
    )
  }

  func windowShouldClose(_ sender: NSWindow) -> Bool {
    // Retain the Flutter engine and its owned backend while the window is hidden.
    sender.orderOut(nil)
    return false
  }
}
