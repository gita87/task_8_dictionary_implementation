from __future__ import annotations

import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cli import main
from tests.test_dict_docx_to_csv import make_docx


class CliTests(unittest.TestCase):
    def test_converts_with_explicit_output_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "terms.docx"
            output_path = root / "exports" / "terms.csv"
            input_path.write_bytes(make_docx(False).getvalue())
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                status = main([str(input_path), str(output_path)])

            self.assertEqual(status, 0)
            self.assertTrue(output_path.is_file())
            self.assertIn("2 rows", stdout.getvalue())
            text = output_path.read_text(encoding="utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(text), delimiter="\t"))
            self.assertEqual(rows[0]["word"], "abate")

    def test_uses_default_output_path(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "terms.docx"
            input_path.write_bytes(make_docx(True).getvalue())

            with contextlib.redirect_stdout(io.StringIO()):
                status = main([str(input_path)])

            self.assertEqual(status, 0)
            self.assertTrue(input_path.with_suffix(".csv").is_file())

    def test_reports_invalid_docx(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "invalid.docx"
            output_path = Path(directory) / "invalid.csv"
            input_path.write_bytes(b"not a docx")
            stderr = io.StringIO()

            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(stderr),
            ):
                status = main([str(input_path), str(output_path)])

            self.assertEqual(status, 1)
            self.assertIn("Conversion failed", stderr.getvalue())
            self.assertFalse(output_path.exists())

    def test_qa_mode_builds_and_serves_report(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "terms.docx"
            output_path = Path(directory) / "terms.csv"
            input_path.write_bytes(make_docx(True).getvalue())

            stdout = io.StringIO()
            with (
                patch("app.qa_server.serve_qa_report") as serve,
                contextlib.redirect_stdout(stdout),
            ):
                status = main(
                    [
                        str(input_path),
                        str(output_path),
                        "--qa",
                        "--no-browser",
                    ]
                )

            self.assertEqual(status, 0)
            serve.assert_called_once()
            session = serve.call_args.args[0]
            self.assertEqual(session.report.status, "PASSED")
            self.assertIn("[1/3] Converting", stdout.getvalue())
            self.assertIn("[2/3] Running QA checks", stdout.getvalue())
            self.assertIn("[3/3] Starting QA report server", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
