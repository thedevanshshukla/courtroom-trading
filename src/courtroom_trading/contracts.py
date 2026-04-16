from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Features:
    price: float
    rsi: float
    ma20: float
    ma50: float
    trend: str
    volume_strength: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DerivedSignals:
    rsi_signal: str
    trend_strength: str
    ma_alignment: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MemoryBias:
    bull_weight: float = 0.5
    bear_weight: float = 0.5
    historical_outcome_bias: str = "NEUTRAL"
    similar_cases: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SystemInput:
    features: Features
    derived_signals: DerivedSignals
    memory_bias: MemoryBias
    market_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "features": self.features.to_dict(),
            "derived_signals": self.derived_signals.to_dict(),
            "memory_bias": self.memory_bias.to_dict(),
            "market_context": self.market_context,
        }


@dataclass(slots=True)
class AuthenticatedUser:
    user_id: str
    email: str
    name: str
    picture: str = ""
    google_sub: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RuleResult:
    rule: str
    valid: bool
    impact: float
    side: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Argument:
    claim: str
    evidence: str
    rule_used: str
    strength: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentOutput:
    stance: str
    arguments: list[Argument] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stance": self.stance,
            "arguments": [argument.to_dict() for argument in self.arguments],
        }


@dataclass(slots=True)
class ValidatedArgument:
    side: str
    claim: str
    rule_used: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RejectedArgument:
    side: str
    claim: str
    rule_used: str
    reason: str
    penalty: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class JudgeDecision:
    verdict: str
    confidence: float
    winning_side: str
    bull_total: float
    bear_total: float
    final_score: float
    validated_arguments: list[ValidatedArgument]
    rejected_arguments: list[RejectedArgument]
    final_reasoning: str
    confidence_level: str = "Medium"
    trade_possible: bool | None = None
    suggested_trade_price: float | None = None
    suggested_trade_range_low: float | None = None
    suggested_trade_range_high: float | None = None
    suggestion_note: str = ""
    suggested_entry_price: float | None = None
    suggested_stop_loss: float | None = None
    suggested_target_price: float | None = None
    suggested_risk_reward: float | None = None
    suggested_price_reason: str = ""
    opportunity_confidence: str = "Low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "winning_side": self.winning_side,
            "bull_total": self.bull_total,
            "bear_total": self.bear_total,
            "final_score": self.final_score,
            "validated_arguments": [item.to_dict() for item in self.validated_arguments],
            "rejected_arguments": [item.to_dict() for item in self.rejected_arguments],
            "final_reasoning": self.final_reasoning,
            "confidence_level": self.confidence_level,
            "trade_possible": self.trade_possible,
            "suggested_trade_price": self.suggested_trade_price,
            "suggested_trade_range_low": self.suggested_trade_range_low,
            "suggested_trade_range_high": self.suggested_trade_range_high,
            "suggestion_note": self.suggestion_note,
            "suggested_entry_price": self.suggested_entry_price,
            "suggested_stop_loss": self.suggested_stop_loss,
            "suggested_target_price": self.suggested_target_price,
            "suggested_risk_reward": self.suggested_risk_reward,
            "suggested_price_reason": self.suggested_price_reason,
            "opportunity_confidence": self.opportunity_confidence,
        }


@dataclass(slots=True)
class MemoryRecord:
    user_id: str
    features_hash: str
    decision: str
    bull_score: float
    bear_score: float
    winning_side: str
    confidence: float = 0.0
    outcome: str = "PENDING"
    feature_snapshot: dict[str, Any] = field(default_factory=dict)
    signal_snapshot: dict[str, Any] = field(default_factory=dict)
    record_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DecisionImpact:
    """Cached decision outcome for reuse on matching feature patterns."""
    cache_key: str
    user_id: str
    verdict: str  # TRADE/NO_TRADE/NEUTRAL
    confidence: float
    bull_score: float
    bear_score: float
    hit_count: int = 1  # how many times this pattern was matched
    avg_confidence: float = 0.0  # rolling average confidence
    last_matched: str = field(default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"))
    impact_id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
