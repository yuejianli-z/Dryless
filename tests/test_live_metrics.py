import unittest
from live_metrics import BlinkWindows, frequency


class LiveMetricsTests(unittest.TestCase):
    def test_startup_missing_and_real_zero_are_distinct(self):
        w = BlinkWindows(0)
        for second in range(30):
            self.assertIsNone(w.sample(second, True, False)['rate'])
        self.assertEqual(w.sample(30, True, False)['rate'], 0)
        for second in range(31, 92):
            result = w.sample(second, False, False)
        self.assertIsNone(result['rate'])
        self.assertEqual(result['valid_seconds'], 0)

    def test_sliding_expiry_and_no_thirty_cap(self):
        w = BlinkWindows(0)
        for second in range(61):
            result = w.sample(second, True, 0 < second <= 45)
        self.assertEqual(result['rate'], 45)
        self.assertEqual(result['completed'][0].blinks, 45)
        self.assertEqual(result['completed'][0].valid_seconds, 60)
        for second in range(61, 76):
            result = w.sample(second, True, False)
        self.assertEqual(result['rate'], 30)
        for second in range(76, 121):
            result = w.sample(second, True, False)
        self.assertEqual(result['rate'], 0)

    def test_effective_exposure_matches_completed_minute(self):
        w = BlinkWindows(0)
        for second in range(61):
            result = w.sample(second, second <= 30, 0 < second <= 10)
        minute = result['completed'][0]
        self.assertEqual(minute.valid_seconds, 30)
        self.assertEqual(result['rate'], 20)
        self.assertEqual(result['rate'], frequency(minute.blinks, minute.valid_seconds))

    def test_gap_is_not_counted_and_invalid_events_are_ignored(self):
        w = BlinkWindows(0)
        w.sample(0, True, False)
        result = w.sample(59, True, False)
        self.assertEqual(result['valid_seconds'], 0)
        result = w.sample(60, False, True)
        self.assertEqual(result['blinks'], 0)
        self.assertEqual(result['completed'][0].valid_seconds, 0)

    def test_boundary_blink_goes_to_new_minute_without_losing_first(self):
        w = BlinkWindows(0)
        for second in range(61):
            result = w.sample(second, True, second in (0, 60))
        self.assertEqual(result['completed'][0].blinks, 1)
        for second in range(61, 121):
            result = w.sample(second, True, False)
        self.assertEqual(result['completed'][0].blinks, 1)

    def test_fractional_spans_are_clipped_at_window_boundary(self):
        w = BlinkWindows(0)
        for i in range(241):
            result = w.sample(i*.25, True, i % 12 == 1)
        result = w.sample(60.6, True, False)
        self.assertAlmostEqual(result['valid_seconds'], 60)
        self.assertEqual(result['blinks'], 19)

    def test_empty_minutes_preserve_gaps_and_dont_pollute_next_minute(self):
        w = BlinkWindows(100.123)
        w.sample(100.123, True, False)
        result = w.sample(281.123, True, True)
        self.assertEqual([m.index for m in result['completed']], [0, 1, 2])
        self.assertTrue(all(m.valid_seconds == 0 and m.blinks == 0 for m in result['completed']))
        self.assertEqual(result['blinks'], 1)

    def test_monotonic_order_required(self):
        w = BlinkWindows(0)
        w.sample(5, True, False)
        with self.assertRaises(ValueError):
            w.sample(4, True, False)
        with self.assertRaises(ValueError):
            w.sample(float('nan'), True, False)


if __name__ == '__main__':
    unittest.main()
