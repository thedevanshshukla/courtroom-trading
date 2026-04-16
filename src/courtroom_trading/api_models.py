from __future__ import annotations

from pydantic import BaseModel, Field

from courtroom_trading.contracts import DerivedSignals, Features, MemoryBias, SystemInput


class FeaturesModel(BaseModel):
    price: float
    rsi: float = Field(ge=0, le=100)
    ma20: float
    ma50: float
    trend: str
    volume_strength: str

    def to_domain(self) -> Features:
        return Features(**self.model_dump())


class DerivedSignalsModel(BaseModel):
    rsi_signal: str
    trend_strength: str
    ma_alignment: str

    def to_domain(self) -> DerivedSignals:
        return DerivedSignals(**self.model_dump())


class DecisionRequest(BaseModel):
    features: FeaturesModel
    derived_signals: DerivedSignalsModel
    market_context: dict[str, object] = Field(default_factory=dict)
    investment_preferences: dict[str, object] = Field(default_factory=dict)
    symbol: str | None = None

    def to_domain(self) -> SystemInput:
        return SystemInput(
            features=self.features.to_domain(),
            derived_signals=self.derived_signals.to_domain(),
            memory_bias=MemoryBias(),
            market_context=self.market_context,
        )


class OutcomeUpdateRequest(BaseModel):
    record_id: str
    outcome: str = Field(pattern="^(PROFIT|LOSS|BREAKEVEN|CANCELLED|PENDING)$")


class GoogleAuthRequest(BaseModel):
    credential: str


class ManualSignupRequest(BaseModel):
    email: str
    password: str
    name: str


class ManualLoginRequest(BaseModel):
    email: str
    password: str
