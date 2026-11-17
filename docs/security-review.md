# Security review and limitations

The scope is a **loopback-only demonstration using fictional data**, not an audit of a production deployment. Tests prove specific local behavior; they are not a penetration test or a GDPR certification.

| Concern | Implemented in demo | Production gap |
| --- | --- | --- |
| Authentication | Required bearer token for leads API | Users, roles, rotation, rate limits, audit logging |
| Credentials | Environment variable, not committed | Managed secret store and secret rotation |
| Transport | HTTPS enforced for non-local HTTP client targets; local API binds loopback by default | TLS termination, reverse proxy policy, HSTS, infrastructure |
| Input | Pydantic constraints, strict CSV headers, sanitized error summaries | Data retention/deletion, provenance, consent, enterprise DLP |
| Idempotency | Unique external IDs, hashed normalized content, 409 on conflict | Replay windows, audit history, customer-defined merge policy |
| SQLite | Parameterized queries, bounded query pagination | Backups, migrations, concurrent writes, recovery runbooks |
| Retry | 2 default retries on transient errors; finite numeric Retry-After | Provider-specific budgets and rate-limit handling |
| Dashboard | Token entered locally, held only in page memory; DOM uses textContent for user data | Browser hardening, session management, CSP and public hosting review |
| Observability | Count-only JSON report and tests | Correlation IDs, structured monitoring, alerting, privacy review |

The dashboard's HTML shell is public on localhost, but the actual lead listing is protected by the same API bearer token. Do not expose this demo server to the public Internet. Public health and documentation routes are suitable only for local demonstration as configured.

## Threat-informed decisions

* Malformed or ambiguous CSV headers fail **before network transmission**.
* Unsanitized lead values are never inserted into HTML strings; the dashboard uses `textContent`.
* Retry delays reject non-finite numeric values such as `NaN`, which would otherwise cause bad sleeps.
* API listing uses bounded pagination rather than returning the entire table.
* The screenshot generator may use a browser-network fallback in managed environments that block localhost navigation. Its fallback uses a **real HTTP API response** retrieved by Python; browser network success is not claimed.

## For a real customer integration

1. Obtain official CRM API documentation and field mapping.
2. Specify access scopes, permitted data, lawful basis and retention/deletion rules.
3. Implement a provider adapter and staging tests with synthetic or approved anonymized data.
4. Add production authentication, monitoring, deployment hardening, backups and disaster recovery.
5. Obtain separate client approval before processing personal or organizational records.

* Database transactions now explicitly close SQLite connections in `finally`, confirmed by a regression test; no resource warnings were observed in the final coverage test.
