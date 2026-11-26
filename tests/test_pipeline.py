import csv
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src import pipeline


class ReportingMathTests(unittest.TestCase):
    def test_signed_changes_and_complete_rolling_window(self):
        observations = pipeline.derive([1, 2, 3, 4, 5, 6, 8, 6])
        self.assertEqual([point.daily for point in observations], [1, 1, 1, 1, 1, 1, 2, -2])
        self.assertEqual([point.avg_7d for point in observations[:6]], [None] * 6)
        self.assertEqual(observations[6].avg_7d, "1.142857")
        self.assertEqual(observations[7].avg_7d, "0.714286")

    def test_gap_never_allocates_unobserved_changes(self):
        observations = pipeline.derive([0, 3, None, 10, 11, 12, 13, 14, 15, 16, 17])
        self.assertEqual([point.daily for point in observations[:5]], [0, 3, None, None, 1])
        self.assertEqual(observations[3].cumulative, 10)
        self.assertIsNone(observations[9].avg_7d)
        self.assertEqual(observations[10].avg_7d, "1.000000")

    def test_possible_batch_reporting_requires_nonzero_prior_baseline(self):
        after_start = pipeline.derive([1] * 8 + [3])
        before_start = pipeline.derive([0] * 8 + [3])
        after_gap = pipeline.derive([1] * 8 + [None, 3])
        self.assertTrue(after_start[-1].possible_batch_report)
        self.assertTrue(all(not point.possible_batch_report for point in before_start + after_gap))

    def test_monday_weeks_mark_observed_days_and_partial_weeks(self):
        dates = pipeline.calendar(date(2020, 1, 6), date(2020, 1, 14))
        dimensions = [("example", "Example", "", "", "")]
        sources = {
            "cases": {"Example": [2, 4, None, 9, 12, 11, 11, 13, 15]},
            "deaths": {"Example": [None] * len(dates)},
        }
        with TemporaryDirectory() as temporary:
            destination = Path(temporary)
            stats, count = pipeline.write_facts(destination, dates, dimensions, sources)
            with (destination / "weekly.csv").open(newline="", encoding="utf-8") as week_file:
                rows = list(csv.reader(week_file))
        self.assertEqual(count, 2)
        self.assertEqual(rows[1:], [
            ["2020-01-06", "example", "6", "", "5", "0", "7"],
            ["2020-01-13", "example", "4", "", "2", "0", "2"],
        ])
        self.assertEqual(stats["cases"]["daily_sum"], 10)
        self.assertEqual(stats["cases"]["weekly_sum"], 10)


class SourceParsingTests(unittest.TestCase):
    def test_country_sum_is_unknown_with_a_missing_province_or_date(self):
        dates = pipeline.calendar(date(2020, 1, 22), date(2020, 1, 25))
        source = (
            "Province/State,Country/Region,Lat,Long,1/22/20,1/24/20,1/25/20\n"
            "East,Example,1,1,5,8,9\n"
            "West,Example,1,1,7,,11\n"
        )
        with TemporaryDirectory() as temporary:
            csv_path = Path(temporary) / "example.csv"
            csv_path.write_text(source, encoding="utf-8")
            totals, missing = pipeline.load_time_series(csv_path, dates)
        self.assertEqual(totals, {"Example": [12, None, None, 20]})
        self.assertEqual(missing, 3)

    def test_offline_mode_rejects_modified_source_before_building(self):
        with TemporaryDirectory() as temporary:
            raw = Path(temporary)
            (raw / "confirmed_global.csv").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                pipeline.ensure_source(raw, "confirmed_global.csv", offline=True)


if __name__ == "__main__":
    unittest.main()
