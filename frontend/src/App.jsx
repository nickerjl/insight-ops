import { useEffect, useState } from "react";
import { api } from "./api/client";
import StatusCard from "./components/StatusCard";
import AggregationTable from "./components/AggregationTable";
import InvestigationPanel from "./components/InvestigationPanel";
import TaskDemo from "./components/TaskDemo";
import ErrorTrigger from "./components/ErrorTrigger";
import LogTable from "./components/LogTable";

export default function App() {
  const [health, setHealth] = useState(null);
  const [ready, setReady] = useState(null);
  const [aggregations, setAggregations] = useState({ aggregations: [], count: 0 });
  const [apiLogs, setApiLogs] = useState([]);
  const [taskLogs, setTaskLogs] = useState([]);
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [h, r, aggData, apiLogsData, taskLogsData] = await Promise.all([
          api.health(),
          api.ready(),
          api.aggregations(),
          api.recentLogs("api", 200),
          api.recentLogs("dramatiq", 200),
        ]);
        if (cancelled) return;
        setHealth(h);
        setReady(r);
        setAggregations(aggData);
        setApiLogs(apiLogsData.logs || []);
        setTaskLogs(taskLogsData.logs || []);
        setError(null);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  function refresh() {
    setRefreshKey((k) => k + 1);
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>InsightOps</h1>
        <p className="subtitle">Observability &amp; AI-assisted debugging</p>
        <button className="button ghost" onClick={refresh}>
          Refresh
        </button>
      </header>

      {error && <div className="banner error">Failed to load: {error}</div>}

      <section className="grid">
        <StatusCard health={health} ready={ready} />
        <TaskDemo onDispatched={refresh} />
      </section>

      <section className="grid">
        <ErrorTrigger onDispatched={refresh} />
        <AggregationTable aggregations={aggregations.aggregations} />
      </section>

      <section className="grid">
        <LogTable
          title="API Logs"
          logs={apiLogs}
          columns={[
            { key: "timestamp", label: "Timestamp" },
            { key: "source", label: "Source" },
            { key: "endpoint_name", label: "Endpoint" },
            { key: "status_code", label: "Status" },
            { key: "duration_ms", label: "Duration (ms)" },
          ]}
        />
        <LogTable
          title="Dramatiq Logs"
          logs={taskLogs}
          columns={[
            { key: "timestamp", label: "Timestamp" },
            { key: "source", label: "Source" },
            { key: "actor_name", label: "Task" },
            { key: "duration_s", label: "Duration (s)" },
            { key: "retry_count", label: "Retries" },
          ]}
        />
      </section>

      <InvestigationPanel />
    </div>
  );
}
