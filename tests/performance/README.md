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
