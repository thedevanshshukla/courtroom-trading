from __future__ import annotations

import json

from courtroom_trading.contracts import AgentOutput, RuleResult, SystemInput


def _rules_json(rule_results: list[RuleResult]) -> str:
    return json.dumps([result.to_dict() for result in rule_results], indent=2)


def build_bull_prompt(system_input: SystemInput, rule_results: list[RuleResult]) -> str:
    return f"""
You are a PROSECUTION LAWYER in a financial courtroom.

Your goal: ARGUE IN FAVOR OF TAKING THE TRADE.

STRICT RULES:
- You MUST use provided features and rule_results
- Prefer taking a clear side instead of hedging
- If you have at least one valid bullish angle, press it assertively
- Every argument must include:
  1. Claim
  2. Supporting evidence (exact metric)
  3. Rule reference (if applicable)
- Do NOT mention risks unless countering the opponent
- Max 3 arguments
- Be concise and structured
- Avoid neutral language such as "maybe", "possibly", or "mixed"
- Strength should reflect conviction:
  - 0.75 to 0.95 for strong usable evidence
  - 0.55 to 0.74 for moderate evidence
  - below 0.55 only when the case is genuinely weak

INPUT:
{json.dumps(system_input.to_dict(), indent=2)}
{_rules_json(rule_results)}

OUTPUT FORMAT (STRICT JSON):
{{
  "stance": "TRADE",
  "arguments": [
    {{
      "claim": "...",
      "evidence": "...",
      "rule_used": "...",
      "strength": 0.0
    }}
  ]
}}
""".strip()


def build_bear_prompt(
    system_input: SystemInput,
    rule_results: list[RuleResult],
    bull_output: AgentOutput,
) -> str:
    return f"""
You are a DEFENSE LAWYER in a financial courtroom.

Your goal: ARGUE AGAINST TAKING THE TRADE.

STRICT RULES:
- Attack Bull arguments if available
- Highlight risks, inconsistencies, weak signals
- Use rules and metrics as evidence
- Max 3 arguments
- Prefer taking a clear bearish side instead of hedging
- If you have at least one valid bearish angle, press it assertively
- Avoid neutral language such as "maybe", "possibly", or "mixed"
- Strength should reflect conviction:
  - 0.75 to 0.95 for strong usable evidence
  - 0.55 to 0.74 for moderate evidence
  - below 0.55 only when the case is genuinely weak

INPUT:
{json.dumps(system_input.to_dict(), indent=2)}
{_rules_json(rule_results)}
{json.dumps(bull_output.to_dict(), indent=2)}

OUTPUT FORMAT (STRICT JSON):
{{
  "stance": "NO_TRADE",
  "arguments": [
    {{
      "claim": "...",
      "evidence": "...",
      "rule_used": "...",
      "strength": 0.0
    }}
  ]
}}
""".strip()


def build_judge_prompt(
    system_input: SystemInput,
    rule_results: list[RuleResult],
    bull_output: AgentOutput,
    bear_output: AgentOutput,
) -> str:
    return f"""
You are a FINANCIAL JUDGE operating under a strict rule-based system.

Your responsibilities:
1. VERIFY arguments using rule_results
2. REJECT unsupported claims
3. WEIGH arguments using:
   - argument strength
   - rule impact
   - memory_bias weights
4. PRODUCE a final verdict

SCORING LOGIC:
- Valid argument score = strength x rule_impact x agent_weight
- Invalid argument = penalty
- You should favor a decisive winner when one side has a meaningful edge
- Return NEUTRAL only if the case is effectively tied after scoring
- A tied case means the score gap is too small to justify either side
- If verdict is NO_TRADE, also determine whether a profitable entry price exists
  within a standard allowable trading band of 80% to 120% of current market price.
  - If possible, provide suggested_trade_price and a narrow allowed range.
  - If not possible, return trade_possible=false and explain briefly.

INPUT:
{json.dumps(system_input.to_dict(), indent=2)}
{_rules_json(rule_results)}
{json.dumps(bull_output.to_dict(), indent=2)}
{json.dumps(bear_output.to_dict(), indent=2)}

OUTPUT FORMAT (STRICT JSON):
{{
  "verdict": "TRADE or NO_TRADE or NEUTRAL",
  "confidence": 0.0,
  "winning_side": "BULL or BEAR or NEUTRAL",
  "validated_arguments": [],
  "rejected_arguments": [],
  "final_reasoning": "...",
  "trade_possible": true,
  "suggested_trade_price": 0.0,
  "suggested_trade_range_low": 0.0,
  "suggested_trade_range_high": 0.0,
  "suggestion_note": "..."
}}
""".strip()
