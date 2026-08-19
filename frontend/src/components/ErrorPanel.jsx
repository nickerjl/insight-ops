export default function ErrorPanel({ events }) {
  return (
    <div className="card">
      <h2>Recent Errors</h2>
      {events.length === 0 ? (
        <p className="muted">No errors recorded yet. Try the demo error endpoints.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Endpoint</th>
              <th>Status</th>
              <th>Fingerprint</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event, index) => (
              <tr key={index}>
                <td>{event.error_type}</td>
                <td>
                  <code>{event.endpoint}</code>
                </td>
                <td>
                  <span className={`pill ${event.status_code >= 500 ? "error" : "warn"}`}>
                    {event.status_code}
                  </span>
                </td>
                <td>
                  <code className="mono-small" title={event.error_message}>
                    {event.fingerprint}
                  </code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
