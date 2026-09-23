# Standardisasi qaos-common

Baseline: `qaos-common==0.2.2`, schema `dictionary/1.0`.
Wheel disalin tanpa modifikasi dari `../qaos_common/dist/` ke `vendor/`.
SHA-256:

```text
f0218d9a9e670fdf997dd69c16c8eccb8bc55414a196c449f64c35d3959a0588
```

Instal dari root proyek (Python 3.11–3.13):

```sh
python -m pip install --find-links ./vendor '.[dev,ui]'
python -m pip check
python -m pytest
```

`requirements.txt` dan `requirements-lock.txt` juga menunjuk `vendor/`.
Tes integrasi memverifikasi hash wheel dan versi yang terpasang.

## Batas kontrak

- Schema, urutan kolom, marker `NA`, dan validasi baris berasal dari common.
- `DictionaryCSVWriter` dengan `DictionaryCSVProfile(line_ending="\r\n")`
  mempertahankan tab, UTF-8 BOM, CRLF, dan QUOTE_MINIMAL.
- Validasi baris mencakup ID unik dan signature data URI gambar. Konversi WebP,
  aturan definition wajib, normalisasi teks, serta prefix apostrof ID tetap lokal.
- Batas upload/cell/output berasal dari `DEFAULT_LIMITS`; writer turut membatasi
  jumlah baris menjadi 100.000. Batas ZIP/XML dan gambar sumber tetap lokal.
- QA memakai reader common yang memulihkan `csv.field_size_limit` setelah membaca.
  Budget input QA mengikuti budget output CSV (512 MiB).
- `CancellationToken` lama kini re-export token common; callable dan threading.Event
  tetap diterima. Pembatalan tetap menghasilkan `conversion_cancelled`.
- Callback lama dan checkpoint tetap menggunakan stage lama. Parameter opsional
  `common_progress_callback` menerima `qaos_common.ProgressEvent` dengan stage
  reading/validating/parsing/writing/completed dan field `current`.
  `ProgressEvent.to_common()` tersedia untuk adapter individual.
- `ConversionError` tetap merupakan ValueError dan mempertahankan `diagnostic`,
  `as_dict()`, serta pesan lama. Ia juga merupakan `QAOSCommonError` dengan
  `to_dict()` berisi code/message/stage/details yang sudah direduksi dari payload
  sensitif. Stage dapat null untuk error lokal. Kode limit lama tetap dipakai;
  kegagalan validator baru memakai `DICTIONARY_SCHEMA_INVALID`.
- `rows_to_csv` tetap menerima subset kolom untuk kompatibilitas utilitas lama;
  ekspor yang mencakup semua kolom dictionary wajib lolos validasi canonical.

Flask, CLI, ekstraksi DOCX, dan publikasi atomik CLI tetap menjadi tanggung jawab
proyek ini. `completed` menunjukkan konversi bytes selesai, sebelum publikasi CLI.

## Verifikasi

Sebelum migrasi: 38 tes lulus pada Python 3.11/macOS.
Setelah migrasi: 44 tes lulus; `pip check` dan `git diff --check` bersih.
Import diverifikasi berasal dari `.venv311/lib/python3.11/site-packages/qaos_common`.
Suite mencakup golden CSV byte-per-byte, CLI/web/QA, dan tes integrasi common:
round-trip bytes dengan/tanpa gambar, hash dependency, callback, pembatalan,
ID duplikat, gambar invalid, dan pemulihan batas parser global.
CI memasang wheel yang sama untuk Python 3.11/3.12/3.13. Eksekusi lokal tidak
membuktikan hasil pada Windows atau interpreter lain.
