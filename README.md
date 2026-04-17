# ⚖️ Courtroom Trading System

A multi-agent AI decision system that simulates real-world trading reasoning using a **Bull–Bear–Judge architecture**.

Instead of relying on black-box predictions, this system focuses on **decision quality, risk awareness, and explainable reasoning** to determine whether a trade should be taken.

---

## 🚀 Why This Exists

Most trading systems try to answer:

> *“What will the price be?”*

This system answers a more practical and actionable question:

> **“Is this trade worth taking?”**

It prioritizes:

* Decision quality over raw prediction accuracy
* Risk management over blind execution
* Explainability over opaque models

---

## 🧠 Core Idea

Markets are uncertain. Signals conflict.

So instead of trusting a single model, this system simulates **structured disagreement**:

* A **Bull agent** argues for the trade
* A **Bear agent** argues against it
* A **Judge** evaluates both sides using deterministic logic

👉 The result is not just a prediction — but a **justified decision**

---

## ⚙️ How It Works

```text
Market Data → Bull Agent → Bear Agent → Judge → Final Decision
```

### Pipeline

1. Market data is processed (price, RSI, moving averages, volume)
2. Bull and Bear agents generate structured arguments
3. Backend validates signals (filters weak or invalid claims)
4. Judge evaluates based on:

   * Momentum strength
   * Trend alignment
   * ATR-based volatility
   * Risk–reward ratio
5. System decides to:

   * Execute trade
   * Reject trade
   * Suggest conditional opportunity

---

## 📊 Key Features

* ⚖️ Multi-agent reasoning (Bull vs Bear vs Judge)
* 🧠 Explainable AI decisions (no black-box outputs)
* 📉 ATR-based volatility modeling
* 🎯 Risk–reward validation (filters low-quality trades)
* 🚫 Intelligent **No Trade** detection
* 💡 Conditional opportunity suggestions (entry, stop-loss, target)
* 📊 Confidence scoring (Low / Medium / High)
* ⚠️ Market instability suppression
* 🗄️ MongoDB-backed history with full decision reasoning
* 🔐 Google OAuth authentication (with demo mode)
* 📈 Interactive charts (Price, RSI, Moving Averages, Volume)
* 🎨 Dark/Light theme with optimized readability

---

## 🧾 Example Output

```text
Verdict: No Trade
Confidence: Low

Bullish Factors:
- Price is above moving average, indicating trend support

Bearish Factors:
- Weak momentum
- Uncertain market conditions

Final Decision:
Trade is not recommended at the current price due to insufficient momentum and elevated risk.

Opportunity Insight:
A potential setup may emerge near ₹95, where risk–reward improves.

Suggested Setup:
- Entry: ₹95
- Stop Loss: ₹90
- Target: ₹110
- Risk–Reward Ratio: 2.0

Note:
Current market conditions do not strongly support execution.
```

---

## 📁 Project Structure

```bash
courtroom-trading/
│
├── backend/                 # FastAPI entrypoint
│   └── main.py
│
├── frontend/                # Static frontend (UI)
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   ├── config.js           # Runtime config (DO NOT commit secrets)
│   └── config.example.js
│
├── src/courtroom_trading/  # Core logic
│   ├── contracts.py        # Data schemas
│   ├── scoring.py          # Decision engine
│   ├── orchestrator.py     # Flow control
│   ├── prompts.py          # Agent prompts
│   ├── llm.py              # LLM integration
│   ├── repository.py       # DB interaction
│   └── auth.py             # Authentication logic
│
├── tests/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🔧 Configuration

### Frontend (`frontend/config.js`)

```javascript
window.COURTROOM_CONFIG = {
  API_BASE_URL: "http://127.0.0.1:8000",
  GOOGLE_CLIENT_ID: "your-google-client-id",
  DEFAULT_THEME: "aurora-day"
};
```

> Google Client ID is public and safe to expose.

---

### Backend (`.env`)

```env
GROQ_API_KEY=your_key
JWT_SECRET=your_secret
MONGODB_URI=your_uri
GOOGLE_CLIENT_SECRET=your_secret
```

---

## 🛠️ Setup

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

---

### Frontend

```bash
cd frontend
python -m http.server 3000
```

Open:

```
http://127.0.0.1:3000
```

---

## 🔐 Security

* No credentials are stored in the repository
* All sensitive values must be stored in `.env`
* Never commit:

  * API keys
  * JWT secrets
  * Database URIs

---

## 🚀 Future Scope

* 📊 Backtesting engine for historical evaluation
* ⚡ Real-time market data integration
* 🔔 Alerts for high-confidence opportunities
* 🤖 Lightweight ML for signal enhancement (without replacing explainable logic)
* 🧠 Extending multi-agent architecture to:

  * Recommendation systems
  * Strategic decision systems

---

## ⚠️ Disclaimer

This project is for educational purposes only.

It does **not** provide financial advice. Trading involves risk.

---

## 🏁 Final Thought

This system is not built to predict the market.

It is built to **make better decisions under uncertainty**.
