import { useState } from "react";

function formatTime(epoch) {
  if (!epoch) return "—";
  try {
    return new Date(Number(epoch) * 1000).toISOString().replace("T", " ").slice(0, 19);
  } catch {
    return "—";
  }
}

export default function AggregationTable({ aggregations }) {
  const [expandedFp, setExpandedFp] = useState(null);

  return (
    <div className="card">
      <h2>Error Aggregations</h2>
      {aggregations.length === 0 ? (
        <p className="muted">
          No error fingerprints aggregated yet. Hit a 5xx demo endpoint to get started.
        </p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Display Name</th>
              <th>Source</th>
              <th>Count</th>
              <th>First seen</th>
              <th>Last seen</th>
              <th>Commit</th>
            </tr>
          </thead>
          <tbody>
            {aggregations.map((agg) => {
              const fp = agg.fingerprint;
              const expanded = expandedFp === fp;
              return (
                <AggRow
                  key={fp}
                  agg={agg}
                  expanded={expanded}
                  onToggle={() => setExpandedFp(expanded ? null : fp)}
                />
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

function AggRow({ agg, expanded, onToggle }) {
  return (
    <>
      <tr className="clickable" onClick={onToggle}>
        <td>
          {agg.display_name || agg.endpoint || agg.error_type}
          {expanded ? " ▴" : " ▾"}
        </td>
        <td>
          <span className={`pill ${agg.source === "task" ? "warn" : "ok"}`}>
            {agg.source || "api"}
          </span>
        </td>
        <td>
          <strong>{agg.count}</strong>
        </td>
        <td>{formatTime(agg.first_seen)}</td>
        <td>{formatTime(agg.last_seen)}</td>
        <td>
          <code className="mono-small">{agg.commit_hash ? agg.commit_hash.slice(0, 10) : "—"}</code>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={6}>
            <div className="agg-detail">
              <div className="agg-detail-grid">
                <span>Error type</span>
                <strong>{agg.error_type}</strong>
                <span>Endpoint</span>
                <strong>{agg.endpoint || "—"}</strong>
                <span>Method</span>
                <strong>{agg.method || "—"}</strong>
                <span>Latest message</span>
                <strong>{agg.message || "—"}</strong>
                <span>Source</span>
                <strong>{agg.source || "api"}</strong>
                <span>Fingerprint</span>
                <code className="mono-small">{agg.fingerprint}</code>
              </div>
              {agg.latest_event && agg.latest_event.exception ? (
                <div className="log-detail-wrap">
                  <strong>{agg.latest_event.exception.type || "—"}</strong>
                  <span className="muted"> · {agg.latest_event.exception.message || ""}</span>
                  <details open>
                    <summary>Traceback</summary>
                    <pre className="log-detail">{agg.latest_event.exception.traceback || "—"}</pre>
                  </details>
                </div>
              ) : null}
              {(agg.latest_event || agg.message) && (
                <details>
                  <summary>Latest log (raw)</summary>
                  <pre className="log-detail">{JSON.stringify(agg.latest_event || agg, null, 2)}</pre>
                </details>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
