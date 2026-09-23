# Build and release gates

Install with a supported Python 3.11–3.13 interpreter:

```sh
python scripts/verify_wheel.py
python -m pip install -r requirements-lock.txt
python -m pip install --no-build-isolation --find-links ./vendor -e '.[dev,ui]'
python -m pip check
ruff check .
ruff format --check .
mypy
python -m pytest --cov --cov-report=term-missing --cov-report=xml:reports/coverage.xml
bandit -r src
python scripts/audit_dependencies.py
python -m tests.performance.benchmark_pipeline --iterations 3
python -m build --no-isolation
python -m twine check dist/*.whl dist/*.tar.gz
python scripts/clean_install.py
python scripts/provenance.py --release
```

Use an empty dist directory for a new version: the gate rejects ambiguous
artifact sets. Build creates wheel and sdist; clean_install creates two fresh
virtualenvs outside the checkout, installs each artifact, runs Python -I smoke
checks for base and UI installs, verifies legacy imports and py.typed, checks
packaged templates/static files and conversion bytes, invokes both CLI entry
points, and runs pip check. Base install must not bring in Flask. Dependencies
can be provided offline through `--wheelhouse /path/to/wheels`, including
setuptools and wheel for sdist build isolation.

CI runs lint, strict typing and 85% branch coverage on Python 3.11/3.12/3.13;
security and the three-run performance budget are separate required jobs. The
performance runner is macos-14; the historical baseline was calibrated on local
Apple Silicon/macOS 26. The existing 16-second/256-MiB budgets are retained.
CI results on that runner must be observed before claiming cross-machine timing
stability; change budgets only with reviewed calibration evidence. Artifact
build/clean-install/provenance runs only after all preceding jobs pass.

## Provenance

`dist/provenance.json` records package/version, source commit, dirty state,
UTC timestamp, build tool versions, platform/Python, artifact SHA-256/size,
qaos-common wheel SHA-256, lock hash, golden-fixture manifest hash, performance
budget hash, and available CI repository/run identifiers. `dist/SHA256SUMS`
provides checksums for the wheel and sdist. CI uploads these together.

`--release` rejects a dirty checkout and requires any GitHub tag to match
`v<package version>`. Local work may use provenance.py without --release; the
manifest explicitly records dirty=true and must not be represented as a clean
release. The sdist hash identifies the actual bundled source even in that case.
This manifest is unsigned and is not a cryptographic builder attestation.
No registry publication or tag is created by these scripts.

Release checklist: review compatibility/security changes; choose a version;
commit reviewed source; run all gates on that commit; retain CI evidence and
artifact checksums; publish only the exact verified artifacts through the
project's approved release channel. Lock updates must be accompanied by audit
and regression results; common wheel version/hash must remain aligned with the
other migrated QAOS consumers.
