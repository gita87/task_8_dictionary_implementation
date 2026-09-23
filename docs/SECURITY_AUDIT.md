# Security audit — 2026-09-23

Scope: local source review of the conversion/CLI/Flask boundaries, adversarial
regression tests, Bandit on src, and pip-audit of the installed third-party
runtime/UI dependency closure. This is not an external penetration test or a
claim of safety for every deployment. Local qaos-common 0.2.2 is verified against
its release SHA-256; it and this unpublished package are not queried as registry
packages. Their third-party dependencies are still audited.

## Reviewed boundaries and remediation

| Boundary | Control / result |
| --- | --- |
| Input size | Bounded read plus one byte; bytes-only stream result; 256 MiB limit |
| ZIP | 512 MiB expanded/10,000 parts; no filesystem extraction; reject duplicate, traversal/absolute/backslash paths and encrypted entries |
| XML | Added defusedxml preflight to each XML/relationship part, rejecting DTD, entities and malformed XML before python-docx parses it |
| Images | MIME/format agreement, byte limit, Pillow decompression protections, WebP re-encoding, common signature validation |
| CSV | Cell checks precede image base64 validation; shared writer enforces output/row limits; safe shared reader restores parser globals |
| Output publication | Atomic sibling replacement; cleanup now covers failures during flush/fsync and interrupts |
| Diagnostics | Shared recursive redaction; tests cover raw bytes, base64 and data URIs |
| Browser | Jinja autoescape, CSP, nosniff, frame denial, no-store; fixed local browser command uses absolute executable and no shell |

Bandit exemptions are narrow and documented: B105 on the literal QA status
`pass`; B404/B603 for the fixed `/usr/bin/open` command; B405 for importing only
the ParseError exception class (actual parsing uses defusedxml). No broad rule
exclusions or severity filters are used.

## Residual limits

Public deployments need authentication/rate/concurrency controls and isolated
worker memory/time budgets. The local Flask development server is not a public
hosting configuration. ZIP limits bound archive content, not Python object
allocation or total process RSS. Image encoding and XML parsing are synchronous;
cancellation does not preempt their individual calls. CSV word/definition text
is intentionally preserved: spreadsheet applications may interpret formula-like
text, so import those columns as text when opening untrusted dictionaries.
Changing those cells automatically would change the shared output contract.

## Repeatable gates

```sh
python scripts/verify_wheel.py
bandit -r src -f json -o reports/security/bandit.json
python scripts/audit_dependencies.py
python -m pytest tests/test_security_contract.py
```

The dependency audit writes the exact audited pins and machine-readable findings
under reports/security. It fails on reported vulnerabilities or lookup errors;
unavailable network is not treated as a clean audit. CI retains the reports.
Known-vulnerability results are a point-in-time observation and must be rerun
for a release. See RELEASE.md for artifact provenance and release gates.
