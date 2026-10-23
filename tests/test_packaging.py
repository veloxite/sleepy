import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import app_paths


class PackagingTests(unittest.TestCase):
    def test_source_data_unchanged(self):
        self.assertEqual(app_paths.user_data_dir(frozen=False), app_paths.RESOURCE_DIR / 'data')

    def test_installed_data_locations(self):
        self.assertEqual(app_paths.user_data_dir(frozen=True, platform='win32', environ={'LOCALAPPDATA': '/profile/local'}, home='/home/a'), Path('/profile/local/Sleepy'))
        self.assertEqual(app_paths.user_data_dir(frozen=True, platform='darwin', environ={}, home='/home/a'), Path('/home/a/Library/Application Support/Sleepy'))
        self.assertEqual(app_paths.user_data_dir(frozen=True, platform='linux', environ={'XDG_DATA_HOME': '/profile/data'}, home='/home/a'), Path('/profile/data/Sleepy'))
        self.assertEqual(app_paths.user_data_dir(frozen=True, platform='linux', environ={'XDG_DATA_HOME': 'relative'}, home='/home/a'), Path('/home/a/.local/share/Sleepy'))

    def test_frozen_relaunch_has_no_python_script(self):
        with patch.object(sys, 'frozen', True, create=True):
            self.assertEqual(app_paths.relaunch_command(), [sys.executable, '--open'])

    def test_packaged_app_never_loads_dotenv(self):
        with patch.object(sys, 'frozen', True, create=True), patch('dotenv.load_dotenv') as load:
            app_paths.load_source_environment()
            load.assert_not_called()

    def test_bundle_does_not_include_private_data(self):
        from build_source import FILES
        self.assertNotIn('.env', FILES)
        self.assertIn('app_paths.py', FILES)
        self.assertIn('Sleepy.spec', FILES)


if __name__ == '__main__':
    unittest.main()
