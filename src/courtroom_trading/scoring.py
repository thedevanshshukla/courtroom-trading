from __future__ import annotations

from statistics import mean, pstdev

from courtroom_trading.contracts import (
    AgentOutput,
    JudgeDecision,
    MemoryBias,
    RejectedArgument,
    RuleResult,
    SystemInput,
    ValidatedArgument,
)


INVALID_ARGUMENT_PENALTY = 0.15
NEUTRAL_SCORE_GAP = 0.08
NEUTRAL_MIN_COMBINED_SCORE = 0.12
STANDARD_RANGE_LOW_MULTIPLIER = 0.8
STANDARD_RANGE_HIGH_MULTIPLIER = 1.2
MIN_VOLATILITY_BAND = 0.03
MAX_VOLATILITY_BAND = 0.12
MIN_ACCEPTABLE_RR = 1.5
LOW_CONFIDENCE_RR_THRESHOLD = 2.0
UNSTABLE_ATR_PCT = 0.06
UNSTABLE_DAILY_MOVE = 0.08


def decide_case(
    bull_output: AgentOutput,
    bear_output: AgentOutput,
    rule_results: list[RuleResult],
    memory_bias: MemoryBias,
    system_input: SystemInput | None = None,
    threshold: float = 0.0,
) -> JudgeDecision:
    rule_index = {result.rule: result for result in rule_results if result.valid}

    validated_arguments: list[ValidatedArgument] = []
    rejected_arguments: list[RejectedArgument] = []

    bull_total = _score_side(
        side="BULL",
        output=bull_output,
        agent_weight=memory_bias.bull_weight,
        rule_index=rule_index,
        validated_arguments=validated_arguments,
        rejected_arguments=rejected_arguments,
    )
    bear_total = _score_side(
        side="BEAR",
        output=bear_output,
        agent_weight=memory_bias.bear_weight,
        rule_index=rule_index,
        validated_arguments=validated_arguments,
        rejected_arguments=rejected_arguments,
    )

    final_score = bull_total - bear_total
    combined_score = bull_total + bear_total
    is_neutral = abs(final_score) <= NEUTRAL_SCORE_GAP and combined_score >= NEUTRAL_MIN_COMBINED_SCORE

    if is_neutral:
        verdict = "NEUTRAL"
        winning_side = "NEUTRAL"
    else:
        verdict = "TRADE" if final_score > threshold else "NO_TRADE"
        winning_side = "BULL" if final_score > threshold else "BEAR"

    denominator = combined_score
    confidence = abs(final_score) / denominator if denominator > 0 else 0.0
    confidence = round(min(1.0, confidence), 3)

    trade_possible: bool | None = None
    suggested_trade_price: float | None = None
    suggested_trade_range_low: float | None = None
    suggested_trade_range_high: float | None = None
    suggestion_note = ""
    suggested_entry_price: float | None = None
    suggested_stop_loss: float | None = None
    suggested_target_price: float | None = None
    suggested_risk_reward: float | None = None
    suggested_price_reason = ""
    opportunity_confidence = "Low"
    unstable_market = False

    if verdict == "NO_TRADE" and system_input is not None:
        (
            trade_possible,
            suggested_trade_price,
            suggested_trade_range_low,
            suggested_trade_range_high,
            suggestion_note,
            suggested_entry_price,
            suggested_stop_loss,
            suggested_target_price,
            suggested_risk_reward,
            suggested_price_reason,
            opportunity_confidence,
            unstable_market,
        ) = suggest_no_trade_entry(system_input, rule_results)

    confidence_level = assess_confidence_level(
        system_input=system_input,
        rule_results=rule_results,
        risk_reward=suggested_risk_reward,
        unstable_market=unstable_market,
    )

    final_reasoning = build_professional_reasoning(
        verdict=verdict,
        bull_total=bull_total,
        bear_total=bear_total,
        validated_arguments=validated_arguments,
        rejected_arguments=rejected_arguments,
        trade_possible=trade_possible,
        suggestion_note=suggestion_note,
        suggested_entry_price=suggested_entry_price,
        suggested_stop_loss=suggested_stop_loss,
        suggested_target_price=suggested_target_price,
        suggested_risk_reward=suggested_risk_reward,
    )

    return JudgeDecision(
        verdict=verdict,
        confidence=confidence,
        winning_side=winning_side,
        bull_total=round(bull_total, 3),
        bear_total=round(bear_total, 3),
        final_score=round(final_score, 3),
        validated_arguments=validated_arguments,
        rejected_arguments=rejected_arguments,
        final_reasoning=final_reasoning,
        trade_possible=trade_possible,
        suggested_trade_price=suggested_trade_price,
        suggested_trade_range_low=suggested_trade_range_low,
        suggested_trade_range_high=suggested_trade_range_high,
        suggestion_note=suggestion_note,
        suggested_entry_price=suggested_entry_price,
        suggested_stop_loss=suggested_stop_loss,
        suggested_target_price=suggested_target_price,
        suggested_risk_reward=suggested_risk_reward,
        suggested_price_reason=suggested_price_reason,
        confidence_level=confidence_level,
        opportunity_confidence=opportunity_confidence,
    )


def _score_side(
    side: str,
    output: AgentOutput,
    agent_weight: float,
    rule_index: dict[str, RuleResult],
    validated_arguments: list[ValidatedArgument],
    rejected_arguments: list[RejectedArgument],
) -> float:
    total = 0.0
    for argument in output.arguments[:3]:
        matched_rule = rule_index.get(argument.rule_used)
        if matched_rule is None or matched_rule.side != side:
            total = max(0.0, total - INVALID_ARGUMENT_PENALTY)
            rejected_arguments.append(
                RejectedArgument(
                    side=side,
                    claim=argument.claim,
                    rule_used=argument.rule_used,
                    reason="Rule missing, inactive, or belongs to the opposing side.",
                    penalty=INVALID_ARGUMENT_PENALTY,
                )
            )
            continue

        score = argument.strength * matched_rule.impact * agent_weight
        total += score
        validated_arguments.append(
            ValidatedArgument(
                side=side,
                claim=argument.claim,
                rule_used=argument.rule_used,
                score=round(score, 3),
            )
        )
    return total


def suggest_no_trade_entry(
    system_input: SystemInput,
    rule_results: list[RuleResult],
) -> tuple[
    bool,
    float | None,
    float | None,
    float | None,
    str,
    float | None,
    float | None,
    float | None,
    float | None,
    str,
    str,
    bool,
]:
    features = system_input.features
    current_price = float(features.price)
    ma20 = float(features.ma20)
    ma50 = float(features.ma50)

    closes = _extract_close_series(system_input)
    highs, lows = _extract_high_low_series(system_input)
    atr_pct = _estimate_atr_percentage(highs, lows, closes)
    close_volatility = _estimate_volatility(closes)
    volatility = atr_pct if atr_pct is not None else close_volatility
    dynamic_band = min(MAX_VOLATILITY_BAND, max(MIN_VOLATILITY_BAND, volatility * 2.2))

    dynamic_low = current_price * (1 - dynamic_band)
    dynamic_high = current_price * (1 + dynamic_band)

    standard_low = current_price * STANDARD_RANGE_LOW_MULTIPLIER
    standard_high = current_price * STANDARD_RANGE_HIGH_MULTIPLIER

    allowed_low = round(max(dynamic_low, standard_low), 2)
    allowed_high = round(min(dynamic_high, standard_high), 2)

    max_daily_move = _max_daily_move(closes)
    unstable_market = (atr_pct is not None and atr_pct >= UNSTABLE_ATR_PCT) or max_daily_move >= UNSTABLE_DAILY_MOVE
    if unstable_market:
        return (
            False,
            None,
            allowed_low,
            allowed_high,
            "Market conditions are currently unstable. No reliable trading opportunity can be identified.",
            None,
            None,
            None,
            None,
            "Volatility is abnormally high relative to normal trading conditions.",
            "Low",
            True,
        )

    anchor = (ma20 + ma50) / 2
    entry = round(min(max(anchor, allowed_low), allowed_high), 2)

    bull_valid = sum(1 for rule in rule_results if rule.valid and rule.side == "BULL")
    bear_valid = sum(1 for rule in rule_results if rule.valid and rule.side == "BEAR")

    if allowed_low >= allowed_high:
        return (
            False,
            None,
            round(allowed_low, 2),
            round(allowed_high, 2),
            "No suitable trading opportunity exists within a reasonable price range under current market conditions.",
            None,
            None,
            None,
            None,
            "Current volatility-adjusted bounds do not provide a valid entry window.",
            "Low",
            False,
        )

    strongly_bearish = bear_valid >= 2 and bull_valid == 0
    if strongly_bearish:
        return (
            False,
            None,
            allowed_low,
            allowed_high,
            "No suitable trading opportunity exists within a reasonable price range under current market conditions.",
            None,
            None,
            None,
            None,
            "Bearish factors remain dominant even after adjusting for volatility.",
            "Low",
            False,
        )

    stop_distance = max(entry * volatility * 1.4, entry * 0.01)
    stop_loss = round(entry - stop_distance, 2)
    target = round(entry + (stop_distance * 2.0), 2)
    risk = max(0.0, entry - stop_loss)
    reward = max(0.0, target - entry)
    risk_reward = round((reward / risk), 2) if risk > 0 else 0.0

    if stop_loss < allowed_low:
        stop_loss = round(allowed_low, 2)
        risk = max(0.0, entry - stop_loss)
        risk_reward = round((reward / risk), 2) if risk > 0 else 0.0

    if target > allowed_high:
        target = round(allowed_high, 2)
        reward = max(0.0, target - entry)
        risk_reward = round((reward / risk), 2) if risk > 0 else 0.0

    if risk <= 0 or reward <= 0 or risk_reward < MIN_ACCEPTABLE_RR:
        return (
            False,
            None,
            allowed_low,
            allowed_high,
            "No suitable trading opportunity exists within a reasonable price range under current market conditions.",
            None,
            None,
            None,
            None,
            "Any potential entry in the allowed range fails minimum risk-reward requirements.",
            "Low",
            False,
        )

    opportunity_confidence = "Low" if risk_reward < LOW_CONFIDENCE_RR_THRESHOLD else "Medium"
    reason = (
        f"At this level, price aligns with support near moving averages and improves risk-reward conditions "
        f"under current volatility."
    )

    return (
        True,
        entry,
        allowed_low,
        allowed_high,
        "A potential setup may emerge near this level, but current conditions do not support execution.",
        entry,
        stop_loss,
        target,
        risk_reward,
        reason,
        opportunity_confidence,
        False,
    )


def _extract_close_series(system_input: SystemInput) -> list[float]:
    market = system_input.market_context.get("last_30_days", {}) if isinstance(system_input.market_context, dict) else {}
    closes = market.get("close_prices", []) if isinstance(market, dict) else []
    if isinstance(closes, list):
        values = [float(item) for item in closes if isinstance(item, (int, float))]
        return values
    return []


def _extract_high_low_series(system_input: SystemInput) -> tuple[list[float], list[float]]:
    market = system_input.market_context.get("last_30_days", {}) if isinstance(system_input.market_context, dict) else {}
    highs = market.get("high_prices", []) if isinstance(market, dict) else []
    lows = market.get("low_prices", []) if isinstance(market, dict) else []

    high_values = [float(item) for item in highs if isinstance(item, (int, float))] if isinstance(highs, list) else []
    low_values = [float(item) for item in lows if isinstance(item, (int, float))] if isinstance(lows, list) else []
    return high_values, low_values


def _estimate_volatility(closes: list[float]) -> float:
    if len(closes) < 2:
        return 0.025

    pct_moves: list[float] = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        curr = closes[i]
        if prev <= 0:
            continue
        pct_moves.append(abs((curr - prev) / prev))

    if not pct_moves:
        return 0.025

    avg_move = mean(pct_moves)
    dispersion = pstdev(pct_moves) if len(pct_moves) > 1 else 0.0
    return max(0.015, avg_move + dispersion)


def _estimate_atr_percentage(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return None

    length = min(len(highs), len(lows), len(closes))
    highs = highs[-length:]
    lows = lows[-length:]
    closes = closes[-length:]

    true_ranges: list[float] = []
    for i in range(1, length):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i - 1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(max(0.0, tr))

    if len(true_ranges) < period:
        return None

    atr = mean(true_ranges[-period:])
    latest_close = closes[-1]
    if latest_close <= 0:
        return None
    return max(0.0, atr / latest_close)


def _max_daily_move(closes: list[float]) -> float:
    if len(closes) < 2:
        return 0.0
    moves = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        curr = closes[i]
        if prev <= 0:
            continue
        moves.append(abs((curr - prev) / prev))
    return max(moves) if moves else 0.0


def assess_confidence_level(
    system_input: SystemInput | None,
    rule_results: list[RuleResult],
    risk_reward: float | None,
    unstable_market: bool,
) -> str:
    if unstable_market:
        return "Low"

    bull_valid = sum(1 for rule in rule_results if rule.valid and rule.side == "BULL")
    bear_valid = sum(1 for rule in rule_results if rule.valid and rule.side == "BEAR")
    total_valid = bull_valid + bear_valid
    agreement = abs(bull_valid - bear_valid) / max(1, total_valid)

    momentum_map = {"WEAK": 0.25, "MODERATE": 0.55, "STRONG": 0.85}
    trend_strength = "MODERATE"
    if system_input is not None:
        trend_strength = str(system_input.derived_signals.trend_strength or "MODERATE").upper()
    momentum_strength = momentum_map.get(trend_strength, 0.5)

    if risk_reward is None:
        rr_quality = 0.45
    elif risk_reward < MIN_ACCEPTABLE_RR:
        rr_quality = 0.2
    elif risk_reward < LOW_CONFIDENCE_RR_THRESHOLD:
        rr_quality = 0.45
    elif risk_reward < 2.5:
        rr_quality = 0.7
    else:
        rr_quality = 0.9

    score = (agreement * 0.45) + (momentum_strength * 0.3) + (rr_quality * 0.25)
    if score >= 0.72:
        return "High"
    if score >= 0.48:
        return "Medium"
    return "Low"


def _summarize_side(validated_arguments: list[ValidatedArgument], side: str) -> str:
    side_items = [item.claim for item in validated_arguments if item.side == side][:2]
    if side_items:
        return " | ".join(side_items)
    if side == "BULL":
        return "Bullish evidence exists, but it lacks enough validated strength."
    return "Bearish evidence exists, but it lacks enough validated strength."


def build_professional_reasoning(
    verdict: str,
    bull_total: float,
    bear_total: float,
    validated_arguments: list[ValidatedArgument],
    rejected_arguments: list[RejectedArgument],
    trade_possible: bool | None,
    suggestion_note: str,
    suggested_entry_price: float | None,
    suggested_stop_loss: float | None,
    suggested_target_price: float | None,
    suggested_risk_reward: float | None,
) -> str:
    bullish = _summarize_side(validated_arguments, "BULL")
    bearish = _summarize_side(validated_arguments, "BEAR")
    rejected_count = len(rejected_arguments)

    lines = [
        f"Bullish factors: {bullish}",
        f"Bearish factors: {bearish}",
    ]

    if verdict == "TRADE":
        lines.append(
            f"Final decision logic: Bullish score ({bull_total:.3f}) is stronger than bearish score ({bear_total:.3f}), so Trade is preferred at current price."
        )
        return "\n".join(lines)

    if verdict == "NO_TRADE":
        lines.append(
            f"Final decision logic: Bearish score ({bear_total:.3f}) outweighs bullish score ({bull_total:.3f}), so current price is not suitable for entry."
        )
        if rejected_count > 0:
            lines.append(
                f"Bullish signals are currently insufficient because {rejected_count} argument(s) failed validation against active rules."
            )

        if trade_possible and all(
            value is not None
            for value in [suggested_entry_price, suggested_stop_loss, suggested_target_price, suggested_risk_reward]
        ):
            lines.append(
                "Condition for acceptance: "
                f"Trade may become possible near Rs {suggested_entry_price:.2f} with stop loss Rs {suggested_stop_loss:.2f}, "
                f"target Rs {suggested_target_price:.2f}, and risk-reward {suggested_risk_reward:.2f}."
            )
            if suggestion_note:
                lines.append(f"Price justification: {suggestion_note}")
        else:
            lines.append("No suitable trading opportunity exists within a reasonable price range under current market conditions.")

        return "\n".join(lines)

    lines.append(
        f"Final decision logic: Bullish score ({bull_total:.3f}) and bearish score ({bear_total:.3f}) are too close, so no clear edge exists at current price."
    )
    return "\n".join(lines)
