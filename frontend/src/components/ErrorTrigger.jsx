import { useState } from "react";
import { api } from "../api/client";

const BUTTONS = [
  { kind: "undefined-name", label: "Undefined name" },
  { kind: "zero-division", label: "ZeroDivision" },
  { kind: "attr-error", label: "AttributeError" },
  { kind: "key-error", label: "KeyError" },
  { kind: "payment-timeout", label: "Payment timeout" },
];

export default function ErrorTrigger({ onDispatched }) {
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null);

  async function trigger(kind) {
    setBusy(kind);
    setError(null);
    try {
      await api.triggerDemoError(kind);
    } catch (err) {
      // Deliberately consume the request error: the server returned 500 as
      // designed. The point is to generate a log/aggregation entry.
      if (err?.message && !String(err.message).includes("500")) {
        setError(err.message);
      }
    } finally {
      setBusy(null);
      if (onDispatched) onDispatched();
    }
  }

  return (
    <div className="card">
      <h2>Trigger Errors</h2>
      <p className="muted">
        Hit the error-generation endpoints to feed the logs and aggregation tables.
      </p>
      <div className="error-buttons">
        {BUTTONS.map((b) => (
          <button
            key={b.kind}
            className="button danger"
            disabled={busy === b.kind}
            onClick={() => trigger(b.kind)}
          >
            {busy === b.kind ? "Triggering…" : b.label}
          </button>
        ))}
      </div>
      {error && <div className="banner error">{error}</div>}
    </div>
  );
}
