const form = document.getElementById("campaign-form");
const timelineEl = document.getElementById("timeline");
const metricsGrid = document.getElementById("metrics-grid");
const playbookEl = document.getElementById("playbook");
const leadGrid = document.getElementById("lead-grid");
const resultGrid = document.getElementById("result-grid");
const historyList = document.getElementById("history-list");
const healthStatus = document.getElementById("health-status");
const leadCount = document.getElementById("lead-count");
const runCount = document.getElementById("run-count");
const runButton = document.getElementById("run-button");

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function toList(value) {
  return value
    .split(/[,，/\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function renderLeads(items) {
  leadCount.textContent = items.length;
  leadGrid.innerHTML = items
    .slice(0, 8)
    .map(
      (lead) => `
        <article class="lead-card">
          <div class="lead-card-header">
            <strong>${lead.company}</strong>
            <span>${lead.industry}</span>
          </div>
          <p>${lead.contact_name} · ${lead.role}</p>
          <p>${lead.region} · ${lead.company_size}</p>
          <p class="muted">${lead.trigger_event}</p>
        </article>
      `
    )
    .join("");
}

function renderHistory(items) {
  runCount.textContent = items.length;
  historyList.innerHTML = items.length
    ? items
        .map(
          (item) => `
            <article class="history-card">
              <strong>${item.campaign_name}</strong>
              <span>${item.created_at}</span>
              <p>合格线索 ${item.qualified_leads} · 主力客群 ${item.top_segment}</p>
            </article>
          `
        )
        .join("")
    : `<div class="empty-state">还没有运行记录。</div>`;
}

function renderTimeline(steps) {
  timelineEl.classList.remove("empty-state");
  timelineEl.innerHTML = steps
    .map(
      (step, index) => `
        <article class="timeline-card" style="animation-delay:${index * 90}ms">
          <div class="timeline-index">0${index + 1}</div>
          <div>
            <h3>${step.agent}</h3>
            <p>${step.purpose}</p>
            <strong>${step.summary}</strong>
            <ul>
              ${step.highlights.map((item) => `<li>${item}</li>`).join("")}
            </ul>
          </div>
        </article>
      `
    )
    .join("");
}

function renderMetrics(summary) {
  const cards = [
    ["合格线索", summary.qualified_leads],
    ["平均匹配分", summary.average_fit_score],
    ["P1 客户", summary.high_priority_count],
    ["主力客群", summary.top_segment]
  ];
  metricsGrid.innerHTML = cards
    .map(
      ([label, value]) => `
        <article class="metric-card">
          <span>${label}</span>
          <strong>${value}</strong>
        </article>
      `
    )
    .join("");
}

function renderPlaybook(playbook) {
  playbookEl.innerHTML = `
    <h3>运营执行剧本</h3>
    <p>${playbook.core_strategy}</p>
    <div class="chip-row">
      ${playbook.execution_focus.map((item) => `<span class="chip">${item}</span>`).join("")}
    </div>
    <div class="kpi-grid">
      ${Object.entries(playbook.weekly_kpis)
        .map(
          ([key, value]) => `
            <article class="kpi-card">
              <span>${key}</span>
              <strong>${value}</strong>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function renderResults(leads) {
  resultGrid.classList.remove("empty-state");
  resultGrid.innerHTML = leads
    .map(
      (lead) => `
        <article class="result-card">
          <div class="result-head">
            <div>
              <h3>${lead.company}</h3>
              <p>${lead.contact_name} · ${lead.role}</p>
            </div>
            <div class="badge-group">
              <span class="badge">${lead.priority}</span>
              <span class="badge soft">${lead.fit_score} 分</span>
            </div>
          </div>
          <p><strong>客群：</strong>${lead.segment}</p>
          <p><strong>痛点：</strong>${lead.pain_hypothesis}</p>
          <p><strong>切入角度：</strong>${lead.campaign_angle}</p>
          <p><strong>推荐钩子：</strong>${lead.recommended_hook}</p>
          <div class="result-block">
            <span>邮件主题</span>
            <strong>${lead.email_subject}</strong>
          </div>
          <div class="result-block">
            <span>首封文案</span>
            <p>${lead.email_body}</p>
          </div>
          <div class="result-block">
            <span>跟进节奏</span>
            <div class="chip-row">
              ${lead.cadence.map((item) => `<span class="chip">${item.day} · ${item.channel}</span>`).join("")}
            </div>
          </div>
        </article>
      `
    )
    .join("");
}

async function bootstrap() {
  try {
    const [health, leads, runs] = await Promise.all([
      fetchJson("/api/health"),
      fetchJson("/api/leads"),
      fetchJson("/api/runs")
    ]);
    healthStatus.textContent = health.status === "ok" ? "运行正常" : "异常";
    renderLeads(leads.items);
    renderHistory(runs.items);
  } catch (error) {
    healthStatus.textContent = "启动失败";
    timelineEl.innerHTML = `<div class="empty-state">初始化失败：${error.message}</div>`;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(form);
  const payload = {
    campaign_name: formData.get("campaign_name"),
    product_name: formData.get("product_name"),
    product_value: formData.get("product_value"),
    target_industries: toList(formData.get("target_industries")),
    target_sizes: toList(formData.get("target_sizes")),
    target_personas: toList(formData.get("target_personas")),
    target_markets: toList(formData.get("target_markets")),
    business_goal: formData.get("business_goal"),
    offer: formData.get("offer"),
    tone: formData.get("tone")
  };

  runButton.disabled = true;
  runButton.textContent = "协同处理中...";
  timelineEl.classList.add("empty-state");
  timelineEl.textContent = "Lead Scout、Research、Segment、Outreach、Sequence、Ops Manager 正在协同执行...";

  try {
    const result = await fetchJson("/api/run-campaign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    renderTimeline(result.timeline);
    renderMetrics(result.summary);
    renderPlaybook(result.playbook);
    renderResults(result.result_leads);
    const runs = await fetchJson("/api/runs");
    renderHistory(runs.items);
  } catch (error) {
    timelineEl.textContent = `运行失败：${error.message}`;
  } finally {
    runButton.disabled = false;
    runButton.textContent = "运行协同流程";
  }
});

bootstrap();
