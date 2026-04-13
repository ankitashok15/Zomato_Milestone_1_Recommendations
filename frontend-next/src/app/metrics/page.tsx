"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { Button } from "@/components/Button";

export default function MetricsPage() {
  const [status, setStatus] = useState("");
  const [statusError, setStatusError] = useState(false);
  const [healthJson, setHealthJson] = useState<string>("");
  const [metricsJson, setMetricsJson] = useState<string>("");

  const loadMetrics = useCallback(async () => {
    setStatus("Loading metrics…");
    setStatusError(false);
    try {
      const healthData = await apiGet<Record<string, unknown>>("/health/detailed");
      setHealthJson(JSON.stringify(healthData, null, 2));

      const metricsData = await apiGet<Record<string, number>>("/ui-api/metrics");
      setMetricsJson(JSON.stringify(metricsData, null, 2));

      setStatus("Metrics loaded successfully.");
    } catch (err) {
      setStatusError(true);
      setStatus(err instanceof Error ? err.message : "Failed to load metrics.");
    }
  }, []);

  useEffect(() => {
    loadMetrics();
  }, [loadMetrics]);

  return (
    <>
      <div className="divider-trio" aria-hidden>
        <span />
        <span />
        <span />
      </div>

      <section className="card">
        <h1>Metrics &amp; health</h1>
        <p className="muted" style={{ marginTop: 0 }}>
          Proxied to the FastAPI backend via <code>/api/backend</code>.
        </p>
        <div className="row-actions">
          <Button variant="primary" onClick={loadMetrics}>
            Refresh
          </Button>
        </div>
        {status && <p className={`status-msg ${statusError ? "error" : ""}`}>{status}</p>}
      </section>

      <section className="card">
        <h2 className="heading">Health (detailed)</h2>
        <pre className="json-pre">{healthJson || "—"}</pre>
      </section>

      <section className="card">
        <h2 className="heading">Counters</h2>
        <pre className="json-pre">{metricsJson || "—"}</pre>
      </section>
    </>
  );
}
