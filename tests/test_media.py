import tempfile
import unittest
from pathlib import Path

from nuke_tools.media import audit_frames, replace_prefix


class MediaTests(unittest.TestCase):
    def test_sequence_gap(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [str(Path(folder) / ("plate.%04d.exr" % frame)) for frame in range(1, 4)]
            Path(paths[0]).touch()
            Path(paths[2]).touch()
            result = audit_frames(lambda frame: paths[frame - 1], 1, 3)
            self.assertEqual(result.checked, 3)
            self.assertEqual(result.missing, (paths[1],))

    def test_movie_checked_once(self):
        result = audit_frames(lambda frame: "/missing/clip.mov", 1, 100)
        self.assertEqual(result.checked, 1)
        self.assertEqual(result.missing, ("/missing/clip.mov",))

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            audit_frames(str, 10, 1)

    def test_windows_relink_preserves_padding(self):
        self.assertEqual(replace_prefix(r"D:\SHOW\plates\shot.%04d.exr", "d:/show", "E:/project"),
                         "E:/project/plates/shot.%04d.exr")

    def test_prefix_boundary(self):
        self.assertEqual(replace_prefix("D:/showcase/a.exr", "D:/show", "E:/new"), "D:/showcase/a.exr")

    def test_unc_and_posix(self):
        self.assertEqual(replace_prefix("//SERVER/share/a.exr", "//server/share", "D:/local"), "D:/local/a.exr")
        self.assertEqual(replace_prefix("/Show/a.exr", "/show", "/new"), "/Show/a.exr")

    def test_expression_rejected(self):
        with self.assertRaises(ValueError):
            replace_prefix("[value root.name]/a.exr", "D:/show", "E:/new")
