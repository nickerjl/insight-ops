import { useEffect, useState } from "react";
import { api } from "./api/client";
import StatusCard from "./components/StatusCard";
import ErrorPanel from "./components/ErrorPanel";
import AggregationTable from "./components/AggregationTable";
import InvestigationPanel from "./components/InvestigationPanel";
import TaskDemo from "./components/TaskDemo";

export default function App() {
  const [health, setHealth] = useState(null);
  const [ready, setReady] = useState(null);
  const [recent, setRecent] = useState({ events: [], count: 0 });
  const [aggregations, setAggregations] = useState({ aggregations: [], count: 0 });
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [h, r, recentData, aggData] = await Promise.all([
          api.health(),
          api.ready(),
          api.recentErrors(),
          api.aggregations(),
        ]);
        if (cancelled) return;
        setHealth(h);
        setReady(r);
        setRecent(recentData);
        setAggregations(aggData);
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
        <ErrorPanel events={recent.events} />
        <AggregationTable aggregations={aggregations.aggregations} />
      </section>

      <InvestigationPanel />
    </div>
  );
}
