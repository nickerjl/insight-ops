function formatTime(epoch) {
  if (!epoch) return "—";
  try {
    return new Date(Number(epoch) * 1000).toISOString().replace("T", " ").slice(0, 19);
  } catch {
    return "—";
  }
}

export default function AggregationTable({ aggregations }) {
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
              <th>Error type</th>
              <th>Endpoint</th>
              <th>Count</th>
              <th>First seen</th>
              <th>Last seen</th>
              <th>Commit</th>
            </tr>
          </thead>
          <tbody>
            {aggregations.map((agg) => (
              <tr key={agg.fingerprint}>
                <td>{agg.error_type}</td>
                <td>
                  <code>{agg.endpoint}</code>
                </td>
                <td>
                  <strong>{agg.count}</strong>
                </td>
                <td>{formatTime(agg.first_seen)}</td>
                <td>{formatTime(agg.last_seen)}</td>
                <td>
                  <code className="mono-small">{agg.commit_hash}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
