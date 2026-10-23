# Sleepy v0.3.0

Models & APIs, Workspaces, Plugins and Music now open their own panels. Settings holds personal preferences. API keys and model choices are saved together, with provider model discovery before saving. A first-run guide explains the main features. Window-state handling has been updated for fullscreen and returning from the ball.

Windows and Linux are normal release downloads. The maintainer reports successful testing of v0.2.1 on a friend's Linux Mint laptop, except microphone input (no input device was available). This does not establish compatibility with every distribution or verify the new v0.3.0 interface on that laptop. macOS downloads remain experimental pending real-device tests.

## Windows installation

Close Sleepy, download the x64 setup EXE, and run it. Open Sleepy from Start. For the portable ZIP, extract the complete folder before running Sleepy.exe. Existing chats and connections are retained. Builds are unsigned; if Windows displays a reputation warning, verify the download source and checksum before proceeding.

## Linux installation and permissions

For Linux Mint 22 / Ubuntu 24.04 and newer compatible x64 systems, download the DEB, double-click it, and choose Install Package. Accept required dependencies, then launch Sleepy from the application menu. Close any older running Sleepy first. No terminal is required when the graphical installer succeeds.

Alternatively, open a terminal in the download folder and run:

```bash
sudo apt install ./Sleepy-0.3.0-linux-x64.deb
```

An `_apt` unsandboxed-download warning alone does not mean installation failed. Check whether installation completed before retrying. If an error reports missing dependencies or incompatible versions, retain its exact text. Older Mint releases are not supported by this build.

Recent Fedora users can use `sudo dnf install ./Sleepy-0.3.0-linux-x64.rpm`. Arch and other compatible systems can extract the complete tar.gz and run the included Sleepy executable. Fedora and Arch have not been manually tested. All Linux downloads require x64, glibc 2.39 or newer, and compatible desktop libraries. There is no ARM Linux build.

On X11, screen capture and window controls generally work directly. On Wayland, choose your screen in the system sharing dialog; PipeWire and your desktop portal backend must be installed. Global window arrangement may be restricted, so use your desktop's tiling controls if needed. For voice, check Sound → Input and confirm the microphone level moves. Unlock the system credential vault when saving API keys.

If Sleepy will not launch, run `sleepy` from a terminal and report the output, distribution version and desktop session. If a browser download times out, retry or use `wget -c` followed by the asset's GitHub download URL. A download timeout does not indicate an installer failure.

## macOS installation and permissions — experimental

Use arm64 for Apple Silicon with macOS 14+, or x64 for Intel with macOS 15+. Open the DMG, drag Sleepy to Applications and launch it there. For ZIP downloads, extract the full app bundle and move it to Applications.

The app is unsigned and not notarized. If macOS blocks an app you trust, check System Settings → Privacy & Security for Open Anyway. Do not disable Gatekeeper globally. If that option is unavailable, report the exact message.

In System Settings → Privacy & Security, grant Screen Recording (or Screen & System Audio Recording) for screen context, Microphone for voice, and Accessibility for window controls. Quit and reopen Sleepy after changing permissions. For blank captures, recheck screen permission and try an ordinary, unprotected window. For microphone failures, check System Settings → Sound → Input. Permissions do not guarantee full feature compatibility; these downloads still need device testing.

## First use and troubleshooting

Open Models & APIs in the left rail. Choose a provider, enter your own key, and find available models. Choose chat and screen models, then Save connection and models. Screen context requires an image-capable model; some providers do not report this capability. The first-run guide covers browser selection, workspaces, plugins, voice and music.

If model loading fails, read the displayed error and check the key, API address, account permissions and provider quota. Your credentials are stored in the OS credential vault. No shared API key is included. Never publish API keys, private chats or personal screenshots in bug reports.
