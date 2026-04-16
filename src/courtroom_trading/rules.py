from __future__ import annotations

from collections.abc import Callable

from courtroom_trading.contracts import Features, RuleResult


RuleCondition = Callable[[Features], bool]


class TradingRule:
    def __init__(
        self,
        name: str,
        condition: RuleCondition,
        impact: float,
        side: str,
        description: str,
    ) -> None:
        self.name = name
        self.condition = condition
        self.impact = impact
        self.side = side
        self.description = description


RULES: tuple[TradingRule, ...] = (
    TradingRule(
        name="RSI_OVERSOLD",
        condition=lambda f: f.rsi < 30,
        impact=0.7,
        side="BULL",
        description="RSI below 30 signals oversold conditions.",
    ),
    TradingRule(
        name="RSI_OVERBOUGHT",
        condition=lambda f: f.rsi > 70,
        impact=0.7,
        side="BEAR",
        description="RSI above 70 signals overbought conditions.",
    ),
    TradingRule(
        name="PRICE_ABOVE_MA50",
        condition=lambda f: f.price > f.ma50,
        impact=0.5,
        side="BULL",
        description="Price above MA50 supports a bullish structure.",
    ),
    TradingRule(
        name="PRICE_BELOW_MA50",
        condition=lambda f: f.price < f.ma50,
        impact=0.5,
        side="BEAR",
        description="Price below MA50 supports a bearish structure.",
    ),
    TradingRule(
        name="LOW_VOLUME",
        condition=lambda f: f.volume_strength.upper() == "LOW",
        impact=0.6,
        side="BEAR",
        description="Low volume weakens conviction in a move.",
    ),
    TradingRule(
        name="BULLISH_MA_STACK",
        condition=lambda f: f.ma20 > f.ma50,
        impact=0.4,
        side="BULL",
        description="MA20 above MA50 supports bullish alignment.",
    ),
)


def evaluate_rules(features: Features) -> list[RuleResult]:
    results: list[RuleResult] = []
    for rule in RULES:
        is_valid = rule.condition(features)
        results.append(
            RuleResult(
                rule=rule.name,
                valid=is_valid,
                impact=rule.impact,
                side=rule.side,
                description=rule.description,
            )
        )
    return results
