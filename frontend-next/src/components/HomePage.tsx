"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import type { HistoryEntry, RecommendationResponse } from "@/lib/types";
import { STORAGE_KEY_HISTORY } from "@/lib/types";
import { Button } from "./Button";

export function HomePage() {
  const [localities, setLocalities] = useState<string[]>([]);
  const [cuisines, setCuisines] = useState<string[]>([]);
  const [location, setLocation] = useState("");
  const [budgetAmount, setBudgetAmount] = useState(1200);
  const [cuisineSelection, setCuisineSelection] = useState<Record<string, boolean>>({});
  const [minRating, setMinRating] = useState(3.8);
  const [topK, setTopK] = useState(5);
  const [partyType, setPartyType] = useState("");
  const [serviceExpectation, setServiceExpectation] = useState("");
  const [freeText, setFreeText] = useState("");
  const [searchPref, setSearchPref] = useState("");
  const [localitySearch, setLocalitySearch] = useState("");

  const [status, setStatus] = useState("");
  const [statusError, setStatusError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<RecommendationResponse | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const d = await apiGet<{ localities: string[] }>("/ui-api/localities");
        if (cancelled) return;
        setLocalities(d.localities || []);
      } catch {
        if (!cancelled) {
          setStatusError(true);
          setStatus("Could not load localities.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const d = await apiGet<{ cuisines: string[] }>("/ui-api/cuisines");
        if (cancelled) return;
        const list = d.cuisines || [];
        setCuisines(list);
        const next: Record<string, boolean> = {};
        let picked = false;
        for (const c of list) {
          if (c === "North Indian") {
            next[c] = true;
            picked = true;
          } else {
            next[c] = false;
          }
        }
        if (!picked && list.length) next[list[0]] = true;
        setCuisineSelection(next);
      } catch {
        if (!cancelled) {
          setStatusError(true);
          setStatus("Could not load cuisines.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedCuisineList = useCallback(
    () => Object.entries(cuisineSelection).filter(([, v]) => v).map(([k]) => k),
    [cuisineSelection]
  );

  const cuisineFilter = searchPref.trim().toLowerCase();
  const visibleCuisines = useMemo(
    () => cuisines.filter((c) => !cuisineFilter || c.toLowerCase().includes(cuisineFilter)),
    [cuisines, cuisineFilter]
  );

  const displayCuisines = useMemo(() => {
    const cap = 220;
    let list =
      visibleCuisines.length <= cap || cuisineFilter ? visibleCuisines : visibleCuisines.slice(0, cap);
    const selected = Object.entries(cuisineSelection)
      .filter(([, v]) => v)
      .map(([k]) => k);
    for (const k of selected) {
      if (visibleCuisines.includes(k) && !list.includes(k)) {
        list = [...list, k];
      }
    }
    return list;
  }, [visibleCuisines, cuisineFilter, cuisineSelection]);

  const filteredLocalities = useMemo(() => {
    const q = localitySearch.trim().toLowerCase();
    let list = q ? localities.filter((n) => n.toLowerCase().includes(q)) : localities.slice(0, 250);
    if (location && !list.includes(location)) {
      list = [location, ...list];
    }
    return list;
  }, [localities, localitySearch, location]);

  const toggleCuisine = (name: string) => {
    setCuisineSelection((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const appendHistory = (entry: HistoryEntry) => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_HISTORY);
      const history: HistoryEntry[] = raw ? JSON.parse(raw) : [];
      history.unshift(entry);
      localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(history.slice(0, 40)));
    } catch {
      /* ignore */
    }
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("");
    setStatusError(false);
    const loc = location.trim();
    if (!loc) {
      setStatusError(true);
      setStatus("Please select a locality.");
      return;
    }
    const cList = selectedCuisineList();
    if (!cList.length) {
      setStatusError(true);
      setStatus("Please select at least one cuisine.");
      return;
    }
    if (Number.isNaN(budgetAmount) || budgetAmount < 50) {
      setStatusError(true);
      setStatus("Please enter a valid budget amount (INR, min 50).");
      return;
    }
    setLoading(true);
    try {
      const payload = {
        location: loc,
        budget_amount: budgetAmount,
        cuisine: cList,
        min_rating: minRating,
        party_type: partyType.trim() || null,
        service_expectation: serviceExpectation.trim() || null,
        free_text_notes: freeText.trim() || null,
        top_k_results: topK,
        top_n_candidates: 30,
        include_debug: true,
      };
      const data = await apiPost<RecommendationResponse>("/ui-api/recommendations", payload);
      setResults(data);
      setRequestId(data.request_id);
      appendHistory({
        created_at: new Date().toISOString(),
        request_id: data.request_id,
        location: loc,
        budget_amount: budgetAmount,
        cuisine: cList,
        result_count: (data.top_recommendations || []).length,
        summary: data.summary,
      });
      setStatus("Recommendations fetched successfully.");
    } catch (err) {
      setStatusError(true);
      setStatus(err instanceof Error ? err.message : "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  const sendFeedback = async (eventType: string, restaurantId: string) => {
    if (!requestId) {
      setStatusError(true);
      setStatus("Request ID missing for feedback.");
      return;
    }
    try {
      await apiPost(`/ui-api/feedback/${eventType}`, {
        request_id: requestId,
        restaurant_id: restaurantId,
        event_value: `next-${eventType}`,
      });
      setStatusError(false);
      setStatus(`Feedback '${eventType}' submitted.`);
    } catch (err) {
      setStatusError(true);
      setStatus(err instanceof Error ? err.message : "Feedback failed.");
    }
  };

  const checkHealth = async () => {
    setStatus("Checking backend health…");
    setStatusError(false);
    try {
      const d = await apiGet<{ circuit_breaker?: { state?: string } }>("/health/detailed");
      setStatus(`Health OK | Circuit: ${d.circuit_breaker?.state ?? "—"}`);
    } catch {
      setStatusError(true);
      setStatus("Health check failed.");
    }
  };

  return (
    <>
      <div className="divider-trio" aria-hidden>
        <span />
        <span />
        <span />
      </div>

      <section className="card">
        <h1>Find restaurants</h1>
        <p className="muted" style={{ marginTop: 0 }}>
          Preferences use your catalog localities and cuisines. Backend must be running (see README).
        </p>
        <label className="label" htmlFor="pref-search">
          Quick filter (optional)
        </label>
        <input
          id="pref-search"
          className="input input-search"
          placeholder="Filter cuisine list…"
          value={searchPref}
          onChange={(e) => setSearchPref(e.target.value)}
          type="search"
        />
      </section>

      <section className="card">
        <h2 className="heading">Request settings</h2>
        <div className="field-group" style={{ maxWidth: 200 }}>
          <label className="label" htmlFor="topK">
            Top K results
          </label>
          <input
            id="topK"
            className="input"
            type="number"
            min={1}
            max={10}
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value, 10) || 5)}
          />
        </div>
      </section>

      <section className="card">
        <h2 className="heading">Your preferences</h2>
        <form onSubmit={onSubmit}>
          <div className="grid-two">
            <div className="field-group">
              <label className="label" htmlFor="locality-filter">
                Find locality
              </label>
              <input
                id="locality-filter"
                className="input input-search"
                placeholder="Type to narrow the list…"
                value={localitySearch}
                onChange={(e) => setLocalitySearch(e.target.value)}
                type="search"
                autoComplete="off"
              />
              <span className="field-hint">
                {localities.length > 250 && !localitySearch.trim()
                  ? `Showing first 250 of ${localities.length} — type to search all.`
                  : `${filteredLocalities.length} match(es)`}
              </span>
              <label className="label" htmlFor="location" style={{ marginTop: 10 }}>
                Locality
              </label>
              <select
                id="location"
                className="select"
                required
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              >
                <option value="">Select locality…</option>
                {filteredLocalities.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field-group">
              <label className="label" htmlFor="budget">
                Max budget (INR, cost for two)
              </label>
              <input
                id="budget"
                className="input"
                type="number"
                min={50}
                max={100000}
                step={50}
                value={budgetAmount}
                onChange={(e) => setBudgetAmount(parseInt(e.target.value, 10) || 0)}
                required
              />
            </div>
            <div className="field-group" style={{ gridColumn: "1 / -1" }}>
              <span className="label">Cuisine (tap to toggle)</span>
              <div
                className="cuisine-toggle-grid"
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                  gap: "8px",
                  maxHeight: "200px",
                  overflowY: "auto",
                  padding: "10px",
                  background: "var(--color-input-bg)",
                  borderRadius: "var(--radius)",
                  border: "1px solid var(--color-border)",
                }}
              >
                {displayCuisines.map((c) => (
                  <label
                    key={c}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      fontSize: "13px",
                      fontWeight: 500,
                      cursor: "pointer",
                      padding: "6px 8px",
                      borderRadius: "var(--radius-sm)",
                      background: cuisineSelection[c] ? "rgba(226, 55, 68, 0.12)" : "transparent",
                      border: cuisineSelection[c] ? "1px solid var(--color-primary)" : "1px solid transparent",
                    }}
                  >
                    <input type="checkbox" checked={!!cuisineSelection[c]} onChange={() => toggleCuisine(c)} />
                    {c}
                  </label>
                ))}
              </div>
              <span className="field-hint">
                Select one or more cuisines.
                {visibleCuisines.length > 220 && !cuisineFilter
                  ? ` Showing first 220 of ${visibleCuisines.length} — use the filter above to narrow.`
                  : null}
              </span>
            </div>
            <div className="field-group">
              <label className="label" htmlFor="rating">
                Minimum rating
              </label>
              <input
                id="rating"
                className="input"
                type="number"
                min={0}
                max={5}
                step={0.1}
                value={minRating}
                onChange={(e) => setMinRating(parseFloat(e.target.value) || 0)}
              />
            </div>
            <div className="field-group">
              <label className="label" htmlFor="party">
                Party type (optional)
              </label>
              <input
                id="party"
                className="input"
                placeholder="family / friends"
                value={partyType}
                onChange={(e) => setPartyType(e.target.value)}
              />
            </div>
            <div className="field-group">
              <label className="label" htmlFor="service">
                Service expectation (optional)
              </label>
              <input
                id="service"
                className="input"
                placeholder="quick service"
                value={serviceExpectation}
                onChange={(e) => setServiceExpectation(e.target.value)}
              />
            </div>
          </div>
          <div className="field-group" style={{ marginTop: 14 }}>
            <label className="label" htmlFor="notes">
              Additional preferences
            </label>
            <textarea
              id="notes"
              className="textarea"
              placeholder="family-friendly, outdoor seating…"
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
            />
          </div>
          <div className="row-actions">
            <Button type="submit" variant="primary" disabled={loading}>
              {loading ? "Loading…" : "Get recommendations"}
            </Button>
            <Button type="button" variant="secondary" onClick={checkHealth}>
              Health check
            </Button>
          </div>
        </form>
        {status && <p className={`status-msg ${statusError ? "error" : ""}`}>{status}</p>}
      </section>

      <section className="card">
        <h2 className="heading">Results</h2>
        {results?.summary && <p className="muted">{results.summary}</p>}
        {!results?.top_recommendations?.length && <p className="muted">No recommendations yet.</p>}
        {results?.top_recommendations?.map((item) => (
          <div key={item.restaurant_id} className="result-item">
            <h3 className="heading" style={{ fontSize: "1.05rem" }}>
              #{item.rank} {item.restaurant_name}
            </h3>
            <p>
              <strong>Rating:</strong> {item.rating} | <strong>Cost:</strong> {item.estimated_cost} {item.currency}
            </p>
            <div className="chips">
              {(item.cuisine || []).map((c) => (
                <span key={c} className="chip">
                  {c}
                </span>
              ))}
            </div>
            <p>
              <strong>Why:</strong> {item.ai_explanation}
            </p>
            {item.cautions && <p className="muted">{item.cautions}</p>}
            <div className="row-actions">
              <Button variant="outlined" className="btn-small" onClick={() => sendFeedback("click", item.restaurant_id)}>
                Click
              </Button>
              <Button variant="primary" className="btn-small" onClick={() => sendFeedback("like", item.restaurant_id)}>
                Like
              </Button>
              <Button variant="secondary" className="btn-small" onClick={() => sendFeedback("not_relevant", item.restaurant_id)}>
                Not relevant
              </Button>
            </div>
          </div>
        ))}
      </section>
    </>
  );
}
