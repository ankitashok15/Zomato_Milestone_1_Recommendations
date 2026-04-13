const refreshBtn = document.getElementById("refreshBtn");
const healthJsonEl = document.getElementById("healthJson");
const metricsJsonEl = document.getElementById("metricsJson");
const statusEl = document.getElementById("metricsStatus");

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.color = isError ? "#b91c1c" : "#4b5563";
}

function formatJson(data) {
  return JSON.stringify(data, null, 2);
}

async function loadMetrics() {
  setStatus("Loading metrics...");
  try {
    const healthResp = await fetch("/health/detailed");
    if (!healthResp.ok) throw new Error("Failed to fetch /health/detailed");
    const healthData = await healthResp.json();
    healthJsonEl.textContent = formatJson(healthData);

    const metricsResp = await fetch("/ui-api/metrics");
    if (!metricsResp.ok) throw new Error(await metricsResp.text());
    const metricsData = await metricsResp.json();
    metricsJsonEl.textContent = formatJson(metricsData);
    setStatus("Metrics loaded successfully.");
  } catch (err) {
    setStatus(err.message || "Failed to load metrics.", true);
  }
}

refreshBtn.addEventListener("click", loadMetrics);
loadMetrics();
