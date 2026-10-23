"""A macOS bundle's resource symlinks must not block its own UI."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QUrl
from sleepy_app import LocalPage


class NavigationTests(unittest.TestCase):
    def test_only_local_entry_document_is_allowed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'ui').mkdir()
            entry = root / 'ui' / 'index.html'
            entry.write_text('test')
            with patch('sleepy_app.BASE', root):
                self.assertTrue(LocalPage.acceptNavigationRequest(None, QUrl.fromLocalFile(str(entry)), None, True))
                self.assertFalse(LocalPage.acceptNavigationRequest(None, QUrl('https://example.com'), None, True))
                self.assertFalse(LocalPage.acceptNavigationRequest(None, QUrl.fromLocalFile(str(root / 'other.html')), None, True))

    def test_symlinked_bundle_resources_are_allowed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            resources = root / 'Resources'
            resources.mkdir()
            (resources / 'index.html').write_text('test')
            try:
                (root / 'ui').symlink_to(resources, target_is_directory=True)
            except OSError:
                self.skipTest('This Windows account cannot create symlinks')
            with patch('sleepy_app.BASE', root):
                self.assertTrue(LocalPage.acceptNavigationRequest(None, QUrl.fromLocalFile(str(resources / 'index.html')), None, True))
