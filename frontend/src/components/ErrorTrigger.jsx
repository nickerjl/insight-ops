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
  const [busy, setBusy] = useState(null);
  const [lastGenerated, setLastGenerated] = useState(null);

  async function trigger(kind) {
    setBusy(kind);
    setLastGenerated(null);
    try {
      const res = await api.triggerDemoError(kind);
      // Show a subtle confirmation that the error was generated (a 500 here is
      // the intended outcome of the demo, not a failure).
      setLastGenerated({ kind, status: res.status });
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
            disabled={busy !== null}
            onClick={() => trigger(b.kind)}
          >
            {busy === b.kind ? "Triggering…" : b.label}
          </button>
        ))}
      </div>
      {lastGenerated && (
        <p className="trigger-confirm">
          ✓ Generated {lastGenerated.kind} error — status {lastGenerated.status}. Refresh or
          check the logs below.
        </p>
      )}
    </div>
  );
}
