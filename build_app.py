"""Build a standalone app on the target OS using the allowlisted spec."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def prepare_licenses():
    target = ROOT / 'build' / 'licenses'
    target.mkdir(parents=True, exist_ok=True)
    inventory = []
    for dist in metadata.distributions():
        name = dist.metadata['Name']
        inventory.append({'name': name, 'version': dist.version,
                          'license': dist.metadata.get('License-Expression') or dist.metadata.get('License', ''),
                          'project_urls': dist.metadata.get_all('Project-URL') or []})
        for entry in dist.files or []:
            parts = entry.parts
            if any(p.endswith('.dist-info') for p in parts) and any(
                    word in entry.name.lower() for word in ('license', 'copying', 'notice', 'copyright')):
                source = Path(dist.locate_file(entry))
                if source.is_file():
                    # Retain subdirectories so differently named bundled notices survive.
                    index = next(i for i, p in enumerate(parts) if p.endswith('.dist-info'))
                    dest = target / name / Path(*parts[index + 1:])
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
    (target / 'dependency-versions.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.exists():
        shutil.copy2(python_license, target / 'Python-LICENSE.txt')
    else:
        import sysconfig
        candidate = Path(sysconfig.get_path('stdlib')) / 'LICENSE.txt'
        if candidate.exists():
            shutil.copy2(candidate, target / 'Python-LICENSE.txt')
    for source in (ROOT / 'packaging' / 'licenses').glob('*'):
        shutil.copy2(source, target / source.name)


def package():
    version = (ROOT / 'VERSION').read_text().strip()
    arch = 'arm64' if platform.machine().lower() in ('arm64', 'aarch64') else 'x64'
    output = ROOT / 'dist' / 'installers'
    output.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'win32':
        shutil.make_archive(str(output / f'Sleepy-{version}-windows-{arch}-portable'), 'zip', ROOT / 'dist', 'Sleepy')
        compiler = shutil.which('ISCC') or 'C:/Program Files (x86)/Inno Setup 6/ISCC.exe'
        if not Path(compiler).is_file():
            raise SystemExit('Portable ZIP built. Install Inno Setup 6 to also build the Windows installer.')
        subprocess.run([compiler, '/DAppVersion=' + version, str(ROOT / 'packaging' / 'windows.iss')], check=True)
    elif sys.platform == 'darwin':
        stage = ROOT / 'build' / 'dmg-stage'
        stage.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ditto', str(ROOT / 'dist' / 'Sleepy.app'), str(stage / 'Sleepy.app')], check=True)
        applications = stage / 'Applications'
        if not applications.exists():
            applications.symlink_to('/Applications')
        subprocess.run(['hdiutil', 'create', '-volname', 'Sleepy', '-srcfolder', str(stage),
                        '-ov', '-format', 'UDZO', str(output / f'Sleepy-{version}-macos-{arch}.dmg')], check=True)
        # ditto preserves bundle symlinks and executable permissions.
        subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
                        str(ROOT / 'dist' / 'Sleepy.app'), str(output / f'Sleepy-{version}-macos-{arch}.zip')], check=True)
    else:
        with tarfile.open(output / f'Sleepy-{version}-linux-{arch}.tar.gz', 'w:gz') as archive:
            archive.add(ROOT / 'dist' / 'Sleepy', arcname='Sleepy')
        if shutil.which('dpkg-deb'):
            package_root = ROOT / 'build' / 'deb'
            app_dir = package_root / 'opt' / 'sleepy'
            shutil.copytree(ROOT / 'dist' / 'Sleepy', app_dir, dirs_exist_ok=True)
            control = package_root / 'DEBIAN'
            control.mkdir(parents=True, exist_ok=True)
            (control / 'control').write_text(
                f'Package: sleepy\nVersion: {version}\nArchitecture: {"arm64" if arch == "arm64" else "amd64"}\n'
                'Maintainer: veloxite <noreply@github.com>\nSection: utils\nPriority: optional\n'
                'Depends: libc6 (>= 2.39), libgl1, libegl1, libnss3, libxkbcommon0, libxkbcommon-x11-0, '
                'libxcb-cursor0, libxcb-icccm4, libxcb-keysyms1, libxcb-shape0, libxcb-xinerama0, '
                'libasound2t64, libpulse0, libdbus-1-3, libfontconfig1, libxcomposite1, libxdamage1, libxrandr2, libxtst6\n'
                'Recommends: gnome-keyring, scrot, xdg-utils\n'
                'Description: Sleepy desktop AI companion\n Local chats and your own model-provider keys.\n', encoding='utf-8')
            desktop = package_root / 'usr' / 'share' / 'applications' / 'sleepy.desktop'
            desktop.parent.mkdir(parents=True, exist_ok=True)
            desktop.write_text('[Desktop Entry]\nType=Application\nName=Sleepy\nExec=/opt/sleepy/Sleepy\n'
                               'Icon=sleepy\nTerminal=false\nCategories=Utility;Education;\n', encoding='utf-8')
            icon = package_root / 'usr' / 'share' / 'icons' / 'hicolor' / '256x256' / 'apps' / 'sleepy.png'
            icon.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / 'assets' / 'sleepy.png', icon)
            subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(package_root),
                            str(output / f'Sleepy-{version}-linux-{arch}.deb')], check=True)
            if shutil.which('rpmbuild'):
                rpmroot = ROOT / 'build' / 'rpm'
                for directory in ('BUILD', 'RPMS', 'SOURCES', 'SPECS', 'SRPMS'):
                    (rpmroot / directory).mkdir(parents=True, exist_ok=True)
                spec = rpmroot / 'SPECS' / 'sleepy.spec'
                spec.write_text(f'''Name: sleepy
Version: {version}
Release: 1
Summary: Desktop AI companion using your own provider keys
License: MIT
URL: https://github.com/veloxite/sleepy
AutoReqProv: no
Requires: glibc >= 2.39, libglvnd-glx, libglvnd-egl, nss, libxkbcommon-x11, xcb-util-cursor, xcb-util-wm, xcb-util-keysyms, libXcomposite, libXdamage, libXrandr, libXtst, alsa-lib, pulseaudio-libs, dbus-libs, fontconfig

%description
Sleepy desktop assistant. Requires a desktop session and unlocked credential vault.

%install
mkdir -p %{{buildroot}}
cp -a {package_root}/opt %{{buildroot}}/
cp -a {package_root}/usr %{{buildroot}}/

%files
/opt/sleepy
/usr/share/applications/sleepy.desktop
/usr/share/icons/hicolor/256x256/apps/sleepy.png
''', encoding='utf-8')
                subprocess.run(['rpmbuild', '--define', '_topdir ' + str(rpmroot),
                                '--define', '__os_install_post %{nil}', '-bb', str(spec)], check=True)
                for built in (rpmroot / 'RPMS').rglob('*.rpm'):
                    shutil.copy2(built, output / f'Sleepy-{version}-linux-{arch}.rpm')
    files = sorted(p for p in output.iterdir() if p.is_file() and p.suffix in ('.zip', '.gz', '.deb', '.exe', '.dmg', '.rpm'))
    checksums = []
    for path in files:
        with path.open('rb') as stream:
            checksums.append(hashlib.file_digest(stream, 'sha256').hexdigest() + '  ' + path.name)
    (output / 'SHA256SUMS.txt').write_text('\n'.join(checksums) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', action='store_true', help='Archive/install an already tested build')
    args = parser.parse_args()
    if args.package:
        package()
    else:
        prepare_licenses()
        subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', str(ROOT / 'Sleepy.spec')], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
