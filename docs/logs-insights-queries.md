# CloudWatch Logs Insights queries

InsightOps publishes one structured JSON log line per request/event to the
CloudWatch log group `/insight-ops/prod` (stream prefixes `api` and
`worker`). These queries demonstrate the observability workflow.

## Filter by status code (5xx)

```text
fields @timestamp, @log, endpoint, status_code, error_type, error_message, request_id
| filter status_code >= 500
| sort @timestamp desc
| limit 50
```

## Filter by endpoint

```text
fields @timestamp, endpoint, status_code, error_type
| filter endpoint = "/api/payments"
| sort @timestamp desc
```

## Filter by IP address

```text
fields @timestamp, ip_address, endpoint, status_code, request_id
| filter ip_address = "10.0.1.25"
```

## Search by keyword

```text
fields @timestamp, endpoint, error_message, error_type
| filter error_message like /timeout/
| sort @timestamp desc
```

## Search by request ID (correlation)

```text
fields @timestamp, request_id, endpoint, method, status_code
| filter request_id = "abc-123"
```

## Search by deployment (commit hash)

```text
fields @timestamp, commit_hash, endpoint, status_code
| filter commit_hash = "8f31a2c"
```

## Error-type distribution (aggregation)

```text
fields error_type, count(*) as occurrences
| stats count(*) by error_type
| sort occurrences desc
```

## Slowest requests

```text
fields @timestamp, endpoint, duration_ms
| filter ispresent(duration_ms)
| sort duration_ms desc
| limit 20
```

## Worker task activity

```text
fields @timestamp, message, task_id, retry_count, error_type
| filter @log like /worker/
| filter ispresent(task_id)
| sort @timestamp desc
```

---

The same fields are also available in the Redis-backed aggregation store via
`GET /api/errors/aggregations`; CloudWatch is the persistent, queryable log
source and Redis only holds temporary aggregation state (TTL bounded).
