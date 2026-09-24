# Offline wheelhouse

This directory contains runtime wheels for the QAOS dictionary producer and
its transitive runtime dependencies. It includes macOS ARM64 wheels for local
development and Linux x86_64 CPython 3.11 wheels for the SaaS baseline.

Install the package without network access after building the package artifact:

```sh
python -m pip install --no-index --find-links ./wheelhouse \
  dist/qaos_dictionary-1.0.0-py3-none-any.whl
python -m pip check
```

The exact wheel hashes are recorded in `SHA256SUMS`. The `qaos-common` wheel
is the pinned 0.2.2 release and matches the hash in `vendor/SHA256SUMS`.
