# Approved Production Golden Files

This directory contains the approved production regression pair:

- `production_dictionary.docx` — source fixture;
- `production_dictionary.expected.csv` — approved byte-exact output; and
- `manifest.json` — immutable sizes, SHA-256 hashes, schema, and counts.

`tests/test_golden_file.py` first verifies that neither fixture has changed and
then converts the DOCX and compares the generated CSV with the approved CSV
byte for byte.

Do not regenerate the expected CSV merely because the golden test fails. A
change requires all of the following:

1. an intentional output-contract change;
2. downstream review in Excel and the consuming system;
3. explicit project-owner approval; and
4. updated manifest hashes and approval date.

These files are exceptions to the repository-wide `*.docx` and `*.csv` ignore
rules. Ordinary local input and output files remain ignored.
