import { useEffect, useState } from "react";
import { api } from "../api/client";

const POLL_INTERVAL_MS = 1500;
const MAX_POLLS = 60;

// Rotating placeholder examples — each is a realistic investigation question
// the system can actually answer from the aggregated error evidence.
const PLACEHOLDER_EXAMPLES = [
  "e.g. Why are payment errors increasing?",
  "e.g. Which errors came from background (dramatiq) tasks?",
  "e.g. What is the most frequent error today?",
  "e.g. What is the root cause of the latest NameError?",
  "e.g. Are the errors related to a specific deployment?",
];

export default function InvestigationPanel() {
  const [query, setQuery] = useState("");
  const [investigationId, setInvestigationId] = useState(null);
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);

  // Rotate the placeholder example every few seconds so users see the kinds
  // of questions the AI investigation can answer.
  useEffect(() => {
    const timer = setInterval(
      () => setPlaceholderIndex((i) => (i + 1) % PLACEHOLDER_EXAMPLES.length),
      4000
    );
    return () => clearInterval(timer);
  }, []);

  async function submit(event) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.createInvestigation(trimmed);
      setInvestigationId(response.investigation_id);
      setStatus("queued");
      poll(response.investigation_id);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  async function poll(id, attempts = 0) {
    try {
      const data = await api.investigation(id);
      setStatus(data.status);
      if (data.status === "completed" || data.status === "failed") {
        setResult(data);
        setLoading(false);
        return;
      }
      if (attempts < MAX_POLLS) {
        setTimeout(() => poll(id, attempts + 1), POLL_INTERVAL_MS);
      } else {
        setError("Investigation timed out while polling for a result.");
        setLoading(false);
      }
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  return (
    <div className="card wide">
      <h2>AI Investigation</h2>
      <form onSubmit={submit} className="investigation-form">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={PLACEHOLDER_EXAMPLES[placeholderIndex]}
          maxLength={500}
          aria-label="Investigation question"
        />
        <button className="button primary" type="submit" disabled={loading || !query.trim()}>
          {loading ? "Investigating…" : "Investigate"}
        </button>
      </form>

      {error && <div className="banner error">{error}</div>}

      {status && !result && <p className="muted">Status: {status}</p>}

      {result && (
        <div className="investigation-result">
          <span className={`pill ${result.status === "completed" ? "ok" : "error"}`}>
            {result.status}
          </span>
          {result.error ? (
            <p className="banner error">
              {result.error.type}: {result.error.message}
            </p>
          ) : (
            <>
              <h3>{result.result?.summary}</h3>
              <p>
                <strong>Likely cause:</strong> {result.result?.likely_cause}
              </p>
              <dl className="details">
                <div>
                  <dt>Endpoint</dt>
                  <dd>{result.result?.affected_endpoint ?? "—"}</dd>
                </div>
                <div>
                  <dt>Error type</dt>
                  <dd>{result.result?.error_type ?? "—"}</dd>
                </div>
                <div>
                  <dt>Deployment</dt>
                  <dd>{result.result?.deployment ?? "—"}</dd>
                </div>
              </dl>
              {result.result?.evidence?.length > 0 && (
                <details>
                  <summary>Supporting evidence ({result.result.evidence.length})</summary>
                  <ul>
                    {result.result.evidence.map((item, index) => (
                      <li key={index}>
                        <code>{item}</code>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
