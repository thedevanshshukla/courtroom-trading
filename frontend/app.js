const config = window.COURTROOM_CONFIG || {};
const apiBaseUrl = (config.API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const themes = ["aurora-day", "midnight-lagoon"];
const PAGE_HASH = {
  "home-page": "home",
  "auth-page": "auth",
  "dashboard-page": "dashboard"
};
const MARKET_COLORS = {
  bull: "#16a34a",
  bear: "#dc2626",
  neutral: "#f59e0b",
  maFast: "#10b981",
  maSlow: "#ef4444"
};
const ARGUMENT_DISPLAY_LIMIT = 25;

const state = {
  auth: {
    token: localStorage.getItem("courtroom_access_token") || "",
    user: null,
    manualMode: "login"
  },
  ui: {
    inputMode: "manual",
    authTab: "google",
    selectedStock: null,
    marketSnapshot: null,
    chartsReady: false,
    detailsOpen: false,
    expandedChart: null,
    investmentPrefs: {
      quantity: 100,
      purpose: "LONG_TERM",
      budget: 0,
      risk: "MODERATE"
    }
  },
  data: {
    lastPayload: null,
    stockResults: []
  }
};

const charts = {
  price: null,
  rsi: null,
  ma: null,
  volume: null,
  expanded: null
};

let googleRenderTimer = null;

const elements = {
  homePage: document.getElementById("home-page"),
  authPage: document.getElementById("auth-page"),
  dashboardPage: document.getElementById("dashboard-page"),

  getStartedButton: document.getElementById("get-started-button"),
  loginButtonHome: document.getElementById("login-button-home"),
  backToHomeButton: document.getElementById("back-to-home-button"),

  themeToggleHome: document.getElementById("theme-toggle-home"),
  themeToggleAuth: document.getElementById("theme-toggle-auth"),
  themeToggleDashboard: document.getElementById("theme-toggle-dashboard"),

  googleLoginSlot: document.getElementById("google-login-slot"),
  googleLoginContainer: document.getElementById("google-login-container"),
  emailAuthTrigger: document.getElementById("email-auth-trigger"),
  authSwitchPrefix: document.getElementById("auth-switch-prefix"),
  authSwitchLink: document.getElementById("auth-switch-link"),

  manualAuthForm: document.getElementById("manual-auth-form"),
  manualAuthSubmit: document.getElementById("manual-auth-submit"),
  manualAuthFeedback: document.getElementById("manual-auth-feedback"),
  manualName: document.getElementById("manual-name"),
  manualPassword: document.getElementById("manual-password"),
  manualPasswordConfirm: document.getElementById("manual-password-confirm"),
  togglePassword: document.getElementById("toggle-password"),
  togglePasswordConfirm: document.getElementById("toggle-password-confirm"),
  nameGroup: document.getElementById("name-group"),
  confirmPasswordGroup: document.getElementById("confirm-password-group"),

  modeManual: document.getElementById("mode-manual"),
  modeRealtime: document.getElementById("mode-realtime"),
  realtimePanel: document.getElementById("realtime-panel"),
  stockSearch: document.getElementById("stock-search"),
  searchStockButton: document.getElementById("search-stock-button"),
  stockResults: document.getElementById("stock-results"),
  useStockButton: document.getElementById("use-stock-button"),
  realtimeFeedback: document.getElementById("realtime-feedback"),
  investmentPrefs: document.getElementById("investment-prefs"),
  investmentQuantity: document.getElementById("investment-quantity"),
  investmentPurpose: document.getElementById("investment-purpose"),
  investmentBudget: document.getElementById("investment-budget"),
  investmentBudgetFeedback: document.getElementById("budget-feedback"),
  investmentRisk: document.getElementById("investment-risk"),
  realtimeDetails: document.getElementById("realtime-details"),
  customStartDate: document.getElementById("custom-start-date"),
  customEndDate: document.getElementById("custom-end-date"),
  customRangeCalc: document.getElementById("custom-range-calc"),
  customRangeResult: document.getElementById("custom-range-result"),

  userInfo: document.getElementById("user-info"),
  logoutButton: document.getElementById("logout-button"),
  providerBadge: document.getElementById("provider-badge"),

  form: document.getElementById("decision-form"),
  submitButton: document.getElementById("submit-button"),

  summary: document.getElementById("summary"),
  bullArguments: document.getElementById("bull-arguments"),
  bearArguments: document.getElementById("bear-arguments"),
  argumentsPanel: document.getElementById("arguments-panel"),
  argumentsNote: document.getElementById("arguments-note"),

  toggleDetailsButton: document.getElementById("toggle-details"),
  agentDetails: document.getElementById("agent-details"),
  rawOutput: document.getElementById("raw-output"),
  copyButton: document.getElementById("copy-button"),

  historyList: document.getElementById("history-list"),
  refreshHistory: document.getElementById("refresh-history"),
  clearHistory: document.getElementById("clear-history"),

  priceChart: document.getElementById("price-chart"),
  rsiChart: document.getElementById("rsi-chart"),
  maChart: document.getElementById("ma-chart"),
  volumeChart: document.getElementById("volume-chart"),
  priceChartTitle: document.getElementById("price-chart-title"),
  rsiChartTitle: document.getElementById("rsi-chart-title"),
  maChartTitle: document.getElementById("ma-chart-title"),
  volumeChartTitle: document.getElementById("volume-chart-title")
};

function setTheme(theme) {
  document.body.dataset.theme = theme;
  localStorage.setItem("courtroom_theme", theme);
  updateThemeButtons();
}

function cycleTheme() {
  const current = document.body.dataset.theme || themes[0];
  const nextIndex = (themes.indexOf(current) + 1) % themes.length;
  setTheme(themes[nextIndex]);
  if (state.ui.chartsReady) {
    renderChartsFromState();
  }
}

function initializeTheme() {
  setTheme(localStorage.getItem("courtroom_theme") || config.DEFAULT_THEME || themes[0]);
}

function updateThemeButtons() {
  const isDark = document.body.dataset.theme === "midnight-lagoon";
  const icon = isDark ? "☀" : "☾";
  [elements.themeToggleHome, elements.themeToggleAuth, elements.themeToggleDashboard].forEach((button) => {
    if (!button) return;
    button.textContent = icon;
    button.setAttribute("title", isDark ? "Switch to light theme" : "Switch to dark theme");
  });
}

function goToPage(pageId) {
  document.querySelectorAll(".page-container").forEach((page) => {
    page.classList.add("hidden");
  });
  document.getElementById(pageId)?.classList.remove("hidden");

  if (pageId === "auth-page") {
    scheduleGoogleButtonRender();
  }

  const hash = PAGE_HASH[pageId];
  if (hash && window.location.hash !== `#${hash}`) {
    window.history.pushState({ pageId }, "", `#${hash}`);
  }
}

function resolvePageFromHash() {
  const hash = (window.location.hash || "#home").replace("#", "");
  const found = Object.entries(PAGE_HASH).find(([, value]) => value === hash);
  return found ? found[0] : "home-page";
}

function setManualMode(mode) {
  state.auth.manualMode = mode;
  const isSignup = mode === "signup";

  // Keep Google OAuth available for both sign-in and sign-up tabs.
  elements.googleLoginContainer?.classList.remove("hidden");
  elements.manualAuthForm?.classList.add("hidden");
  scheduleGoogleButtonRender();

  if (elements.emailAuthTrigger) {
    elements.emailAuthTrigger.textContent = isSignup ? "Sign up by email" : "Sign in by email";
  }
  if (elements.authSwitchPrefix) {
    elements.authSwitchPrefix.textContent = isSignup ? "Already a user?" : "New user?";
  }
  if (elements.authSwitchLink) {
    elements.authSwitchLink.textContent = isSignup ? "Sign in here" : "Sign up here";
  }
  
  // Show name field only in signup mode
  if (elements.nameGroup) {
    elements.nameGroup.style.display = isSignup ? "block" : "none";
  }
  
  // Show confirm password field only in signup mode
  if (elements.confirmPasswordGroup) {
    elements.confirmPasswordGroup.style.display = isSignup ? "block" : "none";
  }
  
  if (elements.manualPassword) {
    elements.manualPassword.setAttribute("autocomplete", isSignup ? "new-password" : "current-password");
  }
  if (elements.manualAuthSubmit) {
    elements.manualAuthSubmit.textContent = isSignup ? "Create Account" : "Login";
  }
  if (elements.manualAuthFeedback) {
    elements.manualAuthFeedback.textContent = "";
  }
}

function revealEmailAuthForm() {
  elements.manualAuthForm?.classList.remove("hidden");
  elements.manualAuthFeedback.textContent = "";
  elements.manualName?.focus();
  if (state.auth.manualMode === "login") {
    elements.manualName?.blur();
    elements.manualPassword?.focus();
  }
}

function setInputMode(mode) {
  state.ui.inputMode = mode;
  const isRealtime = mode === "realtime";
  elements.modeManual?.classList.toggle("active", !isRealtime);
  elements.modeRealtime?.classList.toggle("active", isRealtime);
  elements.realtimePanel?.classList.toggle("hidden", !isRealtime);
  elements.form?.classList.toggle("hidden", isRealtime);
}

async function apiFetch(path, options = {}) {
  const method = String(options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});
  const hasBody = options.body !== undefined && options.body !== null;

  if (hasBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (state.auth.token) {
    headers.set("Authorization", `Bearer ${state.auth.token}`);
  }

  let requestPath = path;
  if (method === "GET") {
    requestPath = path.includes("?") ? `${path}&_t=${Date.now()}` : `${path}?_t=${Date.now()}`;
    headers.set("Cache-Control", "no-cache, no-store, must-revalidate");
    headers.set("Pragma", "no-cache");
  }

  const response = await fetch(`${apiBaseUrl}${requestPath}`, {
    ...options,
    method,
    headers,
    cache: "no-store"
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

function generateMockData(count, min, max) {
  return Array.from({ length: count }, () => Math.random() * (max - min) + min);
}

function buildChartOptions() {
  const computed = getComputedStyle(document.body);
  const isMidnightTheme = document.body.dataset.theme === "midnight-lagoon";
  const textColor = isMidnightTheme
    ? "#e2ebff"
    : computed.getPropertyValue("--text").trim() || "#0f172a";
  const textMuted = isMidnightTheme
    ? "#c5d2ff"
    : computed.getPropertyValue("--text-muted").trim() || "#475569";
  const borderColor = isMidnightTheme
    ? "rgba(226, 235, 255, 0.22)"
    : computed.getPropertyValue("--border").trim() || "rgba(15, 23, 42, 0.12)";
  const fontBody = computed.getPropertyValue("--font-body").trim() || "system-ui";

  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 750,
      easing: 'easeInOutQuart'
    },
    plugins: {
      legend: {
        display: true,
        labels: {
          color: textColor,
          font: { 
            family: fontBody,
            size: 12,
            weight: 500
          },
          padding: 12,
          usePointStyle: true,
          boxWidth: 8
        }
      },
      filler: {
        propagate: true
      }
    },
    scales: {
      y: {
        ticks: { 
          color: textMuted,
          font: { size: 11 },
          maxTicksLimit: 6
        },
        grid: { 
          color: borderColor,
          drawBorder: false,
          lineWidth: 0.5
        },
        beginAtZero: false
      },
      x: {
        ticks: { 
          color: textMuted,
          font: { size: 11 },
          maxRotation: 0
        },
        grid: { 
          color: borderColor,
          drawBorder: false,
          lineWidth: 0.5
        }
      }
    }
  };
}

function destroyCharts() {
  Object.values(charts).forEach((chart) => chart?.destroy());
  charts.price = null;
  charts.rsi = null;
  charts.ma = null;
  charts.volume = null;
  charts.expanded = null;
}

function ensureChartsInitialized() {
  if (state.ui.chartsReady) return;

  const chartOptions = buildChartOptions();
  const labels = Array.from({ length: 24 }, (_, index) => `${index}h`);
  const cBull = MARKET_COLORS.bull;
  const cBear = MARKET_COLORS.bear;
  const cNeutral = MARKET_COLORS.neutral;
  const cFast = MARKET_COLORS.maFast;
  const cSlow = MARKET_COLORS.maSlow;

  charts.price = new Chart(elements.priceChart.getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Price",
          data: generateMockData(24, 100, 110),
          borderColor: cBull,
          backgroundColor: `${cBull}1C`,
          fill: true,
          tension: 0.4,
          borderWidth: 2.5,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: cBull,
          pointBorderColor: "#fff",
          pointBorderWidth: 2
        }
      ]
    },
    options: chartOptions
  });

  charts.rsi = new Chart(elements.rsiChart.getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "RSI",
          data: generateMockData(24, 20, 80),
          borderColor: cNeutral,
          backgroundColor: `${cNeutral}1C`,
          fill: true,
          tension: 0.4,
          borderWidth: 2.5,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: cNeutral,
          pointBorderColor: "#fff",
          pointBorderWidth: 2
        }
      ]
    },
    options: chartOptions
  });

  charts.ma = new Chart(elements.maChart.getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "MA20",
          data: generateMockData(24, 95, 105),
          borderColor: cFast,
          backgroundColor: `${cFast}12`,
          fill: false,
          tension: 0.4,
          borderWidth: 2.5,
          pointRadius: 2,
          pointHoverRadius: 4,
          pointBackgroundColor: cFast,
          pointBorderColor: "#fff",
          pointBorderWidth: 1.5
        },
        {
          label: "MA50",
          data: generateMockData(24, 90, 110),
          borderColor: cSlow,
          backgroundColor: `${cSlow}12`,
          fill: false,
          tension: 0.4,
          borderWidth: 2.5,
          borderDash: [4, 4],
          pointRadius: 2,
          pointHoverRadius: 4,
          pointBackgroundColor: cSlow,
          pointBorderColor: "#fff",
          pointBorderWidth: 1.5
        }
      ]
    },
    options: chartOptions
  });

  charts.volume = new Chart(elements.volumeChart.getContext("2d"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Volume",
          data: generateMockData(24, 1000, 5000),
          backgroundColor: Array.from({ length: labels.length }, (_item, index) => (index % 2 === 0 ? `${cBull}BB` : `${cBear}BB`)),
          borderColor: Array.from({ length: labels.length }, (_item, index) => (index % 2 === 0 ? cBull : cBear)),
          borderWidth: 1,
          borderRadius: 6,
          hoverBackgroundColor: cNeutral
        }
      ]
    },
    options: chartOptions
  });

  state.ui.chartsReady = true;
}

function renderChartsFromState() {
  if (!state.ui.chartsReady) return;

  const marketContext = state.ui.marketSnapshot?.market_context?.last_30_days;
  const { closes, dates } = getSnapshotSeries();
  const features = state.ui.marketSnapshot?.features;

  if (Array.isArray(closes) && closes.length > 5) {
    const labelCount = closes.length;
    const labels = dates.map((dateText) => formatDateLabel(dateText));
    const isUptrend = closes[labelCount - 1] >= closes[0];
    const trendColor = isUptrend ? MARKET_COLORS.bull : MARKET_COLORS.bear;
    const monthRange = formatMonthRange(dates);

    if (elements.priceChartTitle) elements.priceChartTitle.textContent = `Price Movement (${monthRange})`;
    if (elements.rsiChartTitle) elements.rsiChartTitle.textContent = `RSI Indicator (${monthRange})`;
    if (elements.maChartTitle) elements.maChartTitle.textContent = `Moving Averages (${monthRange})`;
    if (elements.volumeChartTitle) elements.volumeChartTitle.textContent = `Volume Analysis (${monthRange})`;

    charts.price.data.labels = labels;
    charts.price.data.datasets[0].data = closes;
    charts.price.data.datasets[0].borderColor = trendColor;
    charts.price.data.datasets[0].backgroundColor = `${trendColor}1C`;
    charts.price.data.datasets[0].pointBackgroundColor = trendColor;

    const ma20Line = closes.map((_, index) => {
      const window = closes.slice(Math.max(0, index - 19), index + 1);
      const avg = window.reduce((sum, value) => sum + value, 0) / window.length;
      return Number(avg.toFixed(4));
    });

    const ma50Line = closes.map((_, index) => {
      const window = closes.slice(Math.max(0, index - 49), index + 1);
      const avg = window.reduce((sum, value) => sum + value, 0) / window.length;
      return Number(avg.toFixed(4));
    });

    charts.ma.data.labels = labels;
    charts.ma.data.datasets[0].data = ma20Line;
    charts.ma.data.datasets[1].data = ma50Line;

    charts.rsi.data.labels = labels;
    charts.rsi.data.datasets[0].data = Array.from({ length: labelCount }, () => features?.rsi || 50);

    const avgVolume = marketContext.average_volume || 0;
    const latestVolume = marketContext.latest_volume || 0;
    charts.volume.data.labels = labels;
    charts.volume.data.datasets[0].data = Array.from({ length: labelCount }, (_item, index) => {
      if (index === labelCount - 1) {
        return latestVolume;
      }
      return avgVolume;
    });
    charts.volume.data.datasets[0].backgroundColor = closes.map((value, index) => {
      if (index === 0) return `${MARKET_COLORS.neutral}BB`;
      return value >= closes[index - 1] ? `${MARKET_COLORS.bull}BB` : `${MARKET_COLORS.bear}BB`;
    });
    charts.volume.data.datasets[0].borderColor = closes.map((value, index) => {
      if (index === 0) return MARKET_COLORS.neutral;
      return value >= closes[index - 1] ? MARKET_COLORS.bull : MARKET_COLORS.bear;
    });
  }

  Object.values(charts).forEach((chart) => {
    if (chart && typeof chart.update === "function") {
      chart.update();
    }
  });
}

function renderUser() {
  if (!state.auth.user) {
    elements.userInfo?.classList.add("hidden");
    elements.logoutButton?.classList.add("hidden");
    return;
  }

  elements.userInfo?.classList.remove("hidden");
  elements.logoutButton?.classList.remove("hidden");
  if (elements.userInfo) {
    elements.userInfo.textContent = state.auth.user.name;
  }
}

async function hydrateSession() {
  if (!state.auth.token) {
    renderUser();
    return;
  }

  try {
    const payload = await apiFetch("/api/auth/me");
    state.auth.user = payload.user;
  } catch (_error) {
    state.auth.token = "";
    state.auth.user = null;
    localStorage.removeItem("courtroom_access_token");
  }

  renderUser();
}

function completeAuth(payload) {
  state.auth.token = payload.access_token;
  state.auth.user = payload.user;
  localStorage.setItem("courtroom_access_token", state.auth.token);
  renderUser();
  goToPage("dashboard-page");
  ensureChartsInitialized();
  renderChartsFromState();
  loadHistory();
}

async function handleGoogleCredential(response) {
  if (!response?.credential) {
    alert("Google authentication failed: credential not returned by provider.");
    return;
  }

  try {
    const payload = await apiFetch("/api/auth/google", {
      method: "POST",
      body: JSON.stringify({ credential: response.credential })
    });
    completeAuth(payload);
  } catch (error) {
    alert(`Google authentication failed: ${error.message}`);
  }
}

function initializeGoogleLogin() {
  if (!elements.googleLoginSlot) return;
  if (elements.authPage?.classList.contains("hidden")) return;

  if (!config.GOOGLE_CLIENT_ID) {
    elements.googleLoginSlot.innerHTML = '<p class="muted">Google Sign-In is not configured.</p>';
    return;
  }

  if (!window.google?.accounts?.id) {
    window.setTimeout(initializeGoogleLogin, 400);
    return;
  }

  try {
    const containerWidth = elements.googleLoginSlot.clientWidth || elements.googleLoginContainer?.clientWidth || 0;
    if (containerWidth < 220) {
      scheduleGoogleButtonRender();
      return;
    }

    const buttonWidth = Math.floor(containerWidth);

    elements.googleLoginSlot.innerHTML = "";

    google.accounts.id.initialize({
      client_id: config.GOOGLE_CLIENT_ID,
      callback: handleGoogleCredential
    });

    google.accounts.id.renderButton(elements.googleLoginSlot, {
      theme: "outline",
      size: "large",
      shape: "pill",
      text: state.auth.manualMode === "signup" ? "signup_with" : "signin_with",
      width: buttonWidth
    });
  } catch (_error) {
    elements.googleLoginSlot.innerHTML = '<p class="muted">Google Sign-In failed to load. Refresh and retry.</p>';
  }
}

function scheduleGoogleButtonRender() {
  if (googleRenderTimer) {
    window.clearTimeout(googleRenderTimer);
  }

  googleRenderTimer = window.setTimeout(() => {
    if (!elements.authPage?.classList.contains("hidden")) {
      initializeGoogleLogin();
    }
  }, 120);
}

async function handleManualAuthSubmit(event) {
  event.preventDefault();

  const formData = new FormData(elements.manualAuthForm);
  const email = String(formData.get("email") || "").trim();
  const password = String(formData.get("password") || "");
  const passwordConfirm = String(formData.get("password_confirm") || "");
  const name = String(formData.get("name") || "").trim();

  if (!email || !password) {
    elements.manualAuthFeedback.textContent = "Email and password are required.";
    return;
  }

  if (state.auth.manualMode === "signup") {
    if (name.length < 2) {
      elements.manualAuthFeedback.textContent = "Name must be at least 2 characters.";
      return;
    }
    if (password.length < 8) {
      elements.manualAuthFeedback.textContent = "Password must be at least 8 characters.";
      return;
    }
    if (password !== passwordConfirm) {
      elements.manualAuthFeedback.textContent = "Passwords do not match.";
      return;
    }
  }

  elements.manualAuthSubmit.disabled = true;
  elements.manualAuthSubmit.textContent = state.auth.manualMode === "signup" ? "Creating..." : "Signing in...";

  try {
    const endpoint = state.auth.manualMode === "signup"
      ? "/api/auth/manual/signup"
      : "/api/auth/manual/login";

    const body = state.auth.manualMode === "signup"
      ? { email, password, name }
      : { email, password };

    const payload = await apiFetch(endpoint, {
      method: "POST",
      body: JSON.stringify(body)
    });

    elements.manualAuthFeedback.textContent = "Authentication successful.";
    completeAuth(payload);
  } catch (error) {
    elements.manualAuthFeedback.textContent = error.message;
  } finally {
    elements.manualAuthSubmit.disabled = false;
    elements.manualAuthSubmit.textContent = state.auth.manualMode === "signup" ? "Create Account" : "Login";
  }
}

function renderArguments(target, items) {
  target.innerHTML = "";

  if (!items?.length) {
    target.innerHTML = '<div class="argument-card muted">No arguments generated.</div>';
    return;
  }

  items.slice(0, ARGUMENT_DISPLAY_LIMIT).forEach((item) => {
    const card = document.createElement("article");
    card.className = "argument-card";
    card.innerHTML = `
      <strong>${item.claim}</strong>
      <p>${item.evidence}</p>
      <div class="argument-meta">
        <span>${item.rule_used}</span>
        <span>Strength: ${item.strength}</span>
      </div>
    `;
    target.appendChild(card);
  });
}

function getFallbackEvidence(ruleName, features = {}) {
  const price = Number(features.price || 0);
  const rsi = Number(features.rsi || 0);
  const ma20 = Number(features.ma20 || 0);
  const ma50 = Number(features.ma50 || 0);
  const trend = String(features.trend || "N/A");
  const volume = String(features.volume_strength || "N/A");

  const map = {
    RSI_OVERSOLD: `RSI is ${rsi.toFixed(2)}, which is below oversold threshold when active.`,
    RSI_OVERBOUGHT: `RSI is ${rsi.toFixed(2)}, which is above overbought threshold when active.`,
    PRICE_ABOVE_MA50: `Price ${price.toFixed(2)} is above MA50 ${ma50.toFixed(2)}.`,
    PRICE_BELOW_MA50: `Price ${price.toFixed(2)} is below MA50 ${ma50.toFixed(2)}.`,
    LOW_VOLUME: `Volume strength is ${volume}.`,
    BULLISH_MA_STACK: `MA20 ${ma20.toFixed(2)} vs MA50 ${ma50.toFixed(2)} with trend ${trend}.`
  };

  return map[ruleName] || `Derived from current metrics: price ${price.toFixed(2)}, RSI ${rsi.toFixed(2)}, trend ${trend}.`;
}

function getFallbackClaim(ruleName, side) {
  const claims = {
    RSI_OVERSOLD: {
      BULL: "RSI is in an oversold zone, which can support a rebound entry.",
      BEAR: "Oversold signals can fail without follow-through, increasing downside risk."
    },
    RSI_OVERBOUGHT: {
      BULL: "Overbought conditions can stay strong in momentum phases.",
      BEAR: "RSI is in overbought territory, which raises pullback risk."
    },
    PRICE_ABOVE_MA50: {
      BULL: "Price is above MA50, which supports bullish market structure.",
      BEAR: "Price above MA50 alone is not enough without stronger confirmation."
    },
    PRICE_BELOW_MA50: {
      BULL: "Price below MA50 can reverse if momentum improves quickly.",
      BEAR: "Price is below MA50, which supports bearish structure."
    },
    LOW_VOLUME: {
      BULL: "Low volume can improve if breakout participation increases.",
      BEAR: "Low volume weakens conviction and increases failure risk."
    },
    BULLISH_MA_STACK: {
      BULL: "MA alignment supports bullish continuation.",
      BEAR: "MA alignment is weak and does not yet confirm a strong trend."
    }
  };

  const sideClaims = claims[ruleName];
  if (sideClaims && sideClaims[side]) {
    return sideClaims[side];
  }

  return side === "BULL"
    ? "Current structure provides a moderate bullish case."
    : "Current structure still has unresolved downside risk.";
}

function toSentence(text) {
  const base = String(text || "").trim().replace(/[.\s]+$/g, "");
  return base ? `${base}.` : "";
}

function toDisplayVerdict(verdict) {
  const map = {
    TRADE: "Trade",
    NO_TRADE: "No Trade",
    NEUTRAL: "Neutral"
  };
  return map[String(verdict || "").toUpperCase()] || "Unknown";
}

function toDisplaySide(side) {
  const map = {
    BULL: "Bullish Side",
    BEAR: "Bearish Side",
    NEUTRAL: "Neutral"
  };
  return map[String(side || "").toUpperCase()] || "Unknown";
}

function buildFallbackArguments(result, side) {
  const rules = Array.isArray(result?.rule_results) ? result.rule_results : [];
  const features = result?.input?.features || {};

  const validRules = rules.filter((rule) => rule?.valid && String(rule?.side || "").toUpperCase() === side);
  const generated = validRules.slice(0, 3).map((rule) => {
    const impact = Number(rule?.impact || 0.5);
    return {
      claim: getFallbackClaim(String(rule.rule || ""), side),
      evidence: getFallbackEvidence(String(rule.rule || ""), features),
      rule_used: String(rule.rule || "FALLBACK_RULE"),
      strength: Math.min(0.95, Math.max(0.55, Number((impact + 0.2).toFixed(2))))
    };
  });

  if (generated.length) return generated;

  if (side === "BULL") {
    return [
      {
        claim: "Price structure still supports a constructive bias.",
        evidence: `Price ${Number(features.price || 0).toFixed(2)} with MA20 ${Number(features.ma20 || 0).toFixed(2)} and MA50 ${Number(features.ma50 || 0).toFixed(2)}.`,
        rule_used: "FALLBACK_BULL_STRUCTURE",
        strength: 0.58
      }
    ];
  }

  return [
    {
      claim: "Momentum conviction is limited, so downside risk control is required.",
      evidence: `RSI ${Number(features.rsi || 0).toFixed(2)}, trend ${String(features.trend || "N/A")}, volume ${String(features.volume_strength || "N/A")}.`,
      rule_used: "FALLBACK_BEAR_RISK",
      strength: 0.58
    }
  ];
}

function getDisplayArguments(result, side) {
  const existing = side === "BULL"
    ? result?.bull_output?.arguments
    : result?.bear_output?.arguments;

  if (Array.isArray(existing) && existing.length) {
    return existing;
  }

  return buildFallbackArguments(result, side);
}

function normalizeReasoning(result, bullArgs, bearArgs) {
  const currentReasoning = String(result?.decision?.final_reasoning || "").trim();
  if (currentReasoning && !currentReasoning.startsWith("[CACHED]")) {
    return currentReasoning;
  }

  const verdict = String(result?.decision?.verdict || "NEUTRAL");
  const bullLead = bullArgs[0]?.claim || "Bull side found limited conviction";
  const bearLead = bearArgs[0]?.claim || "Bear side found limited conviction";
  const bullText = toSentence(bullLead);
  const bearText = toSentence(bearLead);

  if (verdict === "TRADE") {
    return `Bull case led the decision: ${bullText} Bear objections were comparatively weaker: ${bearText}`;
  }
  if (verdict === "NO_TRADE") {
    return `Bear risk signals led the decision: ${bearText} Bull support was not strong enough: ${bullText}`;
  }
  return `Both sides were close: Bull - ${bullText} Bear - ${bearText} No decisive edge was found.`;
}

function renderAgentDetailsText(result, bullArgs = [], bearArgs = []) {
  const decision = result?.decision || {};
  const validated = decision?.validated_arguments || [];
  const rejected = decision?.rejected_arguments || [];
  const reasoning = normalizeReasoning(result, bullArgs, bearArgs);
  const noTradeSuggestion = decision?.verdict === "NO_TRADE" ? getNoTradeSuggestionText(result) : "";

  const lines = [
    "Decision Summary",
    `Verdict: ${toDisplayVerdict(decision?.verdict)}`,
    `Winning Side: ${toDisplaySide(decision?.winning_side)}`,
    `Confidence: ${((Number(decision?.confidence) || 0) * 100).toFixed(1)}%`,
    `Confidence Level: ${String(decision?.confidence_level || "Medium")}`,
    `Bull Score: ${(Number(decision?.bull_total) || 0).toFixed(3)}`,
    `Bear Score: ${(Number(decision?.bear_total) || 0).toFixed(3)}`,
    "",
    `Bull Arguments: ${bullArgs.length}`,
    ...bullArgs.slice(0, ARGUMENT_DISPLAY_LIMIT).map((arg, index) => `${index + 1}. ${arg.claim}`),
    "",
    `Bear Arguments: ${bearArgs.length}`,
    ...bearArgs.slice(0, ARGUMENT_DISPLAY_LIMIT).map((arg, index) => `${index + 1}. ${arg.claim}`),
    "",
    `Validated Arguments: ${validated.length}`,
    ...validated.map((arg, index) => `${index + 1}. [${arg.side}] ${arg.rule_used}: ${arg.claim}`),
    "",
    `Rejected Arguments: ${rejected.length}`,
    ...rejected.map((arg, index) => `${index + 1}. [${arg.side}] ${arg.rule_used}: ${arg.reason}`),
    "",
    `Opportunity: ${noTradeSuggestion || "N/A"}`,
    "",
    `Reasoning: ${reasoning || "N/A"}`
  ];

  elements.rawOutput.textContent = lines.join("\n");
}

function formatDateLabel(dateText) {
  const dt = new Date(dateText);
  if (Number.isNaN(dt.getTime())) return dateText;
  return dt.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

function formatMonthRange(dates) {
  if (!Array.isArray(dates) || !dates.length) return "";
  const start = new Date(dates[0]);
  const end = new Date(dates[dates.length - 1]);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return "";
  const startLabel = start.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
  const endLabel = end.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
  return startLabel === endLabel ? startLabel : `${startLabel} - ${endLabel}`;
}

function getSnapshotSeries() {
  const market = state.ui.marketSnapshot?.market_context?.last_30_days || {};
  let closes = market.close_prices || [];
  let dates = market.dates || [];

  if (typeof closes === "string") {
    closes = closes.split(/[\s,]+/).map((value) => Number(value)).filter((value) => Number.isFinite(value));
  }

  if (!Array.isArray(dates) || dates.length !== closes.length) {
    const today = new Date();
    dates = closes.map((_value, index) => {
      const dt = new Date(today);
      dt.setDate(today.getDate() - (closes.length - 1 - index));
      return dt.toISOString().slice(0, 10);
    });
  }

  return { closes, dates };
}

function calculateCustomRangeStats() {
  const { closes, dates } = getSnapshotSeries();
  const startDate = elements.customStartDate?.value;
  const endDate = elements.customEndDate?.value;
  if (!elements.customRangeResult) return;

  if (!startDate || !endDate || !closes.length) {
    elements.customRangeResult.textContent = "Select valid start/end dates to calculate min/max.";
    return;
  }

  const selected = closes.filter((_value, index) => dates[index] >= startDate && dates[index] <= endDate);
  if (!selected.length) {
    elements.customRangeResult.textContent = "No market data available for selected date range.";
    return;
  }

  const minValue = Math.min(...selected);
  const maxValue = Math.max(...selected);
  elements.customRangeResult.textContent = `Custom Range (${formatDateLabel(startDate)} to ${formatDateLabel(endDate)}): Min Rs ${minValue.toFixed(2)} | Max Rs ${maxValue.toFixed(2)}`;
}

function renderRealtimeDetails(snapshot) {
  const market = snapshot?.market_context?.last_30_days || {};
  const { closes, dates } = getSnapshotSeries();
  if (!closes.length || !elements.realtimeDetails) return;

  const lastClose = closes[closes.length - 1];
  const last10 = closes.slice(-10);
  const min10 = Math.min(...last10);
  const max10 = Math.max(...last10);
  const min30 = Math.min(...closes);
  const max30 = Math.max(...closes);
  const pctChange = Number(market.change_percent ?? 0).toFixed(2);

  elements.realtimeDetails.innerHTML = `
    <strong>Last Close:</strong> Rs ${lastClose.toFixed(2)}<br />
    <strong>Last 10 Days:</strong> Min Rs ${min10.toFixed(2)} | Max Rs ${max10.toFixed(2)}<br />
    <strong>Last 30 Days:</strong> Min Rs ${min30.toFixed(2)} | Max Rs ${max30.toFixed(2)}<br />
    <strong>30D Change:</strong> ${pctChange}%
  `;

  if (elements.customStartDate && elements.customEndDate && dates.length) {
    const minDate = dates[0];
    const maxDate = dates[dates.length - 1];

    elements.customStartDate.min = minDate;
    elements.customStartDate.max = maxDate;
    elements.customEndDate.min = minDate;
    elements.customEndDate.max = maxDate;

    if (!elements.customStartDate.value) elements.customStartDate.value = minDate;
    if (!elements.customEndDate.value) elements.customEndDate.value = maxDate;
    calculateCustomRangeStats();
  }
}

function getNoTradeSuggestionText(payload) {
  const decision = payload?.decision || {};
  const tradePossible = decision.trade_possible;
  const suggestedPrice = Number(decision.suggested_trade_price);
  const rangeLow = Number(decision.suggested_trade_range_low);
  const rangeHigh = Number(decision.suggested_trade_range_high);
  const note = String(decision.suggestion_note || "").trim();
  const entry = Number(decision.suggested_entry_price);
  const stopLoss = Number(decision.suggested_stop_loss);
  const target = Number(decision.suggested_target_price);
  const riskReward = Number(decision.suggested_risk_reward);
  const priceReason = String(decision.suggested_price_reason || "").trim();
  const opportunityConfidence = String(decision.opportunity_confidence || "Low");

  if (tradePossible === true && Number.isFinite(suggestedPrice)) {
    const rangeText = Number.isFinite(rangeLow) && Number.isFinite(rangeHigh)
      ? `Reasonable price range: Rs ${rangeLow.toFixed(2)} to Rs ${rangeHigh.toFixed(2)}.`
      : "";
    const setupText = (
      Number.isFinite(entry) &&
      Number.isFinite(stopLoss) &&
      Number.isFinite(target) &&
      Number.isFinite(riskReward)
    )
      ? `Suggested setup: Entry Rs ${entry.toFixed(2)}, Stop Loss Rs ${stopLoss.toFixed(2)}, Target Rs ${target.toFixed(2)}, Risk Reward ${riskReward.toFixed(2)}.`
      : "";

    return [
      `No Trade at the current market price. A potential setup may emerge near Rs ${suggestedPrice.toFixed(2)}, but current conditions do not support execution.`,
      rangeText,
      setupText,
      `Opportunity confidence: ${opportunityConfidence}.`,
      priceReason,
      note
    ].filter(Boolean).join(" ");
  }

  if (tradePossible === false) {
    return note || "No suitable trading opportunity exists within a reasonable price range under current market conditions.";
  }

  return "";
}

function renderSummary(payload, bullArgs = [], bearArgs = []) {
  const decision = payload.decision;
  const userReasoning = normalizeReasoning(payload, bullArgs, bearArgs);
  const noTradeSuggestion = String(decision?.verdict || "").toUpperCase() === "NO_TRADE" ? getNoTradeSuggestionText(payload) : "";
  const suggestionBlock = noTradeSuggestion
    ? `<p class="muted"><strong>Opportunity:</strong> ${noTradeSuggestion}</p>`
    : "";

  elements.summary.innerHTML = `
    <h3>${toDisplayVerdict(decision.verdict)}</h3>
    <p><strong>Confidence Level:</strong> ${String(decision?.confidence_level || "Medium")}</p>
    <p><strong>Reasoning:</strong> ${userReasoning}</p>
    ${suggestionBlock}
  `;
}

async function loadHistory() {
  if (!state.auth.token) {
    elements.historyList.innerHTML = '<p class="muted">Sign in to view analysis history.</p>';
    return;
  }

  try {
    const payload = await apiFetch("/api/history?limit=10");
    if (!payload.records.length) {
      elements.historyList.innerHTML = '<p class="muted">No analysis history yet.</p>';
      return;
    }

    elements.historyList.innerHTML = payload.records.map((record) => `
      <div class="history-card">
        <div class="history-verdict">${record.decision}</div>
        <div class="history-info">
          <p><strong>Price: ${record.feature_snapshot.price}</strong> | RSI: ${record.feature_snapshot.rsi}</p>
          <div class="history-meta">
            <span>Confidence: ${(record.confidence * 100).toFixed(1)}%</span>
            <span>${new Date(record.created_at).toLocaleDateString()}</span>
          </div>
        </div>
        <div class="outcome-buttons">
          <button class="outcome-btn profit" data-record-id="${record.record_id}" data-outcome="PROFIT">Profit</button>
          <button class="outcome-btn loss" data-record-id="${record.record_id}" data-outcome="LOSS">Loss</button>
          <button class="outcome-btn breakeven" data-record-id="${record.record_id}" data-outcome="BREAKEVEN">Break Even</button>
        </div>
      </div>
    `).join("");
  } catch (error) {
    elements.historyList.innerHTML = `<p class="muted">Error loading history: ${error.message}</p>`;
  }
}

async function clearHistory() {
  if (!state.auth.token) {
    alert("Sign in first to clear history.");
    return;
  }

  const confirmed = confirm("Are you sure you want to delete all trade history? This cannot be undone.");
  if (!confirmed) return;

  try {
    elements.clearHistory.disabled = true;
    elements.clearHistory.textContent = "Clearing...";

    const result = await apiFetch("/api/history", { method: "DELETE" });
    
    elements.historyList.innerHTML = '<p class="muted">History cleared. No analysis history yet.</p>';
    alert(`✓ Cleared ${result.deleted_count} trade records`);
    
    await loadHistory();
  } catch (error) {
    alert(`Error clearing history: ${error.message}`);
  } finally {
    elements.clearHistory.disabled = false;
    elements.clearHistory.textContent = "Clear All";
  }
}

async function handleOutcomeUpdate(recordId, outcome) {
  try {
    await apiFetch("/api/outcomes", {
      method: "POST",
      body: JSON.stringify({ record_id: recordId, outcome })
    });
    await loadHistory();
  } catch (error) {
    alert(`Failed to update outcome: ${error.message}`);
  }
}

function collectManualPayload() {
  const formData = new FormData(elements.form);
  return {
    features: {
      price: Number(formData.get("price")),
      rsi: Number(formData.get("rsi")),
      ma20: Number(formData.get("ma20")),
      ma50: Number(formData.get("ma50")),
      trend: String(formData.get("trend")),
      volume_strength: String(formData.get("volume_strength"))
    },
    derived_signals: {
      rsi_signal: String(formData.get("rsi_signal")),
      trend_strength: String(formData.get("trend_strength")),
      ma_alignment: String(formData.get("ma_alignment"))
    },
    market_context: {}
  };
}

function applySnapshotToForm(snapshot) {
  if (!snapshot?.features || !snapshot?.derived_signals) return;

  const form = elements.form;
  form.price.value = snapshot.features.price;
  form.rsi.value = snapshot.features.rsi;
  form.ma20.value = snapshot.features.ma20;
  form.ma50.value = snapshot.features.ma50;
  form.trend.value = snapshot.features.trend;
  form.volume_strength.value = snapshot.features.volume_strength;
  form.rsi_signal.value = snapshot.derived_signals.rsi_signal;
  form.trend_strength.value = snapshot.derived_signals.trend_strength;
  form.ma_alignment.value = snapshot.derived_signals.ma_alignment;
}

function renderStockResults(items) {
  elements.stockResults.innerHTML = "";
  state.data.stockResults = items;

  if (!items.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No symbols found";
    elements.stockResults.appendChild(option);
    return;
  }

  items.forEach((item, index) => {
    const option = document.createElement("option");
    option.value = item.symbol;
    option.dataset.index = String(index);
    option.textContent = `${item.symbol} - ${item.name}`;
    elements.stockResults.appendChild(option);
  });
}

function formatInr(value) {
  return Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function calculateBudgetRange() {
  const stockPrice = Number(state.ui.marketSnapshot?.features?.price || 0);
  const quantity = Number(elements.investmentQuantity?.value || 0);
  if (!stockPrice || !quantity) return null;

  const currentCost = stockPrice * quantity;
  const lowCost = currentCost * 0.8;
  const highCost = currentCost * 1.05;

  return {
    quantity,
    stockPrice,
    currentCost: Math.ceil(currentCost),
    minBudget: Math.floor(lowCost),
    maxBudget: Math.ceil(highCost)
  };
}

function validateBudgetInput() {
  if (state.ui.inputMode !== "realtime") return true;
  if (!state.ui.marketSnapshot) return true;

  const range = calculateBudgetRange();
  if (!range) return true;

  const budget = Number(elements.investmentBudget?.value || 0);
  const feedbackEl = elements.investmentBudgetFeedback;

  if (!budget) {
    if (feedbackEl) {
      feedbackEl.textContent = `Expected range for ${range.quantity} shares: Rs ${formatInr(range.minBudget)} - Rs ${formatInr(range.maxBudget)} (current ~ Rs ${formatInr(range.currentCost)}).`;
      feedbackEl.classList.remove("error");
      feedbackEl.classList.remove("ok");
    }
    elements.investmentBudget?.setCustomValidity("");
    return true;
  }

  if (budget < range.minBudget) {
    if (feedbackEl) {
      feedbackEl.textContent = `Budget too low. For ${range.quantity} shares at current market, use around Rs ${formatInr(range.currentCost)}. Suggested range: Rs ${formatInr(range.minBudget)} - Rs ${formatInr(range.maxBudget)}.`;
      feedbackEl.classList.add("error");
      feedbackEl.classList.remove("ok");
    }
    elements.investmentBudget?.setCustomValidity("Budget is below suggested range.");
    return false;
  }

  if (feedbackEl) {
    feedbackEl.textContent = `Budget looks valid for ${range.quantity} shares. Suggested range: Rs ${formatInr(range.minBudget)} - Rs ${formatInr(range.maxBudget)}.`;
    feedbackEl.classList.remove("error");
    feedbackEl.classList.add("ok");
  }
  elements.investmentBudget?.setCustomValidity("");
  return true;
}

function closeExpandedChart() {
  const overlay = document.querySelector(".chart-expand-overlay");
  if (overlay) overlay.remove();
  if (charts.expanded) {
    charts.expanded.destroy();
    charts.expanded = null;
  }
  state.ui.expandedChart = null;
}

function openExpandedChart(chartKey) {
  if (!charts[chartKey]) return;
  closeExpandedChart();

  const overlay = document.createElement("div");
  overlay.className = "chart-expand-overlay";
  overlay.innerHTML = `
    <div class="chart-expand-modal">
      <div class="chart-expand-bar">
        <strong>${chartKey.toUpperCase()} Chart</strong>
        <button type="button" class="chart-expand-close" aria-label="Close expanded chart">Close</button>
      </div>
      <div class="chart-expand-canvas-wrap">
        <canvas id="expanded-chart-canvas"></canvas>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
  state.ui.expandedChart = chartKey;

  overlay.querySelector(".chart-expand-close")?.addEventListener("click", closeExpandedChart);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      closeExpandedChart();
    }
  });

  const source = charts[chartKey];
  const expandedCtx = overlay.querySelector("#expanded-chart-canvas")?.getContext("2d");
  if (!expandedCtx) return;

  charts.expanded = new Chart(expandedCtx, {
    type: source.config.type,
    data: JSON.parse(JSON.stringify(source.data)),
    options: {
      ...buildChartOptions(),
      maintainAspectRatio: false,
      animation: false
    }
  });
}

async function searchStocks() {
  const query = elements.stockSearch.value.trim();
  if (query.length < 2) {
    elements.realtimeFeedback.textContent = "Enter at least 2 characters to search.";
    return;
  }

  elements.searchStockButton.disabled = true;
  elements.searchStockButton.textContent = "Searching...";

  try {
    const payload = await apiFetch(`/api/market/search?q=${encodeURIComponent(query)}`);
    renderStockResults(payload.items || []);
    elements.realtimeFeedback.textContent = `Found ${(payload.items || []).length} symbols.`;
  } catch (error) {
    elements.realtimeFeedback.textContent = `Search failed: ${error.message}`;
  } finally {
    elements.searchStockButton.disabled = false;
    elements.searchStockButton.textContent = "Search";
  }
}

async function useSelectedStock() {
  const symbol = elements.stockResults.value;
  if (!symbol) {
    elements.realtimeFeedback.textContent = "Select a stock from the list first.";
    return;
  }

  elements.useStockButton.disabled = true;
  elements.useStockButton.textContent = "Fetching...";

  try {
    const snapshot = await apiFetch(`/api/market/snapshot?symbol=${encodeURIComponent(symbol)}`);
    state.ui.selectedStock = symbol;
    state.ui.marketSnapshot = snapshot;
    applySnapshotToForm(snapshot);
    renderRealtimeDetails(snapshot);
    renderChartsFromState();
    elements.realtimeFeedback.textContent = `${symbol} loaded with last 30-day context.`;
    
    // Show investment preferences section
    if (elements.investmentPrefs) {
      elements.investmentPrefs.classList.remove("hidden");
    }
    if (elements.investmentBudget && !elements.investmentBudget.value) {
      const quantity = Number(elements.investmentQuantity?.value || 100);
      elements.investmentBudget.value = String(Math.ceil(snapshot.features.price * quantity));
    }
    validateBudgetInput();
  } catch (error) {
    elements.realtimeFeedback.textContent = `Realtime fetch failed: ${error.message}`;
  } finally {
    elements.useStockButton.disabled = false;
    elements.useStockButton.textContent = "Use Selected Stock";
  }
}

async function submitDecision(event) {
  if (event) event.preventDefault();

  if (!state.auth.token) {
    elements.summary.innerHTML = "<p class='muted'>Authentication required. Please sign in.</p>";
    return;
  }

  if (state.ui.inputMode === "realtime" && !state.ui.marketSnapshot) {
    elements.summary.innerHTML = "<p class='muted'>Load a stock snapshot first in Realtime mode.</p>";
    return;
  }

  elements.submitButton.disabled = true;
  elements.submitButton.textContent = "Analyzing...";

  try {
    let payload;
    
    if (state.ui.inputMode === "realtime") {
      if (!validateBudgetInput()) {
        const range = calculateBudgetRange();
        elements.summary.innerHTML = `<p class='muted'>Budget is below expected range. Suggested budget: Rs ${formatInr(range?.minBudget)} - Rs ${formatInr(range?.maxBudget)}.</p>`;
        return;
      }

      // Update investment prefs from form
      if (elements.investmentQuantity) {
        state.ui.investmentPrefs.quantity = Number(elements.investmentQuantity.value) || 100;
      }
      if (elements.investmentPurpose) {
        state.ui.investmentPrefs.purpose = elements.investmentPurpose.value;
      }
      if (elements.investmentBudget) {
        state.ui.investmentPrefs.budget = Number(elements.investmentBudget.value) || 0;
      }
      if (elements.investmentRisk) {
        state.ui.investmentPrefs.risk = elements.investmentRisk.value;
      }

      payload = {
        features: state.ui.marketSnapshot.features,
        derived_signals: state.ui.marketSnapshot.derived_signals,
        market_context: state.ui.marketSnapshot.market_context || {},
        investment_preferences: state.ui.investmentPrefs,
        symbol: state.ui.selectedStock
      };
    } else {
      payload = collectManualPayload();
    }

    const result = await apiFetch("/api/decision", {
      method: "POST",
      body: JSON.stringify(payload)
    });

    state.data.lastPayload = result;
    const bullArgs = getDisplayArguments(result, "BULL");
    const bearArgs = getDisplayArguments(result, "BEAR");
    renderSummary(result, bullArgs, bearArgs);
    renderArguments(elements.bullArguments, bullArgs);
    renderArguments(elements.bearArguments, bearArgs);
    renderAgentDetailsText(result, bullArgs, bearArgs);

    await loadHistory();
  } catch (error) {
    elements.summary.innerHTML = `<p class='muted'>Analysis failed: ${error.message}</p>`;
    console.error("Decision error:", error);
  } finally {
    elements.submitButton.disabled = false;
    elements.submitButton.textContent = "Analyze Market";
  }
}

function toggleDetails() {
  state.ui.detailsOpen = !state.ui.detailsOpen;
  elements.agentDetails.classList.toggle("hidden", !state.ui.detailsOpen);
  elements.argumentsPanel.classList.toggle("hidden", !state.ui.detailsOpen);
  elements.argumentsNote?.classList.toggle("hidden", state.ui.detailsOpen);
  elements.toggleDetailsButton.textContent = state.ui.detailsOpen ? "Hide Details" : "Show Details";
}

function bindEvents() {
  elements.getStartedButton?.addEventListener("click", () => goToPage("auth-page"));
  elements.loginButtonHome?.addEventListener("click", () => goToPage("auth-page"));
  elements.backToHomeButton?.addEventListener("click", () => goToPage("home-page"));

  elements.themeToggleHome?.addEventListener("click", cycleTheme);
  elements.themeToggleAuth?.addEventListener("click", cycleTheme);
  elements.themeToggleDashboard?.addEventListener("click", cycleTheme);

  elements.emailAuthTrigger?.addEventListener("click", revealEmailAuthForm);
  elements.authSwitchLink?.addEventListener("click", () => {
    const nextMode = state.auth.manualMode === "signup" ? "login" : "signup";
    setManualMode(nextMode);
  });
  elements.manualAuthForm?.addEventListener("submit", handleManualAuthSubmit);

  elements.togglePassword?.addEventListener("click", (e) => {
    e.preventDefault();
    const isPassword = elements.manualPassword.type === "password";
    elements.manualPassword.type = isPassword ? "text" : "password";
    elements.togglePassword.textContent = isPassword ? "🙈" : "👁";
  });

  elements.togglePasswordConfirm?.addEventListener("click", (e) => {
    e.preventDefault();
    const isPassword = elements.manualPasswordConfirm.type === "password";
    elements.manualPasswordConfirm.type = isPassword ? "text" : "password";
    elements.togglePasswordConfirm.textContent = isPassword ? "🙈" : "👁";
  });

  elements.modeManual?.addEventListener("click", () => setInputMode("manual"));
  elements.modeRealtime?.addEventListener("click", () => setInputMode("realtime"));

  elements.searchStockButton?.addEventListener("click", searchStocks);
  elements.useStockButton?.addEventListener("click", useSelectedStock);
  elements.investmentQuantity?.addEventListener("input", validateBudgetInput);
  elements.investmentBudget?.addEventListener("input", validateBudgetInput);
  elements.customRangeCalc?.addEventListener("click", calculateCustomRangeStats);
  elements.customStartDate?.addEventListener("change", calculateCustomRangeStats);
  elements.customEndDate?.addEventListener("change", calculateCustomRangeStats);

  elements.logoutButton?.addEventListener("click", async () => {
    try {
      if (state.auth.token) {
        await apiFetch("/api/auth/logout", { method: "POST" });
      }
    } catch (_error) {
      // no-op
    }

    state.auth.token = "";
    state.auth.user = null;
    localStorage.removeItem("courtroom_access_token");
    renderUser();
    goToPage("home-page");
  });

  elements.form?.addEventListener("submit", submitDecision);
  elements.submitButton?.addEventListener("click", submitDecision);

  elements.toggleDetailsButton?.addEventListener("click", toggleDetails);

  document.querySelectorAll(".chart-card[data-chart]").forEach((card) => {
    card.addEventListener("click", () => {
      const chartKey = card.getAttribute("data-chart");
      if (chartKey) {
        openExpandedChart(chartKey);
      }
    });
  });

  elements.copyButton?.addEventListener("click", async () => {
    const detailsText = elements.rawOutput?.textContent || "";
    if (!detailsText.trim()) return;
    await navigator.clipboard.writeText(detailsText);
    elements.copyButton.textContent = "Copied";
    window.setTimeout(() => {
      elements.copyButton.textContent = "Copy Details";
    }, 1400);
  });

  elements.refreshHistory?.addEventListener("click", loadHistory);
  elements.clearHistory?.addEventListener("click", clearHistory);

  document.addEventListener("click", async (event) => {
    const button = event.target.closest(".outcome-btn");
    if (!button) return;

    const recordId = button.dataset.recordId;
    const outcome = button.dataset.outcome;
    if (!recordId || !outcome) return;

    await handleOutcomeUpdate(recordId, outcome);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.ui.expandedChart) {
      closeExpandedChart();
    }
  });

  window.addEventListener("popstate", () => {
    let pageId = resolvePageFromHash();
    if (!state.auth.token && pageId === "dashboard-page") {
      pageId = "auth-page";
    }
    document.querySelectorAll(".page-container").forEach((page) => page.classList.add("hidden"));
    document.getElementById(pageId)?.classList.remove("hidden");
    scheduleGoogleButtonRender();
  });

  window.addEventListener("load", scheduleGoogleButtonRender);
  window.addEventListener("resize", scheduleGoogleButtonRender);
}

async function bootstrap() {
  initializeTheme();
  setManualMode("login");
  setInputMode("manual");

  await hydrateSession();

  try {
    const appConfig = await apiFetch("/api/config");
    elements.providerBadge.textContent = `${appConfig.provider}:${appConfig.model}`;
  } catch (_error) {
    elements.providerBadge.textContent = "Unavailable";
  }

  const requestedPage = resolvePageFromHash();

  if (state.auth.token) {
    if (requestedPage === "home-page" || requestedPage === "auth-page") {
      goToPage("dashboard-page");
    } else {
      goToPage(requestedPage);
    }
    ensureChartsInitialized();
    await loadHistory();
  } else {
    if (requestedPage === "dashboard-page") {
      goToPage("auth-page");
    } else {
      goToPage(requestedPage);
    }
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  await bootstrap();
});
