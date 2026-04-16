from __future__ import annotations

import shutil
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi.testclient import TestClient

from courtroom_trading.config import AppConfig
from courtroom_trading.contracts import (
    AuthenticatedUser,
    DerivedSignals,
    Features,
    MemoryBias,
    SystemInput,
)
from courtroom_trading.orchestrator import TradingDecisionEngine, run_sync
from courtroom_trading.repository import InMemoryDecisionRepository
from courtroom_trading.rules import evaluate_rules
from courtroom_trading.webapp import create_app


class CourtroomTradingTests(unittest.TestCase):
    def _workspace_temp_dir(self) -> Path:
        path = ROOT / ".test_tmp" / uuid.uuid4().hex
        path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_rule_evaluation_flags_expected_rules(self) -> None:
        features = Features(
            price=102,
            rsi=28,
            ma20=100,
            ma50=95,
            trend="UPTREND",
            volume_strength="LOW",
        )
        results = evaluate_rules(features)
        indexed = {item.rule: item.valid for item in results}

        self.assertTrue(indexed["RSI_OVERSOLD"])
        self.assertTrue(indexed["PRICE_ABOVE_MA50"])
        self.assertTrue(indexed["LOW_VOLUME"])
        self.assertTrue(indexed["BULLISH_MA_STACK"])
        self.assertFalse(indexed["RSI_OVERBOUGHT"])

    def test_engine_runs_end_to_end(self) -> None:
        engine = TradingDecisionEngine(repository=InMemoryDecisionRepository())
        user = AuthenticatedUser(user_id="u-1", email="user@example.com", name="User One")
        payload = SystemInput(
            features=Features(
                price=102,
                rsi=28,
                ma20=100,
                ma50=95,
                trend="UPTREND",
                volume_strength="LOW",
            ),
            derived_signals=DerivedSignals(
                rsi_signal="OVERSOLD",
                trend_strength="MODERATE",
                ma_alignment="BULLISH",
            ),
            memory_bias=MemoryBias(),
        )

        result = run_sync(engine, user, payload)

        self.assertIn(result["decision"]["verdict"], {"TRADE", "NO_TRADE"})
        self.assertIn("bull_output", result)
        self.assertIn("bear_output", result)
        self.assertGreaterEqual(result["decision"]["confidence"], 0.0)

    def test_repository_records_are_persisted(self) -> None:
        repository = InMemoryDecisionRepository()
        engine = TradingDecisionEngine(repository=repository)
        user = AuthenticatedUser(user_id="u-2", email="user2@example.com", name="User Two")
        payload = SystemInput(
            features=Features(
                price=90,
                rsi=75,
                ma20=94,
                ma50=100,
                trend="DOWNTREND",
                volume_strength="LOW",
            ),
            derived_signals=DerivedSignals(
                rsi_signal="OVERBOUGHT",
                trend_strength="STRONG",
                ma_alignment="BEARISH",
            ),
            memory_bias=MemoryBias(),
        )

        run_sync(engine, user, payload)

        self.assertEqual(len(repository.records), 1)
        self.assertEqual(repository.records[0].user_id, "u-2")
        self.assertTrue(repository.records[0].features_hash)

    def test_api_health_auth_and_decision_routes(self) -> None:
        config = AppConfig(
            app_name="Test Courtroom Trading",
            environment="test",
            host="127.0.0.1",
            port=8000,
            openai_api_key="",
            openai_model="gpt-5.4-mini",
            openai_reasoning_effort="medium",
            openai_timeout_seconds=10,
            openai_store=False,
            use_openai=False,
            groq_api_key="",
            groq_model="llama3-70b-8192",
            groq_temperature=0.3,
            use_groq=False,
            llm_provider="stub",
            public_base_url="",
            frontend_origin="http://127.0.0.1:3000",
            allowed_origins=["*"],
            mongodb_uri="",
            mongodb_database="courtroom_test",
            use_mongodb=False,
            google_client_id="test-google-client",
            google_client_secret="",
            jwt_secret="test-secret",
            jwt_expiration_minutes=60,
            auth_skip_google_verification=True,
            auth_mode="demo",
            demo_user_email="demo@example.com",
            demo_user_name="Demo User",
        )
        client = TestClient(create_app(config, repository=InMemoryDecisionRepository()))

        health = client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["provider"], "stub")
        self.assertEqual(health.json()["storage"], "in-memory")

        login = client.post("/api/auth/demo")
        self.assertEqual(login.status_code, 200)
        token = login.json()["access_token"]

        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["email"], "demo@example.com")

        decision = client.post(
            "/api/decision",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "features": {
                    "price": 102,
                    "rsi": 28,
                    "ma20": 100,
                    "ma50": 95,
                    "trend": "UPTREND",
                    "volume_strength": "LOW",
                },
                "derived_signals": {
                    "rsi_signal": "OVERSOLD",
                    "trend_strength": "MODERATE",
                    "ma_alignment": "BULLISH",
                },
            },
        )
        self.assertEqual(decision.status_code, 200)
        payload = decision.json()
        self.assertIn("memory_record", payload)
        self.assertIn(payload["decision"]["verdict"], {"TRADE", "NO_TRADE"})

        history = client.get("/api/history", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["records"]), 1)


if __name__ == "__main__":
    unittest.main()
