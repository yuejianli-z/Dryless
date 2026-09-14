"""Geometry regression checks; no QApplication or user profile required."""

import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'widgets'))

from PyQt6.QtCore import QPointF, QRectF, QSizeF

from chart_label_layout import (
    BUBBLE_CLEARANCE,
    _circle_hits_rect,
    _segment_hits_rect,
    place_mean_label,
)


class MeanLabelPlacementTest(unittest.TestCase):
    def setUp(self):
        self.plot = QRectF(50, 50, 600, 300)
        self.size = QSizeF(100, 20)
        self.fallback = QRectF(530, 15, 120, 20)

    def place(self, mean=200, bubbles=(), segments=(), plot=None):
        return place_mean_label(plot or self.plot, mean, self.size,
                                list(bubbles), list(segments), self.fallback)

    def test_empty_data_prefers_upper_right(self):
        rect, fallback = self.place()
        self.assertFalse(fallback)
        self.assertEqual(rect, QRectF(546, 174, 100, 20))

    def test_endpoint_bubble_and_hover_ring_are_clear(self):
        center, radius = QPointF(620, 189), 10
        rect, fallback = self.place(bubbles=[(center, radius)])
        self.assertFalse(fallback)
        self.assertEqual(rect.top(), 206)
        self.assertFalse(_circle_hits_rect(rect, center, radius + BUBBLE_CLEARANCE))

    def test_top_boundary_uses_below(self):
        rect, fallback = self.place(mean=self.plot.top())
        self.assertFalse(fallback)
        self.assertEqual(rect.top(), self.plot.top() + 6)

    def test_bottom_boundary_uses_above(self):
        rect, fallback = self.place(mean=self.plot.bottom())
        self.assertFalse(fallback)
        self.assertEqual(rect.bottom(), self.plot.bottom() - 6)

    def test_dense_data_uses_exact_fallback(self):
        rect, fallback = self.place(bubbles=[(self.plot.center(), 1000)])
        self.assertTrue(fallback)
        self.assertEqual(rect, self.fallback)

    def test_line_crossing_without_bubbles_is_avoided(self):
        segment = (QPointF(520, 180), QPointF(650, 190))
        rect, fallback = self.place(segments=[segment])
        self.assertFalse(fallback)
        self.assertEqual(rect.top(), 206)
        self.assertFalse(_segment_hits_rect(rect.adjusted(-3, -3, 3, 3), *segment))

    def test_scan_finds_middle_when_endpoints_are_blocked(self):
        rect, fallback = self.place(bubbles=[(QPointF(595, 200), 80),
                                             (QPointF(105, 200), 80)])
        self.assertFalse(fallback)
        self.assertGreater(rect.left(), 190)
        self.assertLess(rect.right(), 510)

    def test_no_vertical_room_uses_fallback(self):
        rect, fallback = self.place(mean=65, plot=QRectF(50, 50, 600, 30))
        self.assertTrue(fallback)
        self.assertEqual(rect, self.fallback)

    def test_no_horizontal_room_uses_fallback(self):
        rect, fallback = self.place(plot=QRectF(50, 50, 100, 300))
        self.assertTrue(fallback)
        self.assertEqual(rect, self.fallback)

    def test_segment_clipping_corner_and_degenerate_cases(self):
        rect = QRectF(10, 10, 20, 20)
        self.assertTrue(_segment_hits_rect(rect, QPointF(0, 0), QPointF(40, 40)))
        self.assertFalse(_segment_hits_rect(rect, QPointF(0, 9), QPointF(40, 9)))
        self.assertTrue(_segment_hits_rect(rect, QPointF(20, 20), QPointF(20, 20)))
        self.assertFalse(_segment_hits_rect(rect, QPointF(5, 5), QPointF(5, 5)))


if __name__ == '__main__':
    unittest.main()
