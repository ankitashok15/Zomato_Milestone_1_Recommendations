const historyListEl = document.getElementById("historyList");
const clearBtn = document.getElementById("clearHistoryBtn");
const STORAGE_KEY_HISTORY = "zomato_request_history";

function loadHistory() {
  const raw = localStorage.getItem(STORAGE_KEY_HISTORY);
  const history = raw ? JSON.parse(raw) : [];
  historyListEl.innerHTML = "";
  if (!history.length) {
    historyListEl.innerHTML = `<p class="muted">No history found yet. Run recommendations from Home page first.</p>`;
    return;
  }
  history.forEach((entry) => {
    const div = document.createElement("div");
    div.className = "history-item";
    div.innerHTML = `
      <h3>${entry.location} | ${entry.budget_amount != null ? `up to ₹${entry.budget_amount} (two)` : entry.budget ? `${entry.budget} budget` : "—"}</h3>
      <p><strong>Request ID:</strong> ${entry.request_id}</p>
      <p><strong>Cuisine:</strong> ${(entry.cuisine || []).join(", ")}</p>
      <p><strong>Results:</strong> ${entry.result_count}</p>
      <p class="muted">${entry.summary || ""}</p>
      <p class="muted">${new Date(entry.created_at).toLocaleString()}</p>
    `;
    historyListEl.appendChild(div);
  });
}

clearBtn.addEventListener("click", () => {
  localStorage.removeItem(STORAGE_KEY_HISTORY);
  loadHistory();
});

loadHistory();
