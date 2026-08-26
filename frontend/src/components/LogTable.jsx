import { useState } from "react";

export default function LogTable({ title, logs, columns }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  if (!logs || logs.length === 0) {
    return (
      <div className="card">
        <h2>{title}</h2>
        <p className="muted">No logs yet — generate some traffic to see entries.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>{title}</h2>
      <table className="table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {logs.map((log, idx) => (
            <FragmentRow
              key={`${title}-${idx}`}
              columns={columns}
              log={log}
              index={idx}
              expanded={expandedIndex === idx}
              onToggle={() => setExpandedIndex(expandedIndex === idx ? null : idx)}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FragmentRow({ columns, log, index, expanded, onToggle }) {
  return (
    <>
      <tr className="clickable" onClick={onToggle}>
        {columns.map((c) => {
          const value = log[c.key];
          return (
            <td key={c.key} title={value === null || value === undefined ? "—" : String(value)}>
              {value === null || value === undefined ? "—" : String(value)}
            </td>
          );
        })}
      </tr>
      {expanded && (
        <tr>
          <td colSpan={columns.length}>
            <pre className="log-detail">{JSON.stringify(log, null, 2)}</pre>
          </td>
        </tr>
      )}
    </>
  );
}
