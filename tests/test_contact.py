import unittest

from nuke_tools.contact import find_contact


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
