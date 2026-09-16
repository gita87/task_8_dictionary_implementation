from __future__ import annotations

import io
import unittest

from app import create_app
from tests.test_dict_docx_to_csv import make_docx


class WebTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app({"TESTING": True}).test_client()

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})

    def test_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"DOCX to CSV", response.data)
        self.assertIn(b"Choose DOCX and convert", response.data)
        self.assertNotIn(b"From Word tables", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")

    def test_static_assets_are_not_cached(self):
        response = self.client.get("/static/app.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Choose DOCX and convert", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")
        response.close()

    def test_converts_upload(self):
        response = self.client.post(
            "/convert",
            data={"document": (make_docx(False), "kamus.docx")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Row-Count"], "2")
        self.assertEqual(
            response.headers["X-CSV-Columns"], "unique_id,word,definition"
        )
        self.assertIn("kamus.csv", response.headers["Content-Disposition"])

    def test_rejects_wrong_extension(self):
        response = self.client.post(
            "/convert",
            data={"document": (io.BytesIO(b"x"), "data.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(".docx", response.json["error"])


if __name__ == "__main__":
    unittest.main()
