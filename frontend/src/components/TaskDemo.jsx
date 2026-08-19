import { useState } from "react";
import { api } from "../api/client";

export default function TaskDemo({ onDispatched }) {
  const [kind, setKind] = useState("success");
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function dispatch() {
    setBusy(true);
    setError(null);
    setStatus(null);
    setTaskId(null);
    try {
      const response = await api.dispatchDemoTask(kind);
      setTaskId(response.task_id);
      setStatus(response.status);
      poll(response.task_id);
      onDispatched();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  async function poll(id, attempts = 0) {
    try {
      const data = await api.taskStatus(id);
      setStatus(data.status);
      if (data.status !== "completed" && data.status !== "failed" && attempts < 40) {
        setTimeout(() => poll(id, attempts + 1), 1500);
      } else if (attempts >= 40) {
        setError("Timed out waiting for the task to finish.");
      }
      setBusy(false);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Async Task Demo</h2>
      <p className="muted">
        Enqueue a Dramatiq task to demonstrate asynchronous processing with
        retry/backoff (max 3 retries).
      </p>
      <div className="task-demo">
        <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Task kind">
          <option value="success">Succeeds</option>
          <option value="failure">Fails (retries)</option>
        </select>
        <button className="button primary" onClick={dispatch} disabled={busy}>
          {busy ? "Dispatching…" : "Dispatch"}
        </button>
      </div>
      {error && <div className="banner error">{error}</div>}
      {taskId && (
        <p className="muted">
          Task <code className="mono-small">{taskId}</code> — status: {status}
        </p>
      )}
    </div>
  );
}
