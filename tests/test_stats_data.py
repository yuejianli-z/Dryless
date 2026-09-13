"""Data-semantic checks; no Qt, camera, application config, or profile writes."""

import unittest
from datetime import date, datetime, timedelta

from stats_data import aggregate_periods, choose_grain, normalize_history


def records(count, blinks=10, clock="09:30"):
    return [{"minute": index, "time": clock, "blinks": blinks} for index in range(count)]


class HistoryAggregationTests(unittest.TestCase):
    def test_weighted_totals_conserved_across_calendar_grains(self):
        start, end = date(2023, 12, 31), date(2024, 3, 12)
        source = {"2023-12-30": records(13, 900), "2024-03-13": records(7, 800)}
        for offset in range((end - start).days + 1):
            if offset % 5:
                source[(start + timedelta(days=offset)).isoformat()] = records(offset % 19 + 1, offset % 31)
        days, skipped = normalize_history({"days": source})
        expected = [item for day, items in days.items() if start <= day <= end for item in items]
        total = sum(item["blinks"] for item in expected)
        self.assertEqual(skipped, 0)
        for grain in ("day", "week", "month"):
            with self.subTest(grain=grain):
                points, unplaced = aggregate_periods(days, start, end, grain)
                self.assertEqual(unplaced, 0)
                self.assertEqual(sum(p["minutes"] for p in points), len(expected))
                self.assertEqual(sum(p["total"] or 0 for p in points), total)
                self.assertEqual(sum(p["calendar_days"] for p in points), (end - start).days + 1)
                self.assertAlmostEqual(sum((p["average"] or 0) * p["minutes"] for p in points), total)
                self.assertEqual(points[0]["start"], datetime(2023, 12, 31))
                self.assertEqual(points[-1]["end"], datetime(2024, 3, 13))
                self.assertTrue(all(a["end"] == b["start"] for a, b in zip(points, points[1:])))

    def test_period_mean_weights_minutes_instead_of_days(self):
        days, _ = normalize_history({"days": {"2024-02-01": records(100, 1), "2024-02-02": records(1, 100)}})
        points, _ = aggregate_periods(days, date(2024, 2, 1), date(2024, 2, 29), "month")
        self.assertAlmostEqual(points[0]["average"], 200 / 101)
        self.assertEqual(points[0]["recorded_days"], 2)

    def test_zeroes_missing_days_and_repeated_session_indices(self):
        days, _ = normalize_history({"days": {"2024-02-01": records(1, 0) + records(1, 0)}})
        points, _ = aggregate_periods(days, date(2024, 2, 1), date(2024, 2, 3), "day")
        self.assertEqual((points[0]["minutes"], points[0]["total"], points[0]["average"]), (2, 0, 0.0))
        self.assertEqual([item["record_index"] for item in days[date(2024, 2, 1)]], [1, 2])
        for point in points[1:]:
            self.assertEqual(point["minutes"], 0)
            self.assertIsNone(point["total"])
            self.assertIsNone(point["average"])

    def test_leap_year_and_partial_months(self):
        points, _ = aggregate_periods({}, date(2024, 1, 1), date(2024, 12, 31), "month")
        self.assertEqual(len(points), 12)
        self.assertEqual(sum(p["calendar_days"] for p in points), 366)
        self.assertEqual(points[1]["calendar_days"], 29)
        self.assertFalse(any(p["partial"] for p in points))
        clipped, _ = aggregate_periods({}, date(2024, 1, 17), date(2024, 3, 12), "month")
        self.assertEqual([p["partial"] for p in clipped], [True, False, True])
        self.assertEqual([p["calendar_days"] for p in clipped], [15, 29, 12])
        self.assertEqual(clipped[0]["period_start"], datetime(2024, 1, 1))

    def test_weeks_align_monday_across_year_boundary(self):
        points, _ = aggregate_periods({}, date(2023, 12, 31), date(2024, 1, 10), "week")
        self.assertEqual([p["period_start"] for p in points],
                         [datetime(2023, 12, 25), datetime(2024, 1, 1), datetime(2024, 1, 8)])
        self.assertEqual([p["calendar_days"] for p in points], [1, 7, 3])
        self.assertEqual([p["partial"] for p in points], [True, False, True])

    def test_legacy_and_corrupt_entries(self):
        invalid = [True, False, float("nan"), float("inf"), -1, 1.5, "12", None]
        entries = [{"blinks": value} for value in invalid] + [[], None, {"blinks": 0}, {"blinks": 12.0}]
        days, skipped = normalize_history({"date": "2024-02-29", "history": entries})
        self.assertEqual(skipped, 10)
        self.assertEqual([r["blinks"] for r in days[date(2024, 2, 29)]], [0, 12])
        self.assertEqual([r["record_index"] for r in days[date(2024, 2, 29)]], [11, 12])
        days, skipped = normalize_history({"days": {
            "2024-02-30": records(2), "20240229": records(1), "2024-02-29": "invalid",
            "2024-03-01": [], "nonsense": []}})
        self.assertEqual(skipped, 5)
        self.assertEqual(days, {date(2024, 3, 1): []})
        for raw in ([], {}, {"days": []}, {"date": [], "history": []}):
            with self.assertRaises(ValueError):
                normalize_history(raw)

    def test_hour_excludes_only_unplaceable_selected_day_records(self):
        invalid_clocks = ["", "9:30", "24:00", "09:60", "09:30:00", None]
        source = {"2024-06-01": [
            {"blinks": 0, "time": "00:00"}, {"blinks": 12, "time": "09:59"},
            {"blinks": 24, "time": "09:00"}, {"blinks": 10, "time": "23:59"},
            *[{"blinks": 7, "time": clock} for clock in invalid_clocks]],
            "2024-06-02": [{"blinks": 1000}]}
        days, skipped = normalize_history({"days": source})
        self.assertEqual(skipped, 0)
        selected = date(2024, 6, 1)
        points, unplaced = aggregate_periods(days, selected, selected, "hour")
        self.assertEqual(len(points), 24)
        self.assertEqual(unplaced, 6)
        self.assertEqual(sum(p["minutes"] for p in points), 4)
        self.assertEqual(points[9]["average"], 18)
        self.assertEqual(points[0]["total"], 0)
        self.assertIsNone(points[1]["total"])
        self.assertEqual(points[-1]["end"], datetime(2024, 6, 2))
        day_points, unplaced = aggregate_periods(days, selected, selected, "day")
        self.assertEqual(day_points[0]["minutes"], 10)
        self.assertEqual(day_points[0]["total"], 88)
        self.assertEqual(unplaced, 0)

    def test_readable_default_grains_and_invalid_ranges(self):
        start = date(2024, 1, 1)
        for length, grain in ((1, "hour"), (2, "day"), (45, "day"), (46, "week"),
                              (210, "week"), (211, "month"), (3650, "month")):
            self.assertEqual(choose_grain(start, start + timedelta(days=length - 1)), grain)
        with self.assertRaises(ValueError):
            aggregate_periods({}, start, start + timedelta(days=1), "hour")
        with self.assertRaises(ValueError):
            aggregate_periods({}, start, start, "year")
        with self.assertRaises(ValueError):
            choose_grain(start + timedelta(days=1), start)


if __name__ == "__main__":
    unittest.main()
