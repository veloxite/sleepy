# Build on each target OS; never bundle a user's data or .env.
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

root = Path(SPECPATH)
datas = [(str(root / 'ui'), 'ui'), (str(root / 'assets'), 'assets'),
         (str(root / 'LICENSE'), '.'), (str(root / 'THIRD_PARTY_NOTICES.md'), '.'),
         (str(root / 'build' / 'licenses'), 'licenses')]
hidden = collect_submodules('keyring.backends')
for name in ('openai', 'anthropic', 'edge-tts', 'yt-dlp', 'keyring'):
    datas += copy_metadata(name)
a = Analysis([str(root / 'desktop_agent.py')], pathex=[str(root)],
             datas=datas, hiddenimports=hidden, binaries=[],
             excludes=['tkinter', 'customtkinter', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Sleepy',
          debug=False, strip=False, upx=False, console=False,
          icon=str(root / 'assets' / 'sleepy.ico'),
          entitlements_file=str(root / 'packaging' / 'macos-entitlements.plist') if sys.platform == 'darwin' else None)
bundle = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Sleepy')
if sys.platform == 'darwin':
    app = BUNDLE(bundle, name='Sleepy.app', icon=str(root / 'assets' / 'sleepy.ico'),
                 bundle_identifier='io.github.veloxite.sleepy',
                 info_plist={'CFBundleShortVersionString': (root / 'VERSION').read_text().strip(),
                             'NSMicrophoneUsageDescription': 'Sleepy uses your microphone only while you hold push-to-talk.',
                             'NSScreenCaptureUsageDescription': 'Sleepy captures your selected screen only when you ask for screen context.',
                             'NSHighResolutionCapable': True})
