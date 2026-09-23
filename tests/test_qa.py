from __future__ import annotations

import base64
import io
import random
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app import create_app
from qaos_dictionary import (
    ConversionResult,
    convert_dictionary_docx_to_csv,
    rows_to_csv,
)
from app.qa import FAIL, PASS, build_qa_session
from tests.test_dict_docx_to_csv import make_docx


class QualityAssuranceTests(unittest.TestCase):
    def build_session(self, directory: str):
        root = Path(directory)
        input_path = root / "dictionary.docx"
        output_path = root / "dictionary.csv"
        input_path.write_bytes(make_docx(True).getvalue())
        with input_path.open("rb") as source:
            conversion = convert_dictionary_docx_to_csv(source, input_path.name)
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
            # Real WebP bytes: shared validation checks MIME signatures too.
            image_buffer = io.BytesIO()
            Image.frombytes("RGB", (256, 256), random.Random(0).randbytes(256 * 256 * 3)).save(
                image_buffer, format="WEBP", lossless=True)
            image = "data:image/webp;base64," + base64.b64encode(
                image_buffer.getvalue()
            ).decode("ascii")
            self.assertGreater(len(image), 131_072)
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

    def test_rejects_non_webp_image_data_uri(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "dictionary.docx"
            output_path = root / "dictionary.csv"
            input_path.write_bytes(b"QA fixture")
            columns = ("word", "definition", "image")
            content = rows_to_csv(
                columns,
                [
                    {
                        "word": "test",
                        "definition": "invalid image format",
                        "image": "data:image/png;base64,aW52YWxpZA==",
                    }
                ],
            )
            conversion = ConversionResult(
                content=content,
                filename=output_path.name,
                row_count=1,
                columns=columns,
            )

            session = build_qa_session(input_path, output_path, conversion, 0.1)
            image_check = next(
                check
                for check in session.report.checks
                if check.name == "Adaptive image output"
            )

            self.assertEqual(image_check.status, FAIL)
            self.assertEqual(session.report.status, "FAILED")

    def test_rejects_empty_required_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "dictionary.docx"
            output_path = root / "dictionary.csv"
            input_path.write_bytes(b"QA fixture")
            columns = ("word", "definition")
            content = rows_to_csv(
                columns,
                [{"word": "incomplete", "definition": ""}],
            )
            conversion = ConversionResult(
                content=content,
                filename=output_path.name,
                row_count=1,
                columns=columns,
            )

            session = build_qa_session(input_path, output_path, conversion, 0.1)
            completeness_check = next(
                check
                for check in session.report.checks
                if check.name == "Required cell completeness"
            )

            self.assertEqual(completeness_check.status, FAIL)
            self.assertEqual(session.report.status, "FAILED")


if __name__ == "__main__":
    unittest.main()
