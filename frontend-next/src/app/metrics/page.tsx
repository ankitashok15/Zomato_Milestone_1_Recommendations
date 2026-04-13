"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/Button";
import { STREAMLIT_APP_URL, isStreamlitBackendMode } from "@/lib/runtimeConfig";
import { apiGet } from "@/lib/api";

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
    if (!isStreamlitBackendMode()) loadMetrics();
  }, [loadMetrics]);

  if (isStreamlitBackendMode()) {
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
            FastAPI metrics (<code>/health/detailed</code>, <code>/ui-api/metrics</code>) are not available when the app
            runs in <strong>Streamlit-connected</strong> mode. Open{" "}
            <a href={STREAMLIT_APP_URL} target="_blank" rel="noopener noreferrer">
              your Streamlit app
            </a>{" "}
            for the live recommender, or deploy FastAPI and set <code>NEXT_PUBLIC_BACKEND_MODE=fastapi</code> with{" "}
            <code>BACKEND_URL</code>.
          </p>
        </section>
      </>
    );
  }

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
