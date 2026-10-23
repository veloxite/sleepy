# Download and install Sleepy

Version 0.3.0 provides Windows and Linux downloads, plus experimental macOS builds.
Linux Mint was manually tested with v0.2.1, except microphone input. Other Linux
distributions and macOS still need real-device testing. Full installation,
permission and troubleshooting instructions are included directly in the README
and release notes.

Get downloads from [GitHub Releases](https://github.com/veloxite/sleepy/releases).
GitHub's automatically generated **Source code** archives are for developers;
choose a Sleepy app asset for your operating system instead.

| System | Download | Open it |
| --- | --- | --- |
| Windows 10/11, 64-bit | `windows-x64-setup.exe` | Run the installer, then open Sleepy from Start. No administrator account required. |
| Windows portable | `windows-x64-portable.zip` | Extract the entire folder, then run `Sleepy.exe`. Keep `_internal` beside it. |
| Mint 22 / Ubuntu 24.04+, x64 | `linux-x64.deb` | Double-click and install required dependencies. |
| Recent Fedora, x64 (untested) | `linux-x64.rpm` | Install with the package manager. |
| Other compatible Linux, x64 (untested) | `linux-x64.tar.gz` | Extract the complete folder; requires glibc 2.39+. |
| Apple Silicon macOS 14+, experimental | `macos-arm64.dmg` | Drag Sleepy to Applications. |
| Intel macOS 15+, experimental | `macos-x64.dmg` | Drag Sleepy to Applications. |

No Python install, source edits, or `.env` file is needed. In Sleepy, open
**Models & APIs → Add connection**, select a provider, enter your own
key, load/select models, and use the connection. Provider accounts and usage are
separate from Sleepy. Ollama requires a separately installed local model server.

## Release status and platform limits

The Windows release has been tested on a Windows laptop. It is unsigned, so
Windows can show a reputation warning. Mac bundles are ad-hoc signed,
not Apple notarized; Gatekeeper may block them.
If you trust the release, use macOS Privacy & Security → Open Anyway. Do not
disable security protection globally. No signing subscription is required to
build the source, but trusted commercial signing is not configured here.

macOS and untested Linux desktops need testing on real user machines. The build workflow checks that
the packaged runtime and offline chat renderer start; it cannot verify real
microphones, speakers, screen permissions, or every provider account.
Mac builds target macOS 14+ (Apple Silicon) and macOS 15+ (Intel).
Linux targets Ubuntu 24.04/glibc 2.39 or later, with a running desktop and an
unlocked Secret Service credential vault such as GNOME Keyring. No insecure
plaintext-key fallback is installed. X11 is the intended Linux screen-capture
environment; Wayland uses the system screen-sharing portal and can restrict tiling.
Window arrangement on macOS requires Accessibility; X11 uses wmctrl.
On macOS allow Screen Recording and Microphone access when using those features.
Online voices and music depend on external services and internet access.

## Data and updates

Installed apps store chats, preferences and custom logos in:

- Windows: `%LOCALAPPDATA%\Sleepy`
- macOS: `~/Library/Application Support/Sleepy`
- Linux: `$XDG_DATA_HOME/Sleepy`, or `~/.local/share/Sleepy`

API keys remain in the OS credential vault. Installer updates and uninstalling
the app do not delete chats or keys. Delete saved connections in Settings before
uninstalling if you also want to remove their keys. Close Sleepy before updating.
There is no automatic updater; download a new release and install/replace the app.

Existing source users retain their current `data/` directory. To move your own
chats to an installed build, quit both versions, back up `data/`, then copy its
contents into the installed app's data directory. Do not overwrite a newer
database. Legacy `.env` keys must be re-entered in Settings; saved vault keys
continue working on the same account/computer. Do not upload this data to GitHub.
The portable Windows build also stores personal data in the user profile, not
inside the extracted app folder.

## Rebuild and release

Build separately on each OS; PyInstaller does not cross-compile. Use Python 3.12+
and an isolated environment, then:

```sh
python -m pip install -r requirements-build.txt
python -m unittest discover -v -p "test_*.py"
python build_app.py
```

Run the executable with `--self-test /absolute/path/to/report.json` and require
`"ok": true` in the report. On macOS use `dist/Sleepy.app/Contents/MacOS/Sleepy`.
This check uses temporary data and no API calls. Then `python build_app.py --package`
creates downloads in `dist/installers/`. Windows requires Inno Setup 6 on PATH
or in its standard installation directory for the setup executable. Linux uses
`dpkg-deb` when available. Each build includes a dependency-version inventory,
licenses, and SHA-256 download checksums.

The **Build desktop apps** GitHub Actions workflow can be run manually. A tag
matching VERSION (for example `v0.3.0`) builds the platform matrix and creates a
**draft release** only after all checks pass. Review and test the downloaded app,
then publish the draft. Label experimental targets and state exactly which
devices were tested. The unit workflow also runs on ordinary
pushes and pull requests.

## Dependency licenses

Sleepy's source is MIT. Bundled dependencies keep their own licenses, included
under `_internal/licenses` on Windows/Linux and in the Mac bundle's resources.
Qt/PySide are distributed as separate shared libraries, not statically linked.
Users may replace these libraries with compatible modified versions and rebuild
Sleepy; the MIT license imposes no restriction on that or on reverse engineering
for debugging such modifications. Keep dependency notices with redistributed apps.

Exact dependency versions are recorded in `licenses/dependency-versions.json`.
Corresponding upstream sources: [Qt](https://download.qt.io/archive/qt/),
[PySide](https://download.qt.io/official_releases/QtForPython/), and
[Python packages](https://pypi.org/). Qt's module-specific and third-party terms
are described in [Qt licensing](https://doc.qt.io/qt-6/licensing.html) and
[Qt WebEngine licensing](https://doc.qt.io/qt-6/qtwebengine-licensing.html).
See THIRD_PARTY_NOTICES.md and bundled license files for further details.
