"""Source boundary for dictionary conversion."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path, PurePosixPath

# Exception class only; parsing uses defusedxml below.
from xml.etree.ElementTree import ParseError  # nosec B405

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import iterparse

from .contracts import MAX_DOCX_MEMBERS, MAX_UNCOMPRESSED_DOCX_BYTES, MAX_UPLOAD_BYTES
from .models import InputSource
from .operations import _error


def _read_source(source: InputSource, input_filename: str | None) -> tuple[bytes, str]:
    if isinstance(source, (str, Path)):
        path = Path(source)
        filename = input_filename or path.name
        try:
            with path.open("rb") as stream:
                payload = stream.read(MAX_UPLOAD_BYTES + 1)
        except OSError as error:
            raise _error(
                "input_read_failed", "The DOCX file could not be read.", path=str(path)
            ) from error
    elif isinstance(source, (bytes, bytearray, memoryview)):
        payload, filename = bytes(source), input_filename or "dictionary.docx"
    else:
        filename = input_filename or Path(getattr(source, "name", "dictionary.docx")).name
        try:
            payload = source.read(MAX_UPLOAD_BYTES + 1)
        except (AttributeError, OSError, ValueError) as error:
            raise _error("input_read_failed", "The DOCX stream could not be read.") from error
    if not isinstance(payload, bytes):
        raise _error("input_read_failed", "The DOCX stream must return bytes.")
    if not payload:
        raise _error("input_empty", "The DOCX file is empty.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise _error(
            "input_too_large",
            "The DOCX exceeds the upload size limit.",
            size_bytes=len(payload),
            limit_bytes=MAX_UPLOAD_BYTES,
        )
    return payload, filename


def _validated_docx_buffer(payload: bytes) -> io.BytesIO:
    buffer = io.BytesIO(payload)
    try:
        with zipfile.ZipFile(buffer) as package:
            members = package.infolist()
            names = {member.filename for member in members}
            expanded_size = sum(member.file_size for member in members)
            if len(members) > MAX_DOCX_MEMBERS:
                raise _error("docx_too_many_parts", "The DOCX contains too many internal parts.")
            if expanded_size > MAX_UNCOMPRESSED_DOCX_BYTES:
                raise _error(
                    "docx_uncompressed_too_large",
                    "The DOCX is too large after decompression.",
                    size_bytes=expanded_size,
                    limit_bytes=MAX_UNCOMPRESSED_DOCX_BYTES,
                )
            if len(names) != len(members):
                raise _error("invalid_docx_package", "The DOCX contains duplicate internal parts.")
            for member in members:
                path = PurePosixPath(member.filename)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in member.filename
                    or member.flag_bits & 1
                ):
                    raise _error("invalid_docx_package", "The DOCX contains unsafe internal parts.")
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise _error("invalid_docx_package", "The file is not a valid DOCX package.")
            for member in members:
                if member.filename.endswith((".xml", ".rels")):
                    with package.open(member) as stream:
                        for _, element in iterparse(stream, events=("end",), forbid_dtd=True):
                            element.clear()
    except (DefusedXmlException, ParseError) as error:
        raise _error("invalid_docx_xml", "The DOCX contains unsafe or malformed XML.") from error
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError) as error:
        raise _error("invalid_docx_zip", "The file could not be read as a valid DOCX.") from error
    buffer.seek(0)
    return buffer
