"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/Button";
import { STREAMLIT_APP_URL, isStreamlitBackendMode } from "@/lib/runtimeConfig";
import type { HistoryEntry } from "@/lib/types";
import { STORAGE_KEY_HISTORY } from "@/lib/types";

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  const loadHistory = useCallback(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_HISTORY);
      setHistory(raw ? (JSON.parse(raw) as HistoryEntry[]) : []);
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const clear = () => {
    localStorage.removeItem(STORAGE_KEY_HISTORY);
    loadHistory();
  };

  return (
    <>
      <div className="divider-trio" aria-hidden>
        <span />
        <span />
        <span />
      </div>

      <section className="card">
        <h1>Request history</h1>
        <p className="muted" style={{ marginTop: 0 }}>
          Stored in this browser only (same key as the legacy UI).
        </p>
        {isStreamlitBackendMode() ? (
          <p className="muted">
            Recommendations on{" "}
            <a href={STREAMLIT_APP_URL} target="_blank" rel="noopener noreferrer">
              Streamlit
            </a>{" "}
            use that session; this page only lists requests made from this Next.js site (e.g. after switching to FastAPI
            mode).
          </p>
        ) : null}
        <div className="row-actions">
          <Button variant="secondary" onClick={clear}>
            Clear history
          </Button>
        </div>
      </section>

      <section className="card">
        {!history.length && <p className="muted">No history found yet. Run recommendations from Home first.</p>}
        {history.map((entry) => (
          <div key={`${entry.request_id}-${entry.created_at}`} className="history-item">
            <h2 className="heading" style={{ fontSize: "1.05rem" }}>
              {entry.location} |{" "}
              {entry.budget_amount != null
                ? `up to ₹${entry.budget_amount} (two)`
                : entry.budget
                  ? `${entry.budget} budget`
                  : "—"}
            </h2>
            <p>
              <strong>Request ID:</strong> {entry.request_id}
            </p>
            <p>
              <strong>Cuisine:</strong> {(entry.cuisine || []).join(", ")}
            </p>
            <p>
              <strong>Results:</strong> {entry.result_count}
            </p>
            {entry.summary && <p className="muted">{entry.summary}</p>}
            <p className="muted">{new Date(entry.created_at).toLocaleString()}</p>
          </div>
        ))}
      </section>
    </>
  );
}
