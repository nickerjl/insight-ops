import { useState } from "react";

const PAGE_SIZE = 20;
const TRACE_FIELD = "exception";

export default function LogTable({ title, logs, columns, defaultPageSize = PAGE_SIZE }) {
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [page, setPage] = useState(0);

  if (!logs || logs.length === 0) {
    return (
      <div className="card">
        <h2>{title}</h2>
        <p className="muted">No logs yet — generate some traffic to see entries.</p>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(logs.length / defaultPageSize));
  const start = page * defaultPageSize;
  const pageLogs = logs.slice(start, start + defaultPageSize);

  return (
    <div className="card">
      <h2>{title}</h2>
      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key}>{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageLogs.map((log, idx) => {
              const absoluteIndex = start + idx;
              return (
                <FragmentRow
                  key={`${title}-${absoluteIndex}`}
                  columns={columns}
                  log={log}
                  expanded={expandedIndex === absoluteIndex}
                  onToggle={() =>
                    setExpandedIndex(expandedIndex === absoluteIndex ? null : absoluteIndex)
                  }
                />
              );
            })}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="pagination">
          <button
            className="button ghost small"
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            ‹ Prev
          </button>
          <span className="muted">
            Page {page + 1} / {totalPages} · {logs.length} rows
          </span>
          <button
            className="button ghost small"
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
          >
            Next ›
          </button>
        </div>
      )}
    </div>
  );
}

function FragmentRow({ columns, log, expanded, onToggle }) {
  return (
    <>
      <tr className="clickable" onClick={onToggle}>
        {columns.map((c) => {
          const raw = log[c.key];
          const value = formatValue(c.key, raw);
          return (
            <td key={c.key} title={raw === null || raw === undefined ? "—" : String(raw)}>
              {value}
            </td>
          );
        })}
      </tr>
      {expanded && (
        <tr>
          <td colSpan={columns.length}>
            <ExpandedDetail log={log} />
          </td>
        </tr>
      )}
    </>
  );
}

// Format the timestamp cell as a readable ISO-8601 string. The stored value
// is already ISO-8601 (e.g. 2026-08-26T15:01:37Z); normalise it to include
// milliseconds and a clean Z so the table reads consistently.
function formatValue(key, raw) {
  if (raw === null || raw === undefined) return "—";
  if (key === "timestamp") {
    const iso = String(raw).replace("T", " ").replace("Z", " UTC");
    return iso;
  }
  return String(raw);
}

function ExpandedDetail({ log }) {
  // If this is a 5xx error log, surface the traceback prominently for ease
  // of debugging (the reason we widened the ring buffer to carry it).
  if (log[TRACE_FIELD]) {
    return (
      <div className="log-detail-wrap">
        <div className="agg-detail-grid">
          <span>Error type</span>
          <strong>{log[TRACE_FIELD].type || "—"}</strong>
          <span>Message</span>
          <strong>{log[TRACE_FIELD].message || "—"}</strong>
        </div>
        <details open>
          <summary>Traceback</summary>
          <pre className="log-detail">{log[TRACE_FIELD].traceback || "—"}</pre>
        </details>
        <details>
          <summary>Full log (JSON)</summary>
          <pre className="log-detail">{JSON.stringify(log, null, 2)}</pre>
        </details>
      </div>
    );
  }
  return <pre className="log-detail">{JSON.stringify(log, null, 2)}</pre>;
}
