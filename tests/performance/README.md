# Performance Test

The benchmark converts the approved production golden DOCX in three isolated
Python processes. Isolation prevents memory retained by an earlier iteration
from contaminating a later measurement.

Run the required performance test:

```bash
.venv/bin/python -m tests.performance.benchmark_pipeline
```

The command measures wall-clock conversion duration and maximum resident set
size (peak RSS). It also verifies row count, image count, and output SHA-256
against `thresholds.json`.

The generated machine-readable report is written to:

```text
reports/performance/latest.json
```

Recalibrate without enforcing existing thresholds:

```bash
.venv/bin/python -m tests.performance.benchmark_pipeline --no-thresholds
```

Threshold changes require review. They must not be increased only to hide a
performance regression.

CI now invokes this command as a blocking job on macos-14, independently of
coverage instrumentation. The unit suite also verifies that exceeding duration
or memory by even a small amount fails and that the CLI writes FAILED and exits
1. The metric-collection smoke test alone is not a regression gate.

The budget remains 16 seconds median over three isolated runs and 256 MiB
maximum RSS, plus exact row/image counts and output SHA-256. The historical
baseline remains unchanged; new local measurements are evidence rather than an
automatic recalibration. This budget catches regressions that cross the limits;
it does not promise to detect every slowdown below them.
