"""Regression coverage for shared contracts and legacy adapters."""

import csv
import hashlib
import io
from importlib.metadata import version
from pathlib import Path

import pytest
from qaos_common import CancellationToken
from qaos_common.csvio import CSVReader, DictionaryCSVProfile, DictionaryCSVWriter
from qaos_common.errors import QAOSCommonError
from qaos_common.schemas import DICTIONARY_COLUMNS, validate_dictionary_row

from app.qa import _image_metrics, _parse_csv
from qaos_dictionary import ConversionError, convert_dictionary_docx, rows_to_csv
from tests.test_dict_docx_to_csv import make_docx


def test_pinned_wheel():
    wheel = Path(__file__).resolve().parents[1] / "vendor/qaos_common-0.2.2-py3-none-any.whl"
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == (
        "f0218d9a9e670fdf997dd69c16c8eccb8bc55414a196c449f64c35d3959a0588"
    )
    assert version("qaos-common") == "0.2.2"


@pytest.mark.parametrize("images", [False, True])
def test_common_round_trip_is_byte_identical(images):
    result = convert_dictionary_docx(make_docx(images))
    output = io.BytesIO()
    profile = DictionaryCSVProfile(line_ending="\r\n")
    with CSVReader(result.content, profile=profile) as reader:
        assert tuple(reader.headers) == DICTIONARY_COLUMNS
        seen = set()
        with DictionaryCSVWriter(output, profile=profile) as writer:
            for number, row in reader:
                validate_dictionary_row(row, row_number=number, seen_ids=seen)
                writer.write_row(row)
    assert output.getvalue() == result.content


def test_legacy_and_common_progress_and_cancellation():
    legacy, shared = [], []
    convert_dictionary_docx(
        make_docx(False), progress_callback=legacy.append, common_progress_callback=shared.append
    )
    assert [e.stage for e in shared] == [
        "reading",
        "validating",
        "parsing",
        "parsing",
        "writing",
        "completed",
    ]
    assert shared[-1].current == legacy[-1].completed == 1
    token = CancellationToken()

    def cancel_at_write(event):
        if event.stage == "writing":
            token.cancel()

    with pytest.raises(ConversionError) as caught:
        convert_dictionary_docx(
            make_docx(False), cancellation=token, common_progress_callback=cancel_at_write
        )
    assert isinstance(caught.value, (ValueError, QAOSCommonError))
    assert caught.value.to_dict()["code"] == "conversion_cancelled"


def test_invalid_image_and_duplicate_id_have_safe_context():
    row = dict(unique_id="0001", word="one", definition="first", image="NA")
    with pytest.raises(ConversionError) as caught:
        rows_to_csv(DICTIONARY_COLUMNS, [row, row])
    assert caught.value.to_dict()["details"]["row_number"] == 3
    bad = {**row, "image": "data:image/png;base64,YmFk"}
    with pytest.raises(ConversionError) as caught:
        rows_to_csv(DICTIONARY_COLUMNS, [bad])
    assert caught.value.to_dict()["details"]["column"] == "image"
    assert bad["image"] not in str(caught.value.as_dict())
    assert _image_metrics([{"image": "data:image/webp;base64,YmFk"}]) == (1, 0)


def test_qa_reader_restores_global_csv_limit():
    content = rows_to_csv(
        DICTIONARY_COLUMNS, [dict(unique_id="0001", word="a", definition="x" * 150_000, image="NA")]
    )
    previous = csv.field_size_limit()
    columns, rows = _parse_csv(content)
    assert tuple(columns) == DICTIONARY_COLUMNS
    assert len(rows[0]["definition"]) == 150_000
    assert csv.field_size_limit() == previous
