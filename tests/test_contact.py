import unittest
from types import SimpleNamespace

from nuke_tools.contact import CONTACT_ALPHA, CONTACT_MASK, find_contact


class ContactMatteTests(unittest.TestCase):
    def evaluate(self, expression, **values):
        parent = SimpleNamespace(contact_y=100, contact_band=5,
                                 contact_density=0.5, contact_strength=1)
        return eval(expression, {"__builtins__": {}}, dict(
            parent=parent, a=values.get("a", 1), y=values.get("y", 100.5),
            clamp=lambda value, low, high: max(low, min(high, value)), max=max))

    def test_band_excludes_below_ground_and_lifted_alpha(self):
        for y, expected in ((99.5, 0), (100, 1), (100.5, .9), (102.5, .5), (105, 0), (130.5, 0)):
            self.assertAlmostEqual(self.evaluate(CONTACT_MASK, y=y), expected)

    def test_transparent_and_partial_alpha(self):
        self.assertEqual(self.evaluate(CONTACT_MASK, a=0), 0)
        self.assertEqual(self.evaluate(CONTACT_MASK, a=0.25, y=100), 0.25)
        self.assertEqual(self.evaluate(CONTACT_ALPHA, a=0), 0)
        self.assertEqual(self.evaluate(CONTACT_ALPHA, a=0.5), 0.25)

    def test_strength_can_disable_contact(self):
        parent = SimpleNamespace(contact_density=0.8, contact_strength=0)
        result = eval(CONTACT_ALPHA, {"__builtins__": {}}, dict(
            parent=parent, a=1, clamp=lambda value, low, high: max(low, min(high, value))))
        self.assertEqual(result, 0)

    def test_raised_foot_loses_patch_while_planted_foot_remains(self):
        planted = [self.evaluate(CONTACT_MASK, y=row + .5) for row in range(100, 104)]
        raised = [self.evaluate(CONTACT_MASK, y=row + .5) for row in range(106, 110)]
        self.assertGreater(sum(planted), 0)
        self.assertEqual(sum(raised), 0)

    def test_fade_is_monotonic_above_floor(self):
        samples = [self.evaluate(CONTACT_MASK, y=100 + offset * .5) for offset in range(12)]
        self.assertEqual(samples, sorted(samples, reverse=True))


class ContactTests(unittest.TestCase):
    def test_lowest_occupied_row(self):
        rows = [0, 0.0001, 0.03, 0.5, 0]
        self.assertEqual(find_contact(len(rows), rows.__getitem__, 0.001), 2)

    def test_empty_frame(self):
        self.assertIsNone(find_contact(10, lambda row: 0, 0.001))

    def test_moving_silhouette(self):
        for bottom in (0, 12, 4, 19):
            self.assertEqual(find_contact(20, lambda row: 0.1 if row >= bottom else 0, 0.001), bottom)

    def test_threshold_can_reject_noise(self):
        rows = [0.002, 0, 0.1]
        self.assertEqual(find_contact(3, rows.__getitem__, 0.005), 2)

    def test_invalid_inputs(self):
        for height, threshold in ((0, 0.1), (10, 0), (10, 1)):
            with self.assertRaises(ValueError):
                find_contact(height, lambda row: 0, threshold)
