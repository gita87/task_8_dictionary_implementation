from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from dict_docx_to_csv import convert_dictionary_docx_to_csv


GOLDEN_DIRECTORY = Path(__file__).parent / "fixtures" / "golden"
MANIFEST_PATH = GOLDEN_DIRECTORY / "manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ProductionGoldenFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.input_path = GOLDEN_DIRECTORY / cls.manifest["input_file"]
        cls.expected_path = (
            GOLDEN_DIRECTORY / cls.manifest["expected_output_file"]
        )

    def test_fixture_matches_approved_manifest(self):
        self.assertEqual(self.manifest["approval_status"], "approved")
        self.assertEqual(
            self.input_path.stat().st_size,
            self.manifest["input_size_bytes"],
        )
        self.assertEqual(
            self.expected_path.stat().st_size,
            self.manifest["expected_output_size_bytes"],
        )
        self.assertEqual(sha256(self.input_path), self.manifest["input_sha256"])
        self.assertEqual(
            sha256(self.expected_path),
            self.manifest["expected_output_sha256"],
        )

    def test_production_docx_matches_approved_csv_byte_for_byte(self):
        with self.input_path.open("rb") as source:
            result = convert_dictionary_docx_to_csv(
                source,
                input_filename=self.input_path.name,
            )

        expected_content = self.expected_path.read_bytes()

        self.assertEqual(result.content, expected_content)
        self.assertEqual(result.row_count, self.manifest["expected_row_count"])
        self.assertEqual(
            list(result.columns),
            self.manifest["expected_columns"],
        )


if __name__ == "__main__":
    unittest.main()
