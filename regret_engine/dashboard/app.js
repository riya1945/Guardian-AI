const state = {
  decisions: [],
  analytics: null,
  health: null,
  selectedId: null,
  risk: "",
};

const currency = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 0,
});

const pct = new Intl.NumberFormat("en-IN", {
  style: "percent",
  maximumFractionDigits: 0,
});

const els = {
  connectionStatus: document.getElementById("connectionStatus"),
  lastUpdated: document.getElementById("lastUpdated"),
  metricTotal: document.getElementById("metricTotal"),
  metricRegret: document.getElementById("metricRegret"),
  metricConfidence: document.getElementById("metricConfidence"),
  metricHighRisk: document.getElementById("metricHighRisk"),
  metricEvidence: document.getElementById("metricEvidence"),
  decisionRows: document.getElementById("decisionRows"),
  detailTitle: document.getElementById("detailTitle"),
  detailRisk: document.getElementById("detailRisk"),
  detailBody: document.getElementById("detailBody"),
};

async function loadData() {
  try {
    const query = state.risk ? `?risk_level=${state.risk}` : "";
    const feedRes = await fetch(`/dashboard/feed${query}`);

    if (!feedRes.ok) {
      throw new Error("API request failed");
    }

    const feed = await feedRes.json();
    state.health = feed.health;
    state.analytics = feed.analytics;
    state.decisions = feed.decisions;
    if (!state.selectedId && state.decisions.length) {
      state.selectedId = state.decisions[0].decision_id;
    }

    setOnline(true);
    render();
  } catch (error) {
    setOnline(false);
    els.decisionRows.innerHTML = `<tr><td colspan="7" class="empty">Unable to load dashboard data</td></tr>`;
  }
}

function setOnline(isOnline) {
  els.connectionStatus.textContent = isOnline ? "Online" : "Offline";
  els.connectionStatus.className = `status-dot ${isOnline ? "online" : "offline"}`;
  const backend = state.health
    ? `${state.health.storage_backend} / ${state.health.vector_backend} / ${state.health.llm_provider}`
    : "Backend connected";
  els.lastUpdated.textContent = isOnline
    ? `${backend} | ${new Date().toLocaleTimeString()}`
    : "Backend unavailable";
}

function render() {
  renderMetrics();
  renderCharts();
  renderRows();
  renderDetail();
}

function renderMetrics() {
  const analytics = state.analytics;
  if (!analytics) return;
  els.metricTotal.textContent = analytics.total_decisions;
  els.metricRegret.textContent = `${currency.format(analytics.average_regret)} INR`;
  els.metricConfidence.textContent = pct.format(analytics.average_confidence);
  els.metricHighRisk.textContent = analytics.high_risk_decisions;
  els.metricEvidence.textContent = analytics.retrieved_evidence_sources;
}

function renderRows() {
  if (!state.decisions.length) {
    els.decisionRows.innerHTML = `<tr><td colspan="7" class="empty">No decisions match filter</td></tr>`;
    return;
  }

  els.decisionRows.innerHTML = state.decisions
    .map((record) => {
      const selected = record.decision_id === state.selectedId ? "selected" : "";
      return `
        <tr class="${selected}" data-id="${escapeHtml(record.decision_id)}">
          <td>${escapeHtml(record.decision_id)}</td>
          <td>${escapeHtml(record.sku)}</td>
          <td>${record.price.toFixed(2)} INR</td>
          <td>${record.regret.best_price.toFixed(2)} INR</td>
          <td>${currency.format(record.regret_score)} INR</td>
          <td><span class="${riskClass(record.risk_level)}">${record.risk_level}</span></td>
          <td>${pct.format(record.confidence)}</td>
        </tr>
      `;
    })
    .join("");

  els.decisionRows.querySelectorAll("tr[data-id]").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedId = row.dataset.id;
      renderRows();
      renderDetail();
    });
  });
}

function renderDetail() {
  const record = state.decisions.find((item) => item.decision_id === state.selectedId);
  if (!record) {
    els.detailTitle.textContent = "No decision selected";
    els.detailRisk.textContent = "None";
    els.detailRisk.className = "risk-pill";
    els.detailBody.innerHTML = `<p class="empty">Select a row to inspect decision, evidence, counterfactual, and uncertainty.</p>`;
    return;
  }

  const explanation = record.explanation;
  els.detailTitle.textContent = record.decision_id;
  els.detailRisk.textContent = record.risk_level;
  els.detailRisk.className = riskClass(record.risk_level);

  els.detailBody.innerHTML = `
    <section class="detail-block">
      <h3>Decision</h3>
      <p>${escapeHtml(record.recommendation)}</p>
    </section>
    <section class="detail-block">
      <h3>Why</h3>
      <p>${escapeHtml(explanation?.explanation || "No explanation available")}</p>
    </section>
    <section class="detail-block">
      <h3>Key Factors</h3>
      ${record.factors.map(renderFactor).join("")}
    </section>
    <section class="detail-block">
      <h3>Counterfactual</h3>
      <p>${escapeHtml(explanation?.counterfactual || "No counterfactual available")}</p>
    </section>
    <section class="detail-block">
      <h3>Evidence</h3>
      ${(explanation?.supporting_evidence || []).map(renderEvidence).join("") || `<p class="empty">No grounded evidence returned</p>`}
    </section>
    <section class="detail-block">
      <h3>Uncertainty</h3>
      <ul class="detail-list">
        ${(explanation?.uncertainties || record.uncertainties)
          .map((item) => `<li>${escapeHtml(item)}</li>`)
          .join("")}
      </ul>
    </section>
  `;
}

function renderFactor(factor) {
  const width = Math.max(6, Math.round(factor.magnitude * 100));
  return `
    <div class="factor-row">
      <span>${escapeHtml(factor.factor)}</span>
      <div class="bar"><span style="width:${width}%"></span></div>
      <span>${factor.impact}</span>
    </div>
  `;
}

function renderEvidence(item) {
  return `
    <article class="evidence">
      <strong>${escapeHtml(item.title)}</strong>
      <small>${escapeHtml(item.source)} | relevance ${item.relevance_score.toFixed(3)}</small>
      <p>${escapeHtml(item.content.slice(0, 360))}</p>
    </article>
  `;
}

function renderCharts() {
  if (!state.analytics) return;
  drawLineChart("regretLine", state.analytics.regret_over_time);
  drawRiskBars("riskBars", state.analytics.risk_breakdown);
  drawScatter("confidenceScatter", state.analytics.regret_over_time);
}

function drawLineChart(canvasId, points) {
  const ctx = getCanvas(canvasId);
  if (!ctx) return;
  const { canvas } = ctx;
  clear(ctx);
  drawAxes(ctx);

  if (!points.length) return;
  const values = points.map((point) => point.regret);
  const max = Math.max(...values, 1);
  const pad = 30;
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = pad + (index / Math.max(points.length - 1, 1)) * (canvas.width - pad * 2);
    const y = canvas.height - pad - (point.regret / max) * (canvas.height - pad * 2);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function drawRiskBars(canvasId, breakdown) {
  const ctx = getCanvas(canvasId);
  if (!ctx) return;
  clear(ctx);
  const entries = ["LOW", "MEDIUM", "HIGH"].map((risk) => [risk, breakdown[risk] || 0]);
  const max = Math.max(...entries.map(([, count]) => count), 1);
  const colors = { LOW: "#16803c", MEDIUM: "#b7791f", HIGH: "#c24141" };
  entries.forEach(([risk, count], index) => {
    const x = 44 + index * 112;
    const height = (count / max) * 150;
    ctx.fillStyle = colors[risk];
    ctx.fillRect(x, 178 - height, 58, height);
    ctx.fillStyle = "#667085";
    ctx.font = "12px system-ui";
    ctx.fillText(risk, x + 3, 202);
    ctx.fillText(String(count), x + 22, 170 - height);
  });
}

function drawScatter(canvasId, points) {
  const ctx = getCanvas(canvasId);
  if (!ctx) return;
  const { canvas } = ctx;
  clear(ctx);
  drawAxes(ctx);
  const regrets = points.map((point) => point.regret);
  const maxRegret = Math.max(...regrets, 1);
  const pad = 30;
  ctx.fillStyle = "#2563eb";
  points.forEach((point) => {
    const x = pad + point.confidence * (canvas.width - pad * 2);
    const y = canvas.height - pad - (point.regret / maxRegret) * (canvas.height - pad * 2);
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  });
}

function drawAxes(ctx) {
  const { canvas } = ctx;
  ctx.strokeStyle = "#d9dee8";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(30, 12);
  ctx.lineTo(30, canvas.height - 30);
  ctx.lineTo(canvas.width - 12, canvas.height - 30);
  ctx.stroke();
}

function getCanvas(id) {
  const canvas = document.getElementById(id);
  return canvas ? canvas.getContext("2d") : null;
}

function clear(ctx) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}

function riskClass(risk) {
  return `risk-pill risk-${String(risk).toLowerCase()}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.querySelectorAll(".filter").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".filter").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.risk = button.dataset.risk || "";
    state.selectedId = null;
    loadData();
  });
});

loadData();
setInterval(loadData, 2000);
