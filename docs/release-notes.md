# Release notes: 1.0 → 2.0

Changes to the local portfolio demonstration, not a public deployment.

| Aspect | 1.0 baseline | 2.0 implemented |
| --- | --- | --- |
| Validation | Required headers validated | Duplicate and unexpected headers are rejected before API calls |
| Retry handling | Bounded retries | Non-finite `Retry-After` values safely fall back to bounded backoff |
| API listing | Unbounded listing | Paginated with `limit`, `offset`, `count`, `total` |
| SQLite lifecycle | Context manager committed but did not always close handles | Explicit `finally` close, covered by regression test |
| User interface | CLI and Swagger docs | New read-only local HTML dashboard with runtime API token |
| Gallery | Two 1600 × 900 visuals | Three 4:3 portfolio visuals, including a dashboard screenshot |
| Upwork assets | Generic 16:9 media | 1000 × 750 upload PNGs plus original source assets |
| Automated tests | 14 existing tests | 21 tests including new regression cases |
| Documentation | Technical demo overview | Client-oriented case study, practical setup, limitations and release comparison |

The project still uses a local simulated CRM, not a third-party vendor. No production readiness, customer ROI or real-world CRM delivery is implied.
