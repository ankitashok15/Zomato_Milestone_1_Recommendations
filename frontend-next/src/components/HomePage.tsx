"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import type { HistoryEntry, RecommendationResponse, TopRestaurantsResponse } from "@/lib/types";
import { STORAGE_KEY_HISTORY } from "@/lib/types";
import { isStreamlitBackendMode, STREAMLIT_APP_URL } from "@/lib/runtimeConfig";
import { Button } from "./Button";

const FALLBACK_LOCALITIES = [
  "Bangalore",
  "Indiranagar",
  "Koramangala",
  "HSR Layout",
  "Whitefield",
  "Marathahalli",
  "BTM Layout",
];

const FALLBACK_CUISINES = [
  "North Indian",
  "Chinese",
  "South Indian",
  "Biryani",
  "Fast Food",
  "Italian",
  "Desserts",
];

export function HomePage() {
  const [localities, setLocalities] = useState<string[]>([]);
  const [cuisines, setCuisines] = useState<string[]>([]);
  const [location, setLocation] = useState("");
  const [budgetAmount, setBudgetAmount] = useState(1200);
  const [selectedCuisine, setSelectedCuisine] = useState("");
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
  const [exploringTop, setExploringTop] = useState(false);
  const [apiDegraded, setApiDegraded] = useState(false);
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
          setApiDegraded(true);
          setLocalities(FALLBACK_LOCALITIES);
          setStatusError(false);
          setStatus("Using fallback localities. Live locality API is currently unavailable.");
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
        const defaultCuisine = list.includes("North Indian") ? "North Indian" : list[0] || "";
        setSelectedCuisine(defaultCuisine);
      } catch {
        if (!cancelled) {
          setApiDegraded(true);
          setCuisines(FALLBACK_CUISINES);
          setSelectedCuisine("North Indian");
          setStatusError(false);
          setStatus("Using fallback cuisines. Live cuisine API is currently unavailable.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const cuisineFilter = searchPref.trim().toLowerCase();
  const visibleCuisines = useMemo(() => {
    const list = cuisines.filter((c) => !cuisineFilter || c.toLowerCase().includes(cuisineFilter));
    if (selectedCuisine && !list.includes(selectedCuisine)) {
      return [selectedCuisine, ...list];
    }
    return list;
  }, [cuisines, cuisineFilter, selectedCuisine]);

  const filteredLocalities = useMemo(() => {
    const q = localitySearch.trim().toLowerCase();
    let list = q ? localities.filter((n) => n.toLowerCase().includes(q)) : localities.slice(0, 250);
    if (location && !list.includes(location)) {
      list = [location, ...list];
    }
    return list;
  }, [localities, localitySearch, location]);

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
    if (!selectedCuisine) {
      setStatusError(true);
      setStatus("Please select a cuisine (e.g., North Indian).");
      return;
    }
    if (Number.isNaN(budgetAmount) || budgetAmount < 50) {
      setStatusError(true);
      setStatus("Please enter a valid budget amount (INR, min 50).");
      return;
    }
    if (isStreamlitBackendMode()) {
      setStatusError(false);
      setStatus("This deployment uses Streamlit mode. Open the Streamlit app for live recommendations.");
      if (STREAMLIT_APP_URL) window.open(STREAMLIT_APP_URL, "_blank", "noopener,noreferrer");
      return;
    }
    setLoading(true);
    try {
      const payload = {
        location: loc,
        budget_amount: budgetAmount,
        cuisine: [selectedCuisine],
        min_rating: minRating,
        party_type: partyType.trim() || null,
        service_expectation: serviceExpectation.trim() || null,
        free_text_notes: freeText.trim() || null,
        top_k_results: topK,
        top_n_candidates: 20,
        include_debug: false,
      };
      const data = await apiPost<RecommendationResponse>("/ui-api/recommendations", payload);
      setResults(data);
      setRequestId(data.request_id);
      appendHistory({
        created_at: new Date().toISOString(),
        request_id: data.request_id,
        location: loc,
        budget_amount: budgetAmount,
        cuisine: [selectedCuisine],
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

  const exploreTopRated = async () => {
    setStatus("");
    setStatusError(false);
    const loc = location.trim();
    if (!loc) {
      setStatusError(true);
      setStatus("Please select a locality to explore top restaurants.");
      return;
    }
    if (isStreamlitBackendMode()) {
      setStatusError(false);
      setStatus("Top-rated API is unavailable in Streamlit mode. Open the Streamlit app to explore.");
      if (STREAMLIT_APP_URL) window.open(STREAMLIT_APP_URL, "_blank", "noopener,noreferrer");
      return;
    }
    setExploringTop(true);
    try {
      const data = await apiGet<TopRestaurantsResponse>(
        `/ui-api/top-restaurants?locality=${encodeURIComponent(loc)}&limit=5`
      );
      const topItems = data.top_restaurants || [];
      setRequestId(null);
      setResults({
        request_id: `top-rated-${Date.now()}`,
        summary: topItems.length
          ? `Top rated picks in ${loc} based on ratings and vote volume.`
          : `No top-rated restaurants found for ${loc}.`,
        top_recommendations: topItems.map((item, index) => ({
          rank: index + 1,
          restaurant_id: item.restaurant_id,
          restaurant_name: item.restaurant_name,
          cuisine: item.cuisine || [],
          rating: item.rating,
          estimated_cost: item.estimated_cost,
          currency: item.currency || "INR",
          ai_explanation: `${item.restaurant_name} is highly rated (${item.rating}) with strong local trust (${item.votes} votes).`,
          cautions: "Exploration mode: ranked only by rating and votes in the selected locality.",
        })),
      });
      setStatus("Top rated restaurants loaded.");
    } catch (err) {
      setStatusError(true);
      setStatus(err instanceof Error ? err.message : "Could not load top restaurants.");
    } finally {
      setExploringTop(false);
    }
  };

  const sendFeedback = async (eventType: string, restaurantId: string) => {
    if (isStreamlitBackendMode()) {
      setStatusError(false);
      setStatus("Feedback endpoint is unavailable in Streamlit mode.");
      return;
    }
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
    if (isStreamlitBackendMode()) {
      setStatusError(false);
      setStatus("Health check is unavailable in Streamlit mode. Use the Streamlit app URL.");
      return;
    }
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
        {apiDegraded ? (
          <p className="field-hint">
            Live API is not reachable. Fallback dropdown values are shown so the UI remains usable.
          </p>
        ) : null}
        {isStreamlitBackendMode() && STREAMLIT_APP_URL ? (
          <div className="row-actions" style={{ marginTop: 10 }}>
            <Button type="button" variant="outlined" onClick={() => window.open(STREAMLIT_APP_URL, "_blank", "noopener,noreferrer")}>
              Open Streamlit app
            </Button>
          </div>
        ) : null}
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
              <label className="label" htmlFor="cuisine-dropdown">
                Cuisine dropdown
              </label>
              <select
                id="cuisine-dropdown"
                className="select"
                value={selectedCuisine}
                onChange={(e) => setSelectedCuisine(e.target.value)}
                required
              >
                <option value="">Select cuisine (e.g., North Indian)</option>
                {visibleCuisines.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <span className="field-hint">
                Example: try "North Indian" or "Chinese", then click Get recommendations.
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
            <Button type="button" variant="outlined" onClick={exploreTopRated} disabled={exploringTop || loading}>
              {exploringTop ? "Loading top rated…" : "Explore Top Rated in Locality"}
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
            {requestId ? (
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
            ) : null}
          </div>
        ))}
      </section>
    </>
  );
}
