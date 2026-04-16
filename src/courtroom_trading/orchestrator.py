from __future__ import annotations

import asyncio

from courtroom_trading.agents import AgentContext, CourtroomAgentRunner, StubCourtroomAgentRunner
from courtroom_trading.contracts import AuthenticatedUser, DecisionImpact, JudgeDecision, MemoryRecord, SystemInput
from courtroom_trading.prompts import build_bear_prompt, build_bull_prompt, build_judge_prompt
from courtroom_trading.repository import DecisionRepository, generate_cache_key, hash_features
from courtroom_trading.rules import evaluate_rules
from courtroom_trading.scoring import assess_confidence_level, decide_case, suggest_no_trade_entry


class TradingDecisionEngine:
    def __init__(
        self,
        repository: DecisionRepository,
        agent_runner: CourtroomAgentRunner | None = None,
    ) -> None:
        self.repository = repository
        self.agent_runner = agent_runner or StubCourtroomAgentRunner()

    async def run(self, user: AuthenticatedUser, system_input: SystemInput) -> dict[str, object]:
        memory_bias = await self.repository.fetch_bias(user.user_id, system_input)
        hydrated_input = SystemInput(
            features=system_input.features,
            derived_signals=system_input.derived_signals,
            memory_bias=memory_bias,
            market_context=system_input.market_context,
        )
        rule_results = evaluate_rules(hydrated_input.features)
        
        # Generate cache key and check for cached impact
        cache_key = generate_cache_key(hydrated_input)
        cached_impact = await self.repository.get_cached_impact(user.user_id, cache_key)
        
        cache_hit = False
        bull_output = None
        bear_output = None
        decision = None
        cache_argument_runner = StubCourtroomAgentRunner()
        
        if cached_impact:
            # Use cached decision instead of running agents
            cache_hit = True
            # Keep UI explainability intact by generating deterministic arguments
            # locally while still reusing the cached verdict/scores.
            context = AgentContext(system_input=hydrated_input, rule_results=rule_results)
            bull_output = await cache_argument_runner.run_bull(context)
            bear_output = await cache_argument_runner.run_bear(context, bull_output)

            # Reconstruct decision from cached impact data
            decision = JudgeDecision(
                verdict=cached_impact.verdict,
                confidence=cached_impact.confidence,
                winning_side="BULL" if cached_impact.bull_score >= cached_impact.bear_score else "BEAR",
                bull_total=cached_impact.bull_score,
                bear_total=cached_impact.bear_score,
                final_score=cached_impact.bull_score - cached_impact.bear_score,
                validated_arguments=[],
                rejected_arguments=[],
                final_reasoning=_build_cached_reasoning(
                    verdict=cached_impact.verdict,
                    bull_claims=[item.claim for item in bull_output.arguments],
                    bear_claims=[item.claim for item in bear_output.arguments],
                    hit_count=cached_impact.hit_count,
                ),
                confidence_level=assess_confidence_level(
                    system_input=hydrated_input,
                    rule_results=rule_results,
                    risk_reward=None,
                    unstable_market=False,
                ),
                trade_possible=None,
                suggested_trade_price=None,
                suggested_trade_range_low=None,
                suggested_trade_range_high=None,
                suggestion_note="",
                suggested_entry_price=None,
                suggested_stop_loss=None,
                suggested_target_price=None,
                suggested_risk_reward=None,
                suggested_price_reason="",
                opportunity_confidence="Low",
            )

            if cached_impact.verdict == "NO_TRADE":
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
                    _unstable_market,
                ) = suggest_no_trade_entry(hydrated_input, rule_results)
                decision.trade_possible = trade_possible
                decision.suggested_trade_price = suggested_trade_price
                decision.suggested_trade_range_low = suggested_trade_range_low
                decision.suggested_trade_range_high = suggested_trade_range_high
                decision.suggestion_note = suggestion_note
                decision.suggested_entry_price = suggested_entry_price
                decision.suggested_stop_loss = suggested_stop_loss
                decision.suggested_target_price = suggested_target_price
                decision.suggested_risk_reward = suggested_risk_reward
                decision.suggested_price_reason = suggested_price_reason
                decision.opportunity_confidence = opportunity_confidence
        else:
            # Run full agent pipeline
            context = AgentContext(system_input=hydrated_input, rule_results=rule_results)
            bull_output = await self.agent_runner.run_bull(context)
            bear_output = await self.agent_runner.run_bear(context, bull_output)
            decision = decide_case(
                bull_output,
                bear_output,
                rule_results,
                memory_bias,
                system_input=hydrated_input,
            )
        
        # Store decision record and update cache
        memory_record = await self.repository.store(
            MemoryRecord(
                user_id=user.user_id,
                features_hash=hash_features(hydrated_input),
                decision=decision.verdict,
                bull_score=decision.bull_total,
                bear_score=decision.bear_total,
                winning_side=decision.winning_side,
                confidence=decision.confidence,
                feature_snapshot=hydrated_input.features.to_dict(),
                signal_snapshot=hydrated_input.derived_signals.to_dict(),
            )
        )
        
        # Upsert cache impact for future reuse
        cache_impact = DecisionImpact(
            cache_key=cache_key,
            user_id=user.user_id,
            verdict=decision.verdict,
            confidence=decision.confidence,
            bull_score=decision.bull_total,
            bear_score=decision.bear_total,
            hit_count=1,
            avg_confidence=decision.confidence,
        )
        await self.repository.upsert_cache_impact(cache_impact)

        return {
            "input": hydrated_input.to_dict(),
            "rule_results": [result.to_dict() for result in rule_results],
            "bull_prompt": build_bull_prompt(hydrated_input, rule_results),
            "bear_prompt": build_bear_prompt(hydrated_input, rule_results, bull_output) if bull_output else "",
            "judge_prompt": build_judge_prompt(hydrated_input, rule_results, bull_output, bear_output) if bull_output and bear_output else "",
            "bull_output": bull_output.to_dict() if bull_output else None,
            "bear_output": bear_output.to_dict() if bear_output else None,
            "decision": decision.to_dict(),
            "memory_record": memory_record.to_dict(),
            "cache_hit": cache_hit,
            "cache_key": cache_key,
        }

    async def update_outcome(
        self,
        user_id: str,
        record_id: str,
        outcome: str,
    ) -> MemoryRecord | None:
        return await self.repository.update_outcome(user_id=user_id, record_id=record_id, outcome=outcome)

    async def list_history(self, user_id: str, limit: int = 20) -> list[MemoryRecord]:
        return await self.repository.list_records(user_id=user_id, limit=limit)


def run_sync(
    engine: TradingDecisionEngine,
    user: AuthenticatedUser,
    system_input: SystemInput,
) -> dict[str, object]:
    return asyncio.run(engine.run(user, system_input))


def _build_cached_reasoning(
    verdict: str,
    bull_claims: list[str],
    bear_claims: list[str],
    hit_count: int,
) -> str:
    bull_summary = "; ".join(bull_claims[:2]) if bull_claims else "No strong bullish claim was available"
    bear_summary = "; ".join(bear_claims[:2]) if bear_claims else "No strong bearish claim was available"

    if verdict == "TRADE":
        return (
            f"Bull side had stronger support: {bull_summary}. "
            f"Bear side concerns were weaker: {bear_summary}. "
            f"This pattern has appeared {hit_count} times and remained consistent."
        )

    if verdict == "NO_TRADE":
        return (
            f"Bear side had stronger risk signals: {bear_summary}. "
            f"Bull side support was insufficient: {bull_summary}. "
            f"This pattern has appeared {hit_count} times and remained consistent."
        )

    return (
        f"Bull case: {bull_summary}. Bear case: {bear_summary}. "
        f"Neither side created a decisive edge in this repeated pattern ({hit_count} similar cases)."
    )
