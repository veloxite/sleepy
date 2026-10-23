"""Keep installed app resources separate from persistent user data."""
import os
import sys
from pathlib import Path, PurePosixPath

RESOURCE_DIR = Path(__file__).resolve().parent


def user_data_dir(*, frozen=None, platform=None, environ=None, home=None):
    frozen = getattr(sys, 'frozen', False) if frozen is None else frozen
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if not frozen:
        return RESOURCE_DIR / 'data'  # Preserve existing source users' chats.
    if platform == 'win32':
        return Path(environ.get('LOCALAPPDATA') or home / 'AppData' / 'Local') / 'Sleepy'
    if platform == 'darwin':
        return home / 'Library' / 'Application Support' / 'Sleepy'
    xdg = Path(environ.get('XDG_DATA_HOME', ''))
    return (xdg if PurePosixPath(environ.get('XDG_DATA_HOME', '')).is_absolute() else home / '.local' / 'share') / 'Sleepy'


def load_source_environment():
    # A distributed app must never discover somebody else's .env near its exe.
    if not getattr(sys, 'frozen', False):
        from dotenv import load_dotenv
        load_dotenv(RESOURCE_DIR / '.env')


def relaunch_command(root=RESOURCE_DIR):
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--open']
    python = root / 'venv' / 'Scripts' / 'pythonw.exe'
    return [str(python if python.exists() else sys.executable), str(root / 'desktop_agent.py'), '--open']
