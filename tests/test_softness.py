import math
import unittest
from types import SimpleNamespace

from nuke_tools.softness import CAST_DISTANCE, UNDER_DISTANCE, distance_mask, widening_mask


class SoftnessTests(unittest.TestCase):
    def sample(self, expression, y, **settings):
        values = dict(contact_y=100, reach=250, length=0.5,
                      distance_softness=1, falloff_distance=500,
                      under_offset=SimpleNamespace(y=-8))
        values.update(settings)
        return eval(expression, {"__builtins__": {}}, dict(
            parent=SimpleNamespace(**values), y=y, height=1000,
            max=max, abs=abs, pow=pow, sqrt=math.sqrt,
            clamp=lambda value, low, high: max(low, min(high, value))))

    def test_contact_uses_near_blur(self):
        self.assertEqual(self.sample(distance_mask(CAST_DISTANCE), 100), 0)

    def test_midpoint_endpoint_and_saturation(self):
        # A reach of 250 and length of .5 yields sqrt(1+.5^2) units
        # along the projection for every output Y pixel.
        scale = math.sqrt(1.25)
        for distance, expected in ((250, .5), (500, 1), (1000, 1)):
            for sign in (-1, 1):
                self.assertAlmostEqual(self.sample(distance_mask(CAST_DISTANCE),
                                       100 + sign * distance / scale), expected)

    def test_disabled_and_partial_strength(self):
        self.assertEqual(self.sample(distance_mask(CAST_DISTANCE), 1000, distance_softness=0), 0)
        self.assertEqual(self.sample(distance_mask(CAST_DISTANCE), 1000, distance_softness=.5), .5)

    def test_under_offset_moves_near_line(self):
        self.assertEqual(self.sample(distance_mask(UNDER_DISTANCE), 92), 0)
        self.assertEqual(self.sample(distance_mask(UNDER_DISTANCE), 592), 1)

    def test_zero_projection_and_zero_distance_are_guarded(self):
        self.assertTrue(math.isfinite(self.sample(distance_mask(CAST_DISTANCE), 101,
                                                 length=0, falloff_distance=0)))

    def test_widening_interpolates_levels_from_contact_to_tip(self):
        for fraction in (0, .1, .25, .4, .5, .75, 1, 2):
            # Interpolate sample expansion values using the exact masks wired
            # into the Nuke graph. The combined extra width must grow linearly.
            result = 0
            for stage in range(1, 5):
                weight = self.sample(widening_mask(UNDER_DISTANCE, stage), 92 + fraction * 500)
                result = result * (1 - weight) + (stage / 4) * weight
            self.assertAlmostEqual(result, min(fraction, 1))

    def test_widening_preserves_ground_for_both_cast_directions(self):
        for length in (-.5, .5):
            for stage in range(1, 5):
                self.assertEqual(self.sample(widening_mask(CAST_DISTANCE, stage), 100, length=length), 0)

    def test_invalid_widening_stage(self):
        with self.assertRaises(ValueError):
            widening_mask(CAST_DISTANCE, 0)
