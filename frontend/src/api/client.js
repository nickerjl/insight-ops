// InsightOps API client.
// In local dev the Vite dev server proxies /api, /health, /demo to the API.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.error?.message) detail = body.error.message;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return response.json();
}

// Trigger an error endpoint. The 5xx is the INTENDED outcome of the demo, so
// unlike `request` it does not throw on the error status — it just resolves
// with the status so the UI knows the error was generated.
async function triggerError(path) {
  const response = await fetch(`${BASE_URL}${path}`);
  await response.text().catch(() => {});
  return { status: response.status, ok: response.ok };
}

export const api = {
  health: () => request("/health"),
  ready: () => request("/ready"),
  recentErrors: (limit = 50) => request(`/api/errors/recent?limit=${limit}`),
  aggregations: (limit = 100) => request(`/api/errors/aggregations?limit=${limit}`),
  recentLogs: (source = "api", limit = 100) =>
    request(`/api/logs/recent?source=${source}&limit=${limit}`),
  triggerDemoError: (kind) => triggerError(`/demo/error/${kind}`),
  dispatchDemoTask: (kind) =>
    request("/api/tasks/demo", { method: "POST", body: JSON.stringify({ kind }) }),
  taskStatus: (taskId) => request(`/api/tasks/${taskId}`),
  createInvestigation: (query) =>
    request("/api/investigations", { method: "POST", body: JSON.stringify({ query }) }),
  investigation: (id) => request(`/api/investigations/${id}`),
};
