# Screenshots

Add portfolio screenshots here (Phase 20):

- `dashboard.png` — the React dashboard (http://localhost:5173) showing
  Application Status, Async Task Demo, Recent Errors, Error Aggregations
  and the AI Investigation panel.
- `logs-insights.png` — a CloudWatch Logs Insights query result showing
  structured JSON request logs (e.g. filter `status_code >= 500`).
- `aggregations.png` — `GET /api/errors/aggregations` output with repeated
  `PaymentProviderTimeout` errors grouped under one fingerprint.
- `investigation.png` — an investigation result for
  "Why are payment errors increasing?" (requires `DEEPSEEK_API_KEY`).
- `pipeline.png` — the GitHub Actions workflow with test/build/deploy/smoke stages
  green.
