from __future__ import annotations

from dataclasses import dataclass

from courtroom_trading.contracts import AgentOutput, Argument, RuleResult, SystemInput


@dataclass(slots=True)
class AgentContext:
    system_input: SystemInput
    rule_results: list[RuleResult]


class CourtroomAgentRunner:
    async def run_bull(self, context: AgentContext) -> AgentOutput:
        raise NotImplementedError

    async def run_bear(self, context: AgentContext, bull_output: AgentOutput) -> AgentOutput:
        raise NotImplementedError


class StubCourtroomAgentRunner(CourtroomAgentRunner):
    async def run_bull(self, context: AgentContext) -> AgentOutput:
        bullish_rules = [rule for rule in context.rule_results if rule.valid and rule.side == "BULL"][:3]
        arguments = [
            Argument(
                claim=f"{rule.rule} supports entering the trade.",
                evidence=_evidence_for_rule(rule.rule, context.system_input),
                rule_used=rule.rule,
                strength=min(0.95, max(0.58, round(rule.impact + 0.25, 2))),
            )
            for rule in bullish_rules
        ]
        return AgentOutput(stance="TRADE", arguments=arguments)

    async def run_bear(self, context: AgentContext, bull_output: AgentOutput) -> AgentOutput:
        bearish_rules = [rule for rule in context.rule_results if rule.valid and rule.side == "BEAR"][:3]
        arguments = [
            Argument(
                claim=f"{rule.rule} weakens the case for entering the trade.",
                evidence=_evidence_for_rule(rule.rule, context.system_input),
                rule_used=rule.rule,
                strength=min(0.95, max(0.58, round(rule.impact + 0.22, 2))),
            )
            for rule in bearish_rules
        ]

        if not arguments and bull_output.arguments:
            arguments.append(
                Argument(
                    claim="Bull evidence is incomplete without a matching bearish invalidation check.",
                    evidence="No active bearish rule exceeded the threshold, reducing conviction symmetry.",
                    rule_used="NO_ACTIVE_BEAR_RULE",
                    strength=0.2,
                )
            )

        return AgentOutput(stance="NO_TRADE", arguments=arguments)


def _evidence_for_rule(rule_name: str, system_input: SystemInput) -> str:
    features = system_input.features
    mapping = {
        "RSI_OVERSOLD": f"RSI is {features.rsi}, below 30.",
        "RSI_OVERBOUGHT": f"RSI is {features.rsi}, above 70.",
        "PRICE_ABOVE_MA50": f"Price is {features.price} and MA50 is {features.ma50}.",
        "PRICE_BELOW_MA50": f"Price is {features.price} and MA50 is {features.ma50}.",
        "LOW_VOLUME": f"Volume strength is {features.volume_strength}.",
        "BULLISH_MA_STACK": f"MA20 is {features.ma20} and MA50 is {features.ma50}.",
    }
    return mapping.get(rule_name, "Derived from supplied metrics.")
