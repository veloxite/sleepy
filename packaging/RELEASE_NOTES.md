Sleepy's first desktop preview. Install the app, open **Settings → Models & APIs**,
choose a provider, and enter your own API key. Python and .env files are not required.

- **Windows:** download `windows-x64-setup.exe`, or extract the portable ZIP and open `Sleepy.exe`.
- **Mac:** choose `macos-arm64.zip` for Apple Silicon or `macos-x64.zip` for Intel. Extract and move Sleepy.app to Applications.
- **Linux:** the `.deb` targets Ubuntu 24.04 or compatible systems. The tarball is also available; extract it and open `Sleepy`.

These early builds are unsigned. macOS builds are not notarized; Gatekeeper can block them.
Use System Settings → Privacy & Security → Open Anyway only after checking the download source.
Windows may show a SmartScreen reputation warning.

macOS/Linux are experimental. Automated renderer tests do not replace testing microphone,
screen recording, key storage, and music on real devices. Linux screen capture is intended
for X11; Wayland capture support varies. Window tiling is Windows-only.

Keys stay in the operating system credential store. Screenshots and prompts are sent to
the provider you choose when you request an answer. Online voices and music need internet.
Provider use may have its own charges. No API key or paid subscription is included.

See DISTRIBUTION.md for system requirements, data locations, rebuild instructions, and licenses.
