# Sleepy 0.2.0 release candidate

Test builds for macOS and Linux, plus a Windows regression build. These downloads
have automated unit and packaged UI checks. Hardware permissions, audio, screen
capture, and window layout still require real-device acceptance testing.

- macOS arm64 (Apple Silicon, macOS 14+) or x64 (Intel, macOS 15+): open the DMG,
  drag Sleepy to Applications, then launch it there. ZIP bundles are also included.
- Linux x64 with glibc 2.39+: DEB for Mint 22 / Ubuntu 24.04 and compatible systems;
  RPM for recent Fedora; portable tarball for Arch and other compatible systems.
- Windows: installer or portable ZIP. The stable Windows 0.1.0 release remains available.

Read [installation and permission instructions](https://github.com/veloxite/sleepy/blob/main/CROSS_PLATFORM_TESTING.md)
before testing. macOS needs Screen Recording, Microphone, and Accessibility access
for the relevant features. The app is not Apple-notarized. Wayland screen capture
requires the system sharing picker, PipeWire, and a desktop portal backend.
Wayland window layout uses desktop-native tiling. Secure key storage requires an
unlocked system credential vault. No shared API key is included.

AppImage and older Linux library baselines are not included yet. Please report
the OS version, architecture, desktop/session type, and exact steps for any issue.
Do not include keys, private chats, or personal screenshots in public issues.
