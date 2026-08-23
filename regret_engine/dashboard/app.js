const state = {
  decisions: [],
  analytics: null,
  health: null,
  selectedId: null,
  risk: "",
};

const currency = new Intl.NumberFormat("en-IN", {
  currency: "INR",
  maximumFractionDigits: 0,
  style: "currency",
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
    localStorage.setItem("ragex:last-feed", JSON.stringify(feed));
    if (!state.selectedId && state.decisions.length) {
      state.selectedId = state.decisions[0].decision_id;
    }

    setOnline(true);
    render();
  } catch (error) {
    const cached = loadCachedFeed();
    if (cached) {
      state.health = cached.health;
      state.analytics = cached.analytics;
      state.decisions = cached.decisions;
      if (!state.selectedId && state.decisions.length) {
        state.selectedId = state.decisions[0].decision_id;
      }
      setOnline(false, true);
      render();
      return;
    }
    setOnline(false, false);
    els.decisionRows.innerHTML = `<tr><td colspan="7" class="empty">Waiting for dashboard feed</td></tr>`;
  }
}

function loadCachedFeed() {
  try {
    const cached = JSON.parse(localStorage.getItem("ragex:last-feed") || "null");
    if (cached?.health && cached?.analytics && Array.isArray(cached?.decisions)) {
      return cached;
    }
  } catch (error) {
    localStorage.removeItem("ragex:last-feed");
  }
  return null;
}

function setOnline(isOnline, usingCache = false) {
  els.connectionStatus.textContent = isOnline ? "API live" : usingCache ? "Cached" : "API pending";
  els.connectionStatus.className = `status-dot ${isOnline ? "online" : "offline"}`;
  const backend = state.health
    ? `${state.health.storage_backend} / ${state.health.vector_backend} / ${state.health.llm_provider}`
    : "Backend connected";
  els.lastUpdated.textContent = isOnline
    ? `${backend} | ${new Date().toLocaleTimeString()}`
    : usingCache
      ? `${backend} | last snapshot`
      : "Waiting for backend";
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
  setMetricValue(els.metricTotal, analytics.total_decisions);
  setMetricValue(els.metricRegret, currency.format(analytics.average_regret));
  setMetricValue(els.metricConfidence, pct.format(analytics.average_confidence));
  setMetricValue(els.metricHighRisk, analytics.high_risk_decisions);
  setMetricValue(els.metricEvidence, analytics.retrieved_evidence_sources);
  fitMetricValues();
}

function setMetricValue(element, value) {
  element.textContent = value;
  element.title = String(value);
  element.style.removeProperty("font-size");
}

function fitMetricValues() {
  requestAnimationFrame(() => {
    [
      els.metricTotal,
      els.metricRegret,
      els.metricConfidence,
      els.metricHighRisk,
      els.metricEvidence,
    ].forEach(fitMetricValue);
  });
}

function fitMetricValue(element) {
  const minSize = parseFloat(cssVar("--metric-value-min")) || 18;
  let size = parseFloat(getComputedStyle(element).fontSize);

  element.style.removeProperty("font-size");
  size = parseFloat(getComputedStyle(element).fontSize);

  while (size > minSize && element.scrollWidth > element.clientWidth) {
    size -= 1;
    element.style.fontSize = `${size}px`;
  }
}

function renderRows() {
  if (!state.decisions.length) {
    els.decisionRows.innerHTML = `<tr><td colspan="7" class="empty">No decisions match filter</td></tr>`;
    return;
  }

  els.decisionRows.innerHTML = state.decisions
    .map((record) => {
      const selected = record.decision_id === state.selectedId ? "selected" : "";
      const isSelected = record.decision_id === state.selectedId;
      return `
        <tr class="${selected}" data-id="${escapeHtml(record.decision_id)}" tabindex="0" aria-selected="${isSelected}">
          <td>${escapeHtml(record.decision_id)}</td>
          <td>${escapeHtml(record.sku)}</td>
          <td>${formatMoney(record.price)}</td>
          <td>${formatMoney(record.regret.best_price)}</td>
          <td>${formatMoney(record.regret_score)}</td>
          <td><span class="${riskClass(record.risk_level)}">${record.risk_level}</span></td>
          <td>${pct.format(record.confidence)}</td>
        </tr>
      `;
    })
    .join("");

  els.decisionRows.querySelectorAll("tr[data-id]").forEach((row) => {
    const select = () => {
      state.selectedId = row.dataset.id;
      renderRows();
      renderDetail();
    };
    row.addEventListener("click", select);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
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
        ${(explanation?.uncertainties || record.uncertainties || [])
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
      <span title="${escapeHtml(factor.factor)}">${escapeHtml(factor.factor)}</span>
      <div class="bar"><span style="width:${width}%"></span></div>
      <span title="${escapeHtml(factor.impact)}">${factor.impact}</span>
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
  const { width, height } = canvasDimensions(ctx);
  clear(ctx);
  drawAxes(ctx);

  if (!points.length) return;
  const values = points.map((point) => point.regret);
  const max = Math.max(...values, 1);
  const pad = 30;
  ctx.strokeStyle = cssVar("--cyan");
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = pad + (index / Math.max(points.length - 1, 1)) * (width - pad * 2);
    const y = height - pad - (point.regret / max) * (height - pad * 2);
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
  const colors = { LOW: cssVar("--green"), MEDIUM: cssVar("--amber"), HIGH: cssVar("--red") };
  const { width, height } = canvasDimensions(ctx);
  const pad = 30;
  const available = width - pad * 2;
  const slot = available / entries.length;
  const barWidth = Math.max(28, Math.min(58, slot * 0.45));
  const baseY = height - 30;
  ctx.textAlign = "center";
  entries.forEach(([risk, count], index) => {
    const centerX = pad + slot * index + slot / 2;
    const barHeight = (count / max) * (height - 80);
    const x = centerX - barWidth / 2;
    ctx.fillStyle = colors[risk];
    ctx.fillRect(x, baseY - barHeight, barWidth, barHeight);
    ctx.fillStyle = cssVar("--text-dim");
    ctx.font = "12px Inter, Arial, sans-serif";
    ctx.fillText(risk, centerX, baseY + 24);
    ctx.fillText(String(count), centerX, baseY - barHeight - 8);
  });
  ctx.textAlign = "start";
}

function drawScatter(canvasId, points) {
  const ctx = getCanvas(canvasId);
  if (!ctx) return;
  const { width, height } = canvasDimensions(ctx);
  clear(ctx);
  drawAxes(ctx);
  const regrets = points.map((point) => point.regret);
  const maxRegret = Math.max(...regrets, 1);
  const pad = 30;
  ctx.fillStyle = cssVar("--violet");
  points.forEach((point) => {
    const x = pad + point.confidence * (width - pad * 2);
    const y = height - pad - (point.regret / maxRegret) * (height - pad * 2);
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  });
}

function drawAxes(ctx) {
  const { width, height } = canvasDimensions(ctx);
  ctx.strokeStyle = cssVar("--connector");
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(30, 12);
  ctx.lineTo(30, height - 30);
  ctx.lineTo(width - 12, height - 30);
  ctx.stroke();
}

function getCanvas(id) {
  const canvas = document.getElementById(id);
  if (!canvas) return null;
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(1, Math.round(rect.width * dpr));
  const height = Math.max(1, Math.round(rect.height * dpr));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return ctx;
}

function canvasDimensions(ctx) {
  const rect = ctx.canvas.getBoundingClientRect();
  return { width: rect.width, height: rect.height };
}

function clear(ctx) {
  const { width, height } = canvasDimensions(ctx);
  ctx.clearRect(0, 0, width, height);
}

function riskClass(risk) {
  return `risk-pill risk-${String(risk).toLowerCase()}`;
}

function formatMoney(value) {
  return currency.format(value || 0);
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
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
  button.setAttribute("aria-pressed", String(button.classList.contains("active")));
  button.addEventListener("click", () => {
    document.querySelectorAll(".filter").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    document
      .querySelectorAll(".filter")
      .forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
    state.risk = button.dataset.risk || "";
    state.selectedId = null;
    loadData();
  });
});

window.addEventListener("resize", () => {
  fitMetricValues();
  renderCharts();
});

loadData();
setInterval(loadData, 2000);
