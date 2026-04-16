const form = document.getElementById("decision-form");
const submitButton = document.getElementById("submit-button");
const summary = document.getElementById("summary");
const rawOutput = document.getElementById("raw-output");
const bullArguments = document.getElementById("bull-arguments");
const bearArguments = document.getElementById("bear-arguments");
const providerBadge = document.getElementById("provider-badge");
const copyButton = document.getElementById("copy-button");

let latestPayload = null;

async function bootstrap() {
  try {
    const response = await fetch("/api/config");
    const payload = await response.json();
    providerBadge.textContent = `${payload.provider}:${payload.model}`;
  } catch (_error) {
    providerBadge.textContent = "config unavailable";
  }
}

function buildRequestPayload(formData) {
  return {
    features: {
      price: Number(formData.get("price")),
      rsi: Number(formData.get("rsi")),
      ma20: Number(formData.get("ma20")),
      ma50: Number(formData.get("ma50")),
      trend: formData.get("trend"),
      volume_strength: formData.get("volume_strength"),
    },
    derived_signals: {
      rsi_signal: formData.get("rsi_signal"),
      trend_strength: formData.get("trend_strength"),
      ma_alignment: formData.get("ma_alignment"),
    },
  };
}

function renderArguments(target, items) {
  target.innerHTML = "";
  if (!items.length) {
    target.innerHTML = `<div class="argument-card muted">No arguments returned.</div>`;
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "argument-card";
    card.innerHTML = `
      <p><strong>${item.claim}</strong></p>
      <p>${item.evidence}</p>
      <p class="muted">Rule: ${item.rule_used} • Strength: ${item.strength}</p>
    `;
    target.appendChild(card);
  });
}

function renderSummary(payload) {
  const decision = payload.decision;
  summary.className = "summary-card";
  summary.innerHTML = `
    <h3>${decision.verdict}</h3>
    <p>${decision.final_reasoning}</p>
    <div class="metric-row">
      <div class="metric"><strong>Confidence</strong><br>${decision.confidence}</div>
      <div class="metric"><strong>Bull</strong><br>${decision.bull_total}</div>
      <div class="metric"><strong>Bear</strong><br>${decision.bear_total}</div>
    </div>
  `;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  submitButton.textContent = "Running...";

  try {
    const payload = buildRequestPayload(new FormData(form));
    const response = await fetch("/api/decision", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    latestPayload = result;

    if (!response.ok) {
      throw new Error(result.detail || "Request failed");
    }

    renderSummary(result);
    renderArguments(bullArguments, result.bull_output.arguments);
    renderArguments(bearArguments, result.bear_output.arguments);
    rawOutput.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    summary.className = "summary-card";
    summary.innerHTML = `<strong>Request failed</strong><p>${error.message}</p>`;
    rawOutput.textContent = String(error.message);
    bullArguments.innerHTML = "";
    bearArguments.innerHTML = "";
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Run Case";
  }
});

copyButton.addEventListener("click", async () => {
  if (!latestPayload) {
    return;
  }
  await navigator.clipboard.writeText(JSON.stringify(latestPayload, null, 2));
  copyButton.textContent = "Copied";
  window.setTimeout(() => {
    copyButton.textContent = "Copy JSON";
  }, 1200);
});

bootstrap();
