export default function StatusCard({ health, ready }) {
  const healthy = health?.status === "ok";
  const readyOk = ready?.status === "ready";
  return (
    <div className="card">
      <h2>Application Status</h2>
      <div className="status-row">
        <span className={`pill ${healthy ? "ok" : "down"}`}>
          {healthy ? "Healthy" : "Unhealthy"}
        </span>
        <span className={`pill ${readyOk ? "ok" : "down"}`}>
          {readyOk ? "Ready" : "Not ready"}
        </span>
      </div>
      <dl className="details">
        <div>
          <dt>Service</dt>
          <dd>{health?.service ?? "—"}</dd>
        </div>
        <div>
          <dt>Commit</dt>
          <dd>{health?.commit_hash ?? "—"}</dd>
        </div>
        <div>
          <dt>Redis</dt>
          <dd>{ready?.checks?.redis ?? "—"}</dd>
        </div>
      </dl>
    </div>
  );
}
