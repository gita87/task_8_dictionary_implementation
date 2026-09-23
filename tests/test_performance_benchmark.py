from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.performance.benchmark_pipeline import run_once
from tests.test_dict_docx_to_csv import make_docx


class PerformanceBenchmarkTests(unittest.TestCase):
    def test_collects_duration_memory_and_result_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "dictionary.docx"
            input_path.write_bytes(make_docx(True).getvalue())

            metrics = run_once(input_path)

            self.assertGreater(metrics["duration_seconds"], 0)
            self.assertGreater(metrics["peak_rss_bytes"], 0)
            self.assertEqual(metrics["row_count"], 2)
            self.assertEqual(metrics["image_count"], 1)
            self.assertEqual(len(metrics["output_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()


class PerformanceBudgetTests(unittest.TestCase):
    def setUp(self):
        import json

        from tests.performance.benchmark_pipeline import DEFAULT_THRESHOLDS

        self.budget = json.loads(DEFAULT_THRESHOLDS.read_text())
        self.report = {
            "duration_seconds": {"median": self.budget["maximum_median_duration_seconds"]},
            "peak_rss_bytes": {"maximum": self.budget["maximum_peak_rss_mb"] * 1024 * 1024},
            "result": {
                name: self.budget[f"expected_{name}"]
                for name in ("row_count", "image_count", "output_sha256")
            },
        }

    def test_exact_budget_passes(self):
        from tests.performance.benchmark_pipeline import threshold_failures

        self.assertEqual(threshold_failures(self.report, self.budget), [])

    def test_duration_and_memory_regressions_are_rejected(self):
        from tests.performance.benchmark_pipeline import threshold_failures

        self.report["duration_seconds"]["median"] += 0.001
        self.report["peak_rss_bytes"]["maximum"] += 1
        failures = threshold_failures(self.report, self.budget)
        self.assertEqual(len(failures), 2)
        self.assertIn("Median duration", failures[0])
        self.assertIn("Peak RSS", failures[1])

    def test_changed_output_is_rejected(self):
        from tests.performance.benchmark_pipeline import threshold_failures

        self.report["result"] = dict(row_count=0, image_count=0, output_sha256="wrong")
        self.assertEqual(len(threshold_failures(self.report, self.budget)), 3)

    def test_budget_violation_exits_nonzero_and_writes_failed_report(self):
        import json
        from unittest.mock import patch

        from tests.performance.benchmark_pipeline import DEFAULT_INPUT, main

        self.report["duration_seconds"]["median"] += 1
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            with patch("tests.performance.benchmark_pipeline.summarize", return_value=self.report):
                status = main([str(DEFAULT_INPUT), "--report", str(report_path)])
            self.assertEqual(status, 1)
            self.assertEqual(json.loads(report_path.read_text())["status"], "FAILED")
