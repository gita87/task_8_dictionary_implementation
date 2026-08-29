# Dictionary DOCX-to-CSV Output Contract

## Status

This contract is mandatory for every output produced by the dictionary and
vocabulary DOCX conversion pipeline.

## File format

| Property | Required value |
| --- | --- |
| Filename extension | `.csv` |
| Encoding | UTF-8 with BOM |
| Initial bytes | `EF BB BF` |
| Field delimiter | Tab (`\t`) |
| Record line ending | CRLF (`\r\n`) |
| Quote character | Double quote (`"`) |
| Quote escaping | A double quote inside a quoted field is written as `""` |

Although the filename extension is `.csv`, the field delimiter is a tab by
downstream agreement.

## Schema

The output columns use lowercase names and this exact order:

1. `word` — required;
2. `definition` — required; and
3. `image` — included only when the selected DOCX table contains an `image`
   header.

Every emitted row must contain a non-empty `word` and `definition`. A fully
empty table row is ignored. A partially populated row with an empty required
cell is invalid and stops conversion with a row-specific error.

An `image` cell may be empty when its DOCX cell has no embedded image.

## Text normalization

The pipeline extracts plain visible paragraph text. Rich-text formatting,
highlighting, list markers, numbering metadata, and nested tables are not
preserved. Tabs, line breaks, and repeated whitespace in DOCX text are
normalized to a single ASCII space. Literal double quotes are retained and
escaped by the CSV serializer.

## Image representation

Every populated `image` value must have exactly this structure:

```text
data:image/webp;base64,<BASE64_PAYLOAD>
```

The required prefix is:

```text
data:image/webp;base64,
```

The value contains only the data URI. It must not contain an HTML element such
as `<img src="...">` or a framework binding such as `<img [src]="...">`.

PNG, JPEG, GIF, SVG, and other media-type prefixes are not permitted in the
CSV. Every embedded source image is converted to WebP. If conversion to WebP
fails, the complete DOCX conversion fails rather than emitting a fallback
format.

## Compatibility changes

Any modification to encoding, delimiter, line endings, schema, whitespace
normalization, quoting, or image representation is a breaking contract change.
It requires downstream approval and a reviewed update to the golden file.
