from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from qaos_dictionary import (
    DICTIONARY_SCHEMA_VERSION,
    CancellationToken,
    ConversionError,
    convert_dictionary_docx,
    rows_to_csv,
)
from tests.test_dict_docx_to_csv import make_docx


class LibraryApiTests(unittest.TestCase):
    def test_accepts_bytes_stream_and_path(self):
        payload = make_docx(False).getvalue()
        bytes_result = convert_dictionary_docx(payload, "bytes.docx")
        stream_result = convert_dictionary_docx(make_docx(False), "stream.docx")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "path.docx"
            path.write_bytes(payload)
            path_result = convert_dictionary_docx(path)

        self.assertEqual(bytes_result.content, stream_result.content)
        self.assertEqual(bytes_result.content, path_result.content)
        self.assertEqual(path_result.filename, "path.csv")
        self.assertEqual(path_result.schema_version, DICTIONARY_SCHEMA_VERSION)

    def test_reports_progress_and_checkpoints(self):
        progress = []
        checkpoints = []
        result = convert_dictionary_docx(
            make_docx(False),
            progress_callback=progress.append,
            checkpoint_callback=checkpoints.append,
            checkpoint_interval=1,
        )

        self.assertEqual(result.row_count, 2)
        self.assertEqual(progress[-1].stage, "complete")
        self.assertEqual([item.rows_processed for item in checkpoints], [1, 2])

    def test_cancellation_has_structured_diagnostic(self):
        token = CancellationToken()
        token.cancel()
        with self.assertRaises(ConversionError) as raised:
            convert_dictionary_docx(make_docx(False), cancellation=token)

        self.assertEqual(raised.exception.diagnostic.code, "conversion_cancelled")
        self.assertEqual(raised.exception.as_dict()["severity"], "error")

    def test_enforces_upload_limit(self):
        with patch("qaos_dictionary.source.MAX_UPLOAD_BYTES", 2):
            with self.assertRaises(ConversionError) as upload_error:
                convert_dictionary_docx(b"123")
        self.assertEqual(upload_error.exception.diagnostic.code, "input_too_large")

    def test_enforces_cell_and_output_limits(self):
        with patch("qaos_dictionary.images.MAX_CELL_BYTES", 3):
            with self.assertRaises(ConversionError) as cell_error:
                convert_dictionary_docx(make_docx(False))
        self.assertEqual(cell_error.exception.diagnostic.code, "cell_too_large")

        with patch("qaos_dictionary.serialization.MAX_OUTPUT_BYTES", 10):
            with self.assertRaises(ConversionError) as output_error:
                rows_to_csv(("word",), [{"word": "value"}])
        self.assertEqual(output_error.exception.diagnostic.code, "output_too_large")

    def test_rejects_unapproved_image_mime(self):
        with patch(
            "qaos_dictionary.images._first_image_blob",
            return_value=(b"image", "application/octet-stream"),
        ):
            from qaos_dictionary import image_to_data_uri

            with self.assertRaises(ConversionError) as raised:
                image_to_data_uri(object())
        self.assertEqual(raised.exception.diagnostic.code, "unsupported_image_mime")

    def test_rejects_image_mime_content_mismatch(self):
        image = io.BytesIO()
        Image.new("RGB", (2, 2)).save(image, "PNG")
        with patch(
            "qaos_dictionary.images._first_image_blob",
            return_value=(image.getvalue(), "image/jpeg"),
        ):
            from qaos_dictionary import image_to_data_uri

            with self.assertRaises(ConversionError) as raised:
                image_to_data_uri(object())
        self.assertEqual(raised.exception.diagnostic.code, "image_mime_mismatch")


if __name__ == "__main__":
    unittest.main()
