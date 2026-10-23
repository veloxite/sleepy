import os
import unittest
from unittest.mock import patch
import platform_capture


class PlatformCaptureTests(unittest.TestCase):
    def test_windows_keeps_existing_capture_backend(self):
        with patch('platform_capture.sys.platform', 'win32'), patch('platform_capture.ImageGrab.grab', return_value='image') as grab:
            self.assertEqual(platform_capture.grab(all_screens=True), 'image')
            grab.assert_called_once_with(all_screens=True)

    def test_x11_keeps_existing_capture_backend(self):
        with patch('platform_capture.sys.platform', 'linux'), patch.dict(os.environ, {'XDG_SESSION_TYPE': 'x11'}), patch('platform_capture.ImageGrab.grab', return_value='image'):
            self.assertEqual(platform_capture.grab(), 'image')
