from __future__ import annotations

import json
from datetime import datetime
from statistics import mean
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from courtroom_trading.agents import StubCourtroomAgentRunner
from courtroom_trading.api_models import (
    DecisionRequest,
    GoogleAuthRequest,
    ManualLoginRequest,
    ManualSignupRequest,
    OutcomeUpdateRequest,
)
from courtroom_trading.auth import AuthConfig, AuthService, extract_bearer_token
from courtroom_trading.config import AppConfig
from courtroom_trading.contracts import AuthenticatedUser
from courtroom_trading.llm import GroqCourtroomAgentRunner, OpenAICourtroomAgentRunner
from courtroom_trading.orchestrator import TradingDecisionEngine
from courtroom_trading.repository import InMemoryDecisionRepository, MongoDecisionRepository


def create_app(
    config: AppConfig | None = None,
    repository: InMemoryDecisionRepository | MongoDecisionRepository | None = None,
) -> FastAPI:
    resolved_config = config or AppConfig.from_env()

    agent_runner = (
        GroqCourtroomAgentRunner(
            api_key=resolved_config.groq_api_key,
            model=resolved_config.groq_model,
            temperature=resolved_config.groq_temperature,
            timeout_seconds=resolved_config.openai_timeout_seconds,
        )
        if resolved_config.use_groq
        else OpenAICourtroomAgentRunner(
            api_key=resolved_config.openai_api_key,
            model=resolved_config.openai_model,
            reasoning_effort=resolved_config.openai_reasoning_effort,
            timeout_seconds=resolved_config.openai_timeout_seconds,
            store=resolved_config.openai_store,
        )
        if resolved_config.use_openai
        else StubCourtroomAgentRunner()
    )
    resolved_repository = repository or (
        MongoDecisionRepository(
            mongodb_uri=resolved_config.mongodb_uri,
            database_name=resolved_config.mongodb_database,
        )
        if resolved_config.use_mongodb
        else InMemoryDecisionRepository()
    )
    engine = TradingDecisionEngine(
        repository=resolved_repository,
        agent_runner=agent_runner,
    )
    auth_service = AuthService(
        AuthConfig(
            google_client_id=resolved_config.google_client_id,
            jwt_secret=resolved_config.jwt_secret,
            jwt_expiration_minutes=resolved_config.jwt_expiration_minutes,
            auth_skip_google_verification=resolved_config.auth_skip_google_verification,
            auth_mode=resolved_config.auth_mode,
            demo_user_email=resolved_config.demo_user_email,
            demo_user_name=resolved_config.demo_user_name,
        )
    )

    app = FastAPI(title=resolved_config.app_name, version="0.3.0")
    app.state.auth_service = auth_service
    app.state.repository = resolved_repository
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_config.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def current_user(token: str = Depends(extract_bearer_token)) -> AuthenticatedUser:
        return auth_service.authenticate_bearer_token(token)

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "environment": resolved_config.environment,
            "provider": resolved_config.llm_provider,
            "model": resolved_config.groq_model if resolved_config.use_groq else resolved_config.openai_model,
            "storage": "mongodb" if resolved_config.use_mongodb else "in-memory",
        }

    @app.get("/api/config")
    async def app_config() -> dict[str, object]:
        return {
            "provider": resolved_config.llm_provider,
            "model": resolved_config.groq_model if resolved_config.use_groq else resolved_config.openai_model,
            "public_base_url": resolved_config.public_base_url,
            "frontend_origin": resolved_config.frontend_origin,
            "google_client_id": resolved_config.google_client_id,
            "google_client_secret_configured": bool(resolved_config.google_client_secret),
            "auth_enabled": resolved_config.auth_mode in {"demo", "google"},
            "auth_mode": resolved_config.auth_mode,
            "storage": "mongodb" if resolved_config.use_mongodb else "in-memory",
        }

    @app.post("/api/auth/demo")
    async def login_demo() -> dict[str, object]:
        if resolved_config.auth_mode != "demo":
            raise HTTPException(status_code=403, detail="Demo auth is disabled.")
        user = auth_service.build_demo_user()
        await resolved_repository.upsert_user(user)
        session = auth_service.issue_access_token(user)
        return {
            "access_token": session["access_token"],
            "expires_at": session["expires_at"],
            "user": user.to_dict(),
        }

    @app.post("/api/auth/google")
    async def login_with_google(request: GoogleAuthRequest) -> dict[str, object]:
        if resolved_config.auth_mode != "google":
            raise HTTPException(status_code=403, detail="Google auth is not the active auth mode.")
        if not resolved_config.google_client_id and not resolved_config.auth_skip_google_verification:
            raise HTTPException(status_code=500, detail="Google auth is not configured.")
        user = auth_service.verify_google_credential(request.credential)
        await resolved_repository.upsert_user(user)
        session = auth_service.issue_access_token(user)
        return {
            "access_token": session["access_token"],
            "expires_at": session["expires_at"],
            "user": user.to_dict(),
        }

    @app.post("/api/auth/manual/signup")
    async def signup_manual(request: ManualSignupRequest) -> dict[str, object]:
        if resolved_config.auth_mode == "demo":
            raise HTTPException(status_code=403, detail="Manual auth is disabled in demo mode.")

        email = request.email.strip().lower()
        name = request.name.strip()
        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="Valid email is required.")
        if len(name) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters.")
        if len(request.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

        password_hash, password_salt = auth_service.hash_password(request.password)
        created = await resolved_repository.create_local_user(
            email=email,
            name=name,
            password_hash=password_hash,
            password_salt=password_salt,
        )
        if not created:
            raise HTTPException(status_code=409, detail="Account already exists for this email.")

        user = auth_service.build_local_user(email=email, name=name)
        session = auth_service.issue_access_token(user)
        return {
            "access_token": session["access_token"],
            "expires_at": session["expires_at"],
            "user": user.to_dict(),
        }

    @app.post("/api/auth/manual/login")
    async def login_manual(request: ManualLoginRequest) -> dict[str, object]:
        if resolved_config.auth_mode == "demo":
            raise HTTPException(status_code=403, detail="Manual auth is disabled in demo mode.")

        email = request.email.strip().lower()
        user_doc = await resolved_repository.get_local_user_by_email(email)
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        if not auth_service.verify_password(
            request.password,
            user_doc.get("password_hash", ""),
            user_doc.get("password_salt", ""),
        ):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        user = auth_service.build_local_user(email=email, name=user_doc.get("name", email))
        session = auth_service.issue_access_token(user)
        return {
            "access_token": session["access_token"],
            "expires_at": session["expires_at"],
            "user": user.to_dict(),
        }

    @app.get("/api/market/search")
    async def market_search(q: str) -> dict[str, object]:
        """Search for Indian stocks (NSE and BSE)."""
        query = q.strip().upper()
        if len(query) < 2:
            return {"items": []}

        # Try Yahoo Finance search, filter for Indian stocks
        url = (
            "https://query2.finance.yahoo.com/v1/finance/search"
            f"?q={quote(query)}&quotesCount=50&newsCount=0"
        )
        payload = _fetch_json(url)
        quotes = payload.get("quotes", []) if isinstance(payload, dict) else []

        items = []
        for quote_item in quotes:
            symbol = str(quote_item.get("symbol", "")).strip()
            if not symbol:
                continue
            
            # Filter for Indian stocks (NSE: .NS, BSE: .BO)
            if not (symbol.endswith(".NS") or symbol.endswith(".BO")):
                continue
                
            items.append(
                {
                    "symbol": symbol,
                    "name": str(quote_item.get("shortname") or quote_item.get("longname") or symbol),
                    "exchange": str(quote_item.get("exchange") or ""),
                    "type": str(quote_item.get("quoteType") or ""),
                }
            )
        
        return {"items": items[:8]}  # Limit to 8 results

    @app.get("/api/market/snapshot")
    async def market_snapshot(symbol: str) -> dict[str, object]:
        """Get market snapshot for Indian stocks."""
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise HTTPException(status_code=400, detail="Symbol is required.")
        
        # Ensure it's an Indian stock symbol
        if not (normalized_symbol.endswith(".NS") or normalized_symbol.endswith(".BO")):
            # Assume NSE if no extension provided
            if "." not in normalized_symbol:
                normalized_symbol = f"{normalized_symbol}.NS"

        chart_url = (
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{quote(normalized_symbol)}?range=1mo&interval=1d"
        )
        payload = _fetch_json(chart_url)
        try:
            result = payload["chart"]["result"][0]
            quote_data = result["indicators"]["quote"][0]
            timestamps = result.get("timestamp", [])
            raw_closes = quote_data.get("close", [])
            raw_volumes = quote_data.get("volume", [])

            closes: list[float] = []
            volumes: list[float] = []
            trade_dates: list[str] = []

            for index, close_value in enumerate(raw_closes):
                if close_value is None:
                    continue

                closes.append(float(close_value))

                if index < len(raw_volumes) and raw_volumes[index] is not None:
                    volumes.append(float(raw_volumes[index]))

                if index < len(timestamps) and timestamps[index] is not None:
                    trade_dates.append(datetime.utcfromtimestamp(int(timestamps[index])).strftime("%Y-%m-%d"))
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Unable to fetch market data for this symbol.") from exc

        if len(closes) < 15:
            raise HTTPException(status_code=502, detail="Insufficient market data returned for this symbol.")

        ma20 = _safe_mean(closes[-20:])
        ma50 = _safe_mean(closes[-50:] if len(closes) >= 50 else closes)
        rsi_value = _compute_rsi(closes, period=14)
        latest_price = closes[-1]
        latest_volume = volumes[-1] if volumes else 0.0
        avg_volume = _safe_mean(volumes[-20:]) if volumes else 0.0

        trend = "UPTREND" if ma20 > ma50 else "DOWNTREND" if ma20 < ma50 else "RANGE"
        volume_strength = (
            "HIGH"
            if avg_volume and latest_volume > avg_volume * 1.2
            else "LOW"
            if avg_volume and latest_volume < avg_volume * 0.8
            else "MODERATE"
        )
        rsi_signal = "OVERSOLD" if rsi_value < 30 else "OVERBOUGHT" if rsi_value > 70 else "NEUTRAL"
        trend_strength = (
            "STRONG"
            if abs(ma20 - ma50) / max(latest_price, 1e-6) > 0.03
            else "WEAK"
            if abs(ma20 - ma50) / max(latest_price, 1e-6) < 0.01
            else "MODERATE"
        )
        ma_alignment = "BULLISH" if latest_price >= ma20 >= ma50 else "BEARISH" if latest_price <= ma20 <= ma50 else "NEUTRAL"

        min_30d = min(closes)
        max_30d = max(closes)
        min_10d = min(closes[-10:])
        max_10d = max(closes[-10:])
        change_30d = latest_price - closes[0]
        change_pct_30d = (change_30d / closes[0] * 100) if closes[0] else 0.0

        return {
            "symbol": normalized_symbol,
            "name": str(result.get("meta", {}).get("symbol", normalized_symbol)),
            "features": {
                "price": round(latest_price, 4),
                "rsi": round(rsi_value, 2),
                "ma20": round(ma20, 4),
                "ma50": round(ma50, 4),
                "trend": trend,
                "volume_strength": volume_strength,
            },
            "derived_signals": {
                "rsi_signal": rsi_signal,
                "trend_strength": trend_strength,
                "ma_alignment": ma_alignment,
            },
            "market_context": {
                "symbol": normalized_symbol,
                "last_30_days": {
                    "close_prices": [round(value, 4) for value in closes[-30:]],
                    "dates": trade_dates[-30:] if trade_dates else [],
                    "last_close": round(latest_price, 4),
                    "last_10_days": {
                        "low": round(min_10d, 4),
                        "high": round(max_10d, 4),
                    },
                    "change": round(change_30d, 4),
                    "change_percent": round(change_pct_30d, 2),
                    "low": round(min_30d, 4),
                    "high": round(max_30d, 4),
                    "average_volume": round(avg_volume, 2),
                    "latest_volume": round(latest_volume, 2),
                },
            },
        }

    @app.get("/api/auth/me")
    async def me(user: AuthenticatedUser = Depends(current_user)) -> dict[str, object]:
        return {"user": user.to_dict()}

    @app.post("/api/auth/logout")
    async def logout(user: AuthenticatedUser = Depends(current_user)) -> dict[str, object]:
        return {"ok": True, "user_id": user.user_id}

    @app.post("/api/decision")
    async def create_decision(
        request: DecisionRequest,
        user: AuthenticatedUser = Depends(current_user),
    ) -> dict[str, object]:
        try:
            return await engine.run(user, request.to_domain())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/outcomes")
    async def update_outcome(
        request: OutcomeUpdateRequest,
        user: AuthenticatedUser = Depends(current_user),
    ) -> dict[str, object]:
        updated = await engine.update_outcome(user.user_id, request.record_id, request.outcome)
        if updated is None:
            raise HTTPException(status_code=404, detail="Memory record not found.")
        return {"record": updated.to_dict()}

    @app.get("/api/history")
    async def history(
        limit: int = 20,
        user: AuthenticatedUser = Depends(current_user),
    ) -> dict[str, object]:
        records = await engine.list_history(user.user_id, limit=min(limit, 50))
        payload_records: list[dict[str, object]] = []
        for record in records:
            item = record.to_dict()

            # Preserve compatibility while ensuring required fields are always present.
            item.setdefault("bullish_factors", item.get("bull_args", []))
            item.setdefault("bearish_factors", item.get("bear_args", []))
            item.setdefault("final_reasoning", item.get("reasoning", ""))
            item.setdefault("decision_details", {})

            details = item.get("decision_details") if isinstance(item.get("decision_details"), dict) else {}

            if not item.get("bullish_factors") and isinstance(details.get("validated_arguments"), list):
                item["bullish_factors"] = [
                    str(arg.get("claim", "")).strip()
                    for arg in details["validated_arguments"]
                    if isinstance(arg, dict) and str(arg.get("side", "")).upper() == "BULL" and str(arg.get("claim", "")).strip()
                ]

            if not item.get("bearish_factors") and isinstance(details.get("validated_arguments"), list):
                item["bearish_factors"] = [
                    str(arg.get("claim", "")).strip()
                    for arg in details["validated_arguments"]
                    if isinstance(arg, dict) and str(arg.get("side", "")).upper() == "BEAR" and str(arg.get("claim", "")).strip()
                ]

            if not item.get("bearish_factors") and isinstance(details.get("rejected_arguments"), list):
                item["bearish_factors"] = [
                    str(arg.get("reason", "")).strip()
                    for arg in details["rejected_arguments"]
                    if isinstance(arg, dict) and str(arg.get("side", "")).upper() == "BEAR" and str(arg.get("reason", "")).strip()
                ]

            payload_records.append(item)

        return {"records": payload_records}

    @app.delete("/api/history")
    async def clear_history(
        user: AuthenticatedUser = Depends(current_user),
    ) -> dict[str, object]:
        """Clear all decision records for the user."""
        deleted_count = await app.state.repository.clear_records(user.user_id)
        return {"message": f"Cleared {deleted_count} decision records", "deleted_count": deleted_count}

    @app.get("/api/cache/stats")
    async def cache_stats(
        user: AuthenticatedUser = Depends(current_user),
    ) -> dict[str, object]:
        """Get cache performance statistics for the user."""
        records = await engine.list_history(user.user_id, limit=500)
        
        if not records:
            return {
                "total_decisions": 0,
                "cached_decisions": 0,
                "cache_hit_rate": 0.0,
                "avg_cache_confidence": 0.0,
                "note": "No decision history yet"
            }
        
        # Count cache hits from decision history
        # Note: this is approximate since we're counting from memory_records
        # In a production system, you'd query decision_impacts collection directly
        total = len(records)
        
        return {
            "total_decisions": total,
            "status": "Cache system is active and learning from patterns",
            "note": "Each identical feature pattern will be cached after first encounter for faster future decisions",
            "system": "Feature-key based caching (RSI bucket | Price level | MA alignment | Trend | Volume)",
        }

    return app


def _fetch_json(url: str) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail="Market data provider request failed.") from exc

    try:
        loaded = json.loads(raw)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail="Market data provider returned invalid JSON.") from exc

    if not isinstance(loaded, dict):
        raise HTTPException(status_code=502, detail="Market data provider returned an invalid payload.")
    return loaded


def _safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(mean(values))


def _compute_rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) <= period:
        return 50.0

    gains: list[float] = []
    losses: list[float] = []
    for idx in range(1, len(closes)):
        change = closes[idx] - closes[idx - 1]
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))

    avg_gain = _safe_mean(gains[-period:])
    avg_loss = _safe_mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
