import unittest
from types import SimpleNamespace

from nuke_tools.despill_math import EDGE_OPACITY_FACTOR, green_expression


class DespillTests(unittest.TestCase):
    def test_edge_opacity(self):
        def factor(core, opacity):
            return eval(EDGE_OPACITY_FACTOR, {'__builtins__': {}}, dict(
                a=core, parent=SimpleNamespace(extend_opacity=opacity),
                clamp=lambda x, low, high: min(high, max(low, x))))

        for core in (0, .25, .5, 1):
            self.assertEqual(factor(core, 1), 1)
        self.assertEqual(factor(1, 0), 1)
        self.assertEqual(factor(0, 0), 0)
        self.assertEqual(factor(0, .4), .4)
        self.assertAlmostEqual(factor(.5, .4), .7)
        self.assertEqual(factor(0, -1), 0)
        self.assertEqual(factor(0, 2), 1)

    def correct(self, rgb, **settings):
        defaults = dict(balance=.5, threshold=0, core_strength=1, edge_strength=1)
        defaults.update(settings)
        return eval(green_expression('core_strength'), {'__builtins__': {}}, dict(
            r=rgb[0], g=rgb[1], b=rgb[2], parent=SimpleNamespace(**defaults),
            max=max, clamp=lambda x, low, high: min(high, max(low, x))))

    def test_green_is_detected_and_removed(self):
        self.assertAlmostEqual(self.correct((.2, .8, .4)), .3)

    def test_neutral_and_non_green_are_preserved(self):
        for rgb in ((.5, .5, .5), (.8, .2, .3), (2, 2, 2)):
            self.assertEqual(self.correct(rgb), rgb[1])

    def test_strength_and_tolerance(self):
        self.assertEqual(self.correct((.2, .8, .4), core_strength=0), .8)
        self.assertAlmostEqual(self.correct((.2, .8, .4), core_strength=.5), .55)
        self.assertAlmostEqual(self.correct((.2, .8, .4), threshold=.1), .4)
        self.assertEqual(self.correct((.2, .8, .4), threshold=1), .8)

    def test_reference_balance_and_hdr(self):
        self.assertAlmostEqual(self.correct((.2, .8, .4), balance=0), .2)
        self.assertAlmostEqual(self.correct((.2, .8, .4), balance=1), .4)
        self.assertEqual(self.correct((2, 4, 2)), 2)

    def test_region_names_are_explicit(self):
        self.assertIn('parent.edge_strength', green_expression('edge_strength'))
        with self.assertRaises(ValueError):
            green_expression('other')
