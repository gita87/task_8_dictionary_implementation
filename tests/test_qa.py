from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.converter import ConversionResult, convert_docx, rows_to_csv
from app.qa import PASS, build_qa_session
from tests.test_converter import make_docx


class QualityAssuranceTests(unittest.TestCase):
    def build_session(self, directory: str):
        root = Path(directory)
        input_path = root / "dictionary.docx"
        output_path = root / "dictionary.csv"
        input_path.write_bytes(make_docx(True).getvalue())
        with input_path.open("rb") as source:
            conversion = convert_docx(source, input_path.name)
        output_path.write_bytes(conversion.content)
        return build_qa_session(input_path, output_path, conversion, 0.25)

    def test_builds_passing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            session = self.build_session(directory)

            self.assertEqual(session.report.status, "PASSED")
            self.assertEqual(session.report.row_count, 2)
            self.assertEqual(session.report.image_count, 1)
            self.assertTrue(all(check.status == PASS for check in session.report.checks))

    def test_report_and_csv_pages_share_the_same_session(self):
        with tempfile.TemporaryDirectory() as directory:
            session = self.build_session(directory)
            client = create_app({"TESTING": True, "QA_SESSION": session}).test_client()

            report = client.get("/qa")
            self.assertEqual(report.status_code, 200)
            self.assertIn(b"Quality Assurance Report", report.data)
            self.assertIn(b"View CSV results", report.data)
            self.assertIn(b"PASSED", report.data)

            results = client.get("/qa/csv")
            self.assertEqual(results.status_code, 200)
            self.assertIn(b"Converted CSV", results.data)
            self.assertIn(b"abate", results.data)
            self.assertIn(b"data:image/webp;base64", results.data)

            download = client.get("/qa/download")
            self.assertEqual(download.status_code, 200)
            self.assertEqual(download.data, session.conversion.content)
            download.close()

    def test_qa_pages_are_hidden_without_a_cli_session(self):
        client = create_app({"TESTING": True}).test_client()
        self.assertEqual(client.get("/qa").status_code, 404)
        self.assertEqual(client.get("/qa/csv").status_code, 404)

    def test_detects_image_larger_than_default_csv_field_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "large-image.docx"
            output_path = root / "large-image.csv"
            input_path.write_bytes(b"QA fixture")
            image = "data:image/webp;base64," + base64.b64encode(
                b"large-image-payload" * 10_000
            ).decode("ascii")
            columns = ("word", "definition", "image")
            content = rows_to_csv(
                columns,
                [{"word": "test", "definition": "large image", "image": image}],
            )
            conversion = ConversionResult(
                content=content,
                filename=output_path.name,
                row_count=1,
                columns=columns,
            )

            session = build_qa_session(input_path, output_path, conversion, 0.1)

            self.assertEqual(session.report.image_count, 1)
            image_check = next(
                check
                for check in session.report.checks
                if check.name == "Adaptive image output"
            )
            self.assertEqual(image_check.status, PASS)


if __name__ == "__main__":
    unittest.main()
