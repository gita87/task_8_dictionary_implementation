"""Adversarial boundary tests; no network or external files are required."""

import io
import threading
import zipfile
from unittest.mock import patch

import pytest

from qaos_dictionary import ConversionError, convert_dictionary_docx
from qaos_dictionary.cli import write_atomic
from qaos_dictionary.source import _validated_docx_buffer
from tests.test_dict_docx_to_csv import make_docx


def package_with(name, content):
    original = make_docx(False).getvalue()
    target = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(target, "w") as output:
        for item in source.infolist():
            output.writestr(item, content if item.filename == name else source.read(item))
    return target.getvalue()


@pytest.mark.parametrize(
    "xml",
    [
        b'<!DOCTYPE x [<!ENTITY a "expanded">]><x>&a;</x>',
        b'<!DOCTYPE x [<!ENTITY a SYSTEM "file:///etc/passwd">]><x>&a;</x>',
        b"<unclosed>",
    ],
)
def test_rejects_dtd_entities_and_malformed_xml(xml):
    with pytest.raises(ConversionError) as caught:
        convert_dictionary_docx(package_with("word/document.xml", xml))
    assert caught.value.diagnostic.code == "invalid_docx_xml"
    assert "expanded" not in str(caught.value)


@pytest.mark.parametrize("name", ["../escape.xml", "/absolute.xml", "word\\escape.xml"])
def test_rejects_unsafe_zip_names(name):
    content = io.BytesIO(make_docx(False).getvalue())
    with zipfile.ZipFile(content, "a") as archive:
        archive.writestr(name, b"<x/>")
    with pytest.raises(ConversionError, match="unsafe internal parts"):
        _validated_docx_buffer(content.getvalue())


def test_rejects_duplicate_zip_parts():
    content = io.BytesIO(make_docx(False).getvalue())
    with zipfile.ZipFile(content, "a") as archive, pytest.warns(UserWarning):
        archive.writestr("word/document.xml", b"<x/>")
    with pytest.raises(ConversionError, match="duplicate"):
        _validated_docx_buffer(content.getvalue())


@pytest.mark.parametrize("limit_name", ["MAX_DOCX_MEMBERS", "MAX_UNCOMPRESSED_DOCX_BYTES"])
def test_zip_budgets_fail_before_document_load(limit_name):
    with patch(f"qaos_dictionary.source.{limit_name}", 1):
        with pytest.raises(ConversionError) as caught:
            convert_dictionary_docx(make_docx(False))
    assert caught.value.diagnostic.code in ("docx_too_many_parts", "docx_uncompressed_too_large")


def test_atomic_write_failure_keeps_destination_and_removes_temporary(tmp_path):
    output = tmp_path / "keep.csv"
    output.write_bytes(b"original")
    with patch("qaos_dictionary.cli.os.fsync", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            write_atomic(output, b"replacement")
    assert output.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [output]


def test_text_stream_error_is_structured():
    with pytest.raises(ConversionError) as caught:
        convert_dictionary_docx(io.StringIO("not binary"))
    assert caught.value.diagnostic.code == "input_read_failed"


def test_legacy_event_and_callable_cancellation():
    event = threading.Event()
    event.set()
    for cancellation in (event, lambda: True):
        with pytest.raises(ConversionError) as caught:
            convert_dictionary_docx(b"ignored", cancellation=cancellation)
        assert caught.value.diagnostic.code == "conversion_cancelled"


def test_payload_redaction_in_both_error_envelopes():
    error = ConversionError(
        "data:image/png;base64," + "A" * 100, context={"image": b"secret", "payload": "A" * 100}
    )
    for envelope in (error.as_dict(), error.to_dict()):
        assert "A" * 100 not in str(envelope)
        assert "b'secret'" not in str(envelope)


def test_compatibility_modules_reexport_public_api():
    import dict_docx_to_csv
    import qaos_dictionary
    import qaos_dictionary.core

    for name in qaos_dictionary.__all__:
        assert getattr(qaos_dictionary.core, name) is getattr(qaos_dictionary, name)
        assert getattr(dict_docx_to_csv, name) is getattr(qaos_dictionary, name)
