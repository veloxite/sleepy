# macOS and Linux 0.2.1 test builds

These builds are candidates for personal testing, not a claim that every desktop
and device has been validated. The released Windows v0.1.0 downloads are unchanged.

Use the [v0.2.1 testing downloads](https://github.com/veloxite/sleepy/releases/tag/v0.2.1).
This update also includes a Windows installer with the settings fixes.
In Models & APIs, both Save connection and Save changes save the chat and screen
models and activate that connection. Close and reopen Settings, then restart
Sleepy and verify both models are retained before testing chat and screen input.

## macOS

Choose arm64 for Apple Silicon or x64 for Intel. Open the DMG, drag Sleepy to
Applications, eject the disk image, then launch from Applications. ZIP builds are
also available. The current build machines target macOS 14+ for Apple Silicon
and macOS 15+ for Intel; older systems are not claimed as supported.

The app is not Apple-notarized. If blocked, inspect the download source and use
System Settings → Privacy & Security → Open Anyway. Do not disable Gatekeeper.
For Screen On, allow Sleepy in Screen Recording (the name may include System
Audio on newer macOS), then restart it. For push-to-talk, allow Microphone.
For workspace window arrangement, allow Accessibility. Other applications can
refuse resizing, especially while in native full-screen mode.

## Linux

The current x64 packages require glibc 2.39 or newer. Mint 22 / Ubuntu 24.04 and
newer compatible releases meet this baseline; older Mint versions are not yet
supported by these binaries. Use the DEB with Mint/Ubuntu and the RPM with a
compatible recent Fedora system. Arch users can extract the portable tarball
and run Sleepy from the extracted folder. Keep its bundled files together.
An AppImage is not yet provided. The portable tarball still needs system desktop,
graphics, audio, and credential-vault libraries; it is not dependency-free.

On a recent Fedora release install with `sudo dnf install ./Sleepy-0.2.0-linux-x64.rpm`.
On Mint 22 / Ubuntu 24.04 install with `sudo apt install ./Sleepy-0.2.0-linux-x64.deb`.
These commands let the package manager install required system dependencies.
Portable users should install the equivalent Qt/X11 graphics dependencies and
PipeWire/PulseAudio libraries through their own distribution's package manager.

Wayland screen capture uses Qt's system sharing picker. Approve the requested
display. PipeWire, xdg-desktop-portal, and the portal backend for your desktop
(GNOME, KDE, Cinnamon/Xapp, etc.) must be installed and running. Cancellation
does not send a text-only AI request. Screen Off needs no capture permission.
The current native capture path uses one display per request; choose a new
source when needed. On X11, capture uses the existing Pillow backend.

Use GNOME Keyring or a Secret Service-compatible vault such as a configured
KWallet. Unlock it when prompted. Sleepy does not use a plaintext credential
fallback. Microphone and playback require PipeWire or PulseAudio. Natural online
voices use the network; offline voices depend on installed system speech engines.

For automatic X11 workspace arrangement, install wmctrl through the distribution's
package manager. On Wayland use native desktop tiling; allowing screen sharing
does not grant general window-control access. Some GNOME sessions do not show
tray icons without an extension; launch Sleepy again to reopen its existing
instance if the companion was hidden.

## Acceptance checklist

Record the OS version, chip/CPU architecture, desktop name, and X11/Wayland session.
Use test documents and a provider key with appropriate spending limits.

- Install, launch, close to the companion, reopen, quit, and relaunch.
- Add a provider, save a key, restart, and confirm the connection still works.
- Send text with Screen Off and a question about a synthetic screen with Screen On.
- Deny/cancel screen access, then allow and retry. Confirm no request was sent on failure.
- Select a focus area; test scaling, a second monitor, and changed display dimensions.
- Record push-to-talk, release, read a reply aloud, and test audio-device changes.
- Play, pause, resume, seek, and close local music; test SoundCloud separately.
- Open an app, selected browser, and saved workspace; check window arrangement.
- Render code, LaTeX, Mermaid, and flashcards; rename/delete/reopen a saved chat.
- Leave only the ball idle, reopen after a minute, and confirm responsiveness.
- Remove a saved connection; uninstall. Local data intentionally remains unless removed separately.

Report failures with exact steps and OS information, never API keys or personal
screen captures. Automated startup checks do not replace these hardware tests.
