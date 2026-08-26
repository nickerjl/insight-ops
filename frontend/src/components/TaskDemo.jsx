import { useState } from "react";
import { api } from "../api/client";

export default function TaskDemo({ onDispatched }) {
  const [kind, setKind] = useState("success");
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [retryCount, setRetryCount] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function dispatch() {
    setBusy(true);
    setError(null);
    setStatus(null);
    setTaskId(null);
    setRetryCount(null);
    try {
      const response = await api.dispatchDemoTask(kind);
      setTaskId(response.task_id);
      poll(response.task_id);
      onDispatched();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  // Poll until a SUCCESS or a TERMINAL failure (retries exhausted). A
  // non-terminal "failed" just means the current attempt threw and the
  // middleware is about to retry with backoff — keep polling to show it.
  async function poll(id, attempts = 0) {
    try {
      const data = await api.taskStatus(id);
      setStatus(data.status);
      setRetryCount(data.retries ?? null);
      const done =
        data.status === "completed" ||
        (data.status === "failed" && data.terminal === "true");
      if (!done && attempts < 40) {
        setTimeout(() => poll(id, attempts + 1), 1000);
      } else if (!done && attempts >= 40) {
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

      {taskId && (
        <div className="task-result">
          <p className={status === "failed" ? "banner error" : "muted"}>
            Task <code className="mono-small">{taskId}</code> — status: {status}
            {retryCount !== null && retryCount > 0 && (
              <> · retries: <strong>{retryCount}/3</strong></>
            )}
            {retryCount !== null && retryCount > 0 && retryCount < 3 && (
              <> · <em>backing off, will retry…</em></>
            )}
          </p>
          {status === "completed" && (
            <p className="muted">
              ✓ Succeeded on attempt {Number(retryCount ?? 0) + 1}.
            </p>
          )}
          {status === "failed" && retryCount === "3" && (
            <p className="muted">
              ✓ Retried 3 times (backoff 1s → 2s → 4s) then dead-lettered. See
              the worker logs in CloudWatch (/insight-ops/prod) for the
              retry_count sequence 0→3.
            </p>
          )}
        </div>
      )}
      {error && <div className="banner error">{error}</div>}
    </div>
  );
}
