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
