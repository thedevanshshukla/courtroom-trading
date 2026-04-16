from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from courtroom_trading.contracts import AuthenticatedUser, DerivedSignals, Features, MemoryBias, SystemInput
from courtroom_trading.orchestrator import TradingDecisionEngine, run_sync
from courtroom_trading.repository import InMemoryDecisionRepository


def main() -> None:
    sample_input = SystemInput(
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

    engine = TradingDecisionEngine(repository=InMemoryDecisionRepository())
    user = AuthenticatedUser(
        user_id="demo-user",
        email="demo@example.com",
        name="Demo Trader",
    )
    result = run_sync(engine, user, sample_input)
    print(json.dumps(result["decision"], indent=2))


if __name__ == "__main__":
    main()
