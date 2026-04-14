const form = document.getElementById("recommendationForm");
const resultsEl = document.getElementById("results");
const summaryEl = document.getElementById("summary");
const statusEl = document.getElementById("status");
const healthBtn = document.getElementById("healthBtn");
const topRatedBtn = document.getElementById("topRatedBtn");
const locationSelect = document.getElementById("location");
const cuisineSelect = document.getElementById("cuisineDropdown");

const STORAGE_KEY_HISTORY = "zomato_request_history";
const REQUEST_MS = 15000;

let latestRequestId = null;

function timeoutSignal() {
  if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
    return AbortSignal.timeout(REQUEST_MS);
  }
  return undefined;
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.color = isError ? "#b91c1c" : "#4b5563";
}

async function loadLocalities() {
  try {
    const response = await fetch("/ui-api/localities", {
      cache: "no-store",
      signal: timeoutSignal()
    });
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json();
    const list = data.localities || [];
    locationSelect.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.disabled = true;
    placeholder.selected = true;
    placeholder.textContent = "Select locality…";
    locationSelect.appendChild(placeholder);
    for (const name of list) {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      locationSelect.appendChild(opt);
    }
  } catch (err) {
    locationSelect.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Failed to load localities";
    locationSelect.appendChild(opt);
    setStatus(err.message || "Could not load localities.", true);
  }
}

async function loadCuisines() {
  try {
    const response = await fetch("/ui-api/cuisines", {
      cache: "no-store",
      signal: timeoutSignal()
    });
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json();
    const list = data.cuisines || [];
    cuisineSelect.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select cuisine (e.g., North Indian)";
    placeholder.disabled = true;
    placeholder.selected = true;
    cuisineSelect.appendChild(placeholder);
    for (const name of list) {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      cuisineSelect.appendChild(opt);
    }
    const preferred = list.includes("North Indian") ? "North Indian" : list[0];
    if (preferred) cuisineSelect.value = preferred;
  } catch (err) {
    cuisineSelect.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Failed to load cuisines";
    cuisineSelect.appendChild(opt);
    setStatus(err.message || "Could not load cuisines.", true);
  }
}

function appendHistory(entry) {
  const raw = localStorage.getItem(STORAGE_KEY_HISTORY);
  const history = raw ? JSON.parse(raw) : [];
  history.unshift(entry);
  localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(history.slice(0, 40)));
}

async function sendFeedback(eventType, restaurantId) {
  try {
    if (!latestRequestId) throw new Error("Request ID missing for feedback.");
    const response = await fetch(`/ui-api/feedback/${eventType}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      cache: "no-store",
      signal: timeoutSignal(),
      body: JSON.stringify({
        request_id: latestRequestId,
        restaurant_id: restaurantId,
        event_value: `ui-${eventType}`
      })
    });
    if (!response.ok) throw new Error(await response.text());
    setStatus(`Feedback '${eventType}' submitted.`);
  } catch (err) {
    setStatus(err.message || "Feedback failed.", true);
  }
}

function renderResults(data) {
  resultsEl.innerHTML = "";
  summaryEl.textContent = data.summary || "";
  latestRequestId = data.request_id || null;

  const items = data.top_recommendations || [];
  if (!items.length) {
    resultsEl.innerHTML = `<p class="muted">No recommendations found.</p>`;
    return;
  }

  for (const item of items) {
    const box = document.createElement("div");
    box.className = "result-item";
    const feedbackRow = latestRequestId
      ? `<div class="row">
        <button type="button" class="outlined" data-action="click">Click</button>
        <button type="button" data-action="like">Like</button>
        <button type="button" class="secondary" data-action="not_relevant">Not relevant</button>
      </div>`
      : "";
    box.innerHTML = `
      <h3>#${item.rank} ${item.restaurant_name}</h3>
      <p><strong>Rating:</strong> ${item.rating} | <strong>Cost:</strong> ${item.estimated_cost} ${item.currency}</p>
      <div class="chips">${(item.cuisine || []).map((c) => `<span class="chip">${c}</span>`).join("")}</div>
      <p><strong>Why:</strong> ${item.ai_explanation}</p>
      <p class="muted">${item.cautions || ""}</p>
      ${feedbackRow}
    `;
    box.querySelectorAll("button[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => sendFeedback(btn.dataset.action, item.restaurant_id));
    });
    resultsEl.appendChild(box);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Fetching recommendations...");
  try {
    const loc = locationSelect.value.trim();
    if (!loc) {
      setStatus("Please select a locality.", true);
      return;
    }
    const selectedCuisine = cuisineSelect.value.trim();
    if (!selectedCuisine) {
      setStatus("Please select a cuisine (e.g., North Indian).", true);
      return;
    }
    const budgetAmount = parseInt(document.getElementById("budgetAmount").value, 10);
    if (Number.isNaN(budgetAmount) || budgetAmount < 50) {
      setStatus("Please enter a valid budget amount (INR, min 50).", true);
      return;
    }
    const payload = {
      location: loc,
      budget_amount: budgetAmount,
      cuisine: [selectedCuisine],
      min_rating: parseFloat(document.getElementById("minRating").value || "0"),
      party_type: document.getElementById("partyType").value.trim() || null,
      service_expectation: document.getElementById("serviceExpectation").value.trim() || null,
      free_text_notes: document.getElementById("freeText").value.trim() || null,
      top_k_results: parseInt(document.getElementById("topK").value || "5", 10),
      top_n_candidates: 20,
      include_debug: false
    };
    const response = await fetch("/ui-api/recommendations", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      cache: "no-store",
      signal: timeoutSignal(),
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json();
    renderResults(data);
    appendHistory({
      created_at: new Date().toISOString(),
      request_id: data.request_id,
      location: payload.location,
      budget_amount: payload.budget_amount,
      cuisine: payload.cuisine,
      result_count: (data.top_recommendations || []).length,
      summary: data.summary
    });
    setStatus("Recommendations fetched successfully.");
  } catch (err) {
    setStatus(err.message || "Request failed.", true);
  }
});

healthBtn.addEventListener("click", async () => {
  setStatus("Checking backend health...");
  try {
    const response = await fetch("/health/detailed", {
      cache: "no-store",
      signal: timeoutSignal()
    });
    if (!response.ok) throw new Error("Health check failed.");
    const data = await response.json();
    setStatus(`Health OK | Circuit: ${data.circuit_breaker.state}`);
  } catch (err) {
    setStatus(err.message || "Health check failed.", true);
  }
});

Promise.all([loadLocalities(), loadCuisines()]);

topRatedBtn.addEventListener("click", async () => {
  setStatus("Loading top rated restaurants...");
  try {
    const loc = locationSelect.value.trim();
    if (!loc) {
      setStatus("Please select a locality first.", true);
      return;
    }
    const response = await fetch(`/ui-api/top-restaurants?locality=${encodeURIComponent(loc)}&limit=5`, {
      cache: "no-store",
      signal: timeoutSignal()
    });
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json();
    const items = data.top_restaurants || [];
    latestRequestId = null;
    renderResults({
      request_id: `top-rated-${Date.now()}`,
      summary: items.length
        ? `Top rated picks in ${loc} based on ratings and vote volume.`
        : `No top-rated restaurants found for ${loc}.`,
      top_recommendations: items.map((item, idx) => ({
        rank: idx + 1,
        restaurant_id: item.restaurant_id,
        restaurant_name: item.restaurant_name,
        cuisine: item.cuisine || [],
        rating: item.rating,
        estimated_cost: item.estimated_cost,
        currency: item.currency || "INR",
        ai_explanation: `${item.restaurant_name} is highly rated (${item.rating}) with strong local trust (${item.votes} votes).`,
        cautions: "Exploration mode: ranked only by rating and votes in the selected locality."
      }))
    });
    setStatus("Top rated restaurants loaded.");
  } catch (err) {
    setStatus(err.message || "Could not load top rated restaurants.", true);
  }
});

