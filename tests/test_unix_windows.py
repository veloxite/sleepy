import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import unix_windows


class UnixWindowTests(unittest.TestCase):
    def test_wayland_never_attempts_global_window_discovery(self):
        with patch('unix_windows.sys.platform', 'linux'), patch.dict(os.environ, {'XDG_SESSION_TYPE': 'wayland'}), patch('unix_windows.subprocess.run') as run:
            self.assertFalse(unix_windows.supported())
            self.assertEqual(unix_windows.windows(), {})
            run.assert_not_called()

    def test_x11_discovery_excludes_our_own_windows(self):
        with patch('unix_windows.sys.platform', 'linux'), patch.dict(os.environ, {'XDG_SESSION_TYPE': 'x11'}), patch('unix_windows.shutil.which', return_value='/usr/bin/wmctrl'), patch('unix_windows.os.getpid', return_value=123), patch('unix_windows.subprocess.run', return_value=SimpleNamespace(stdout='0x10 0 123 host Sleepy\n0x20 0 999 host Physics PDF\n')):
            self.assertEqual(unix_windows.windows(), {32: ('Physics PDF', '')})

    def test_layout_arguments_are_not_shell_commands(self):
        with patch('unix_windows.sys.platform', 'linux'), patch('unix_windows.subprocess.run') as run:
            unix_windows.move(32, (0, 10, 800, 600))
            self.assertEqual(run.call_args.args[0], ['wmctrl', '-ir', '0x20', '-e', '0,0,10,800,600'])
            self.assertNotIn('shell', run.call_args.kwargs)
