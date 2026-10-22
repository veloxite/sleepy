import unittest
from PySide6.QtCore import QRect
from music_player import music_query
from windows_integration import tile_rects
from desktop_actions import explicit_action

class MusicWorkspaceTests(unittest.TestCase):
    def test_mood_and_exact_track(self):
        self.assertIn('DJ mix',music_query('some party music'))
        self.assertIn('instrumental',music_query('study music'))
        self.assertEqual(music_query('Piano Man by Billy Joel'),'Piano Man by Billy Joel')

    def test_layout_covers_monitor_without_overlap(self):
        area=QRect(-1920,0,1920,1040)
        for count in range(1,11):
            rects=[QRect(*r) for r in tile_rects(area,count)]
            self.assertEqual(len(rects),count)
            self.assertEqual(sum(r.width()*r.height() for r in rects),area.width()*area.height())
            for i,r in enumerate(rects):
                self.assertTrue(area.contains(r))
                for other in rects[i+1:]:self.assertFalse(r.intersects(other))

if __name__=='__main__':unittest.main()
