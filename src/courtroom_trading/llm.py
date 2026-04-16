from __future__ import annotations

import json
import re

from openai import AsyncOpenAI

from courtroom_trading.agents import AgentContext, CourtroomAgentRunner
from courtroom_trading.contracts import AgentOutput, Argument
from courtroom_trading.prompts import build_bear_prompt, build_bull_prompt


AGENT_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "stance": {"type": "string"},
        "arguments": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "claim": {"type": "string"},
                    "evidence": {"type": "string"},
                    "rule_used": {"type": "string"},
                    "strength": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["claim", "evidence", "rule_used", "strength"],
            },
        },
    },
    "required": ["stance", "arguments"],
}


class OpenAICourtroomAgentRunner(CourtroomAgentRunner):
    def __init__(
        self,
        api_key: str,
        model: str,
        reasoning_effort: str = "medium",
        timeout_seconds: float = 60.0,
        store: bool = False,
    ) -> None:
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds)
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.store = store

    async def run_bull(self, context: AgentContext) -> AgentOutput:
        prompt = build_bull_prompt(context.system_input, context.rule_results)
        return await self._run_structured(prompt=prompt, schema_name="bull_agent_output")

    async def run_bear(self, context: AgentContext, bull_output: AgentOutput) -> AgentOutput:
        prompt = build_bear_prompt(context.system_input, context.rule_results, bull_output)
        return await self._run_structured(prompt=prompt, schema_name="bear_agent_output")

    async def _run_structured(self, prompt: str, schema_name: str) -> AgentOutput:
        response = await self.client.responses.create(
            model=self.model,
            input=prompt,
            store=self.store,
            reasoning={"effort": self.reasoning_effort},
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": AGENT_OUTPUT_SCHEMA,
                }
            },
        )
        payload = json.loads(response.output_text)
        arguments = [
            Argument(
                claim=item["claim"],
                evidence=item["evidence"],
                rule_used=item["rule_used"],
                strength=float(item["strength"]),
            )
            for item in payload.get("arguments", [])[:3]
        ]
        return AgentOutput(stance=payload["stance"], arguments=arguments)


class GroqCourtroomAgentRunner(CourtroomAgentRunner):
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.3,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=timeout_seconds,
        )
        self.model = model
        self.temperature = temperature

    async def run_bull(self, context: AgentContext) -> AgentOutput:
        prompt = build_bull_prompt(context.system_input, context.rule_results)
        return await self._run_chat(
            system_message=(
                "You are a PROSECUTION LAWYER in a financial courtroom. "
                "Output only valid JSON matching the requested structure."
            ),
            user_message=prompt,
        )

    async def run_bear(self, context: AgentContext, bull_output: AgentOutput) -> AgentOutput:
        prompt = build_bear_prompt(context.system_input, context.rule_results, bull_output)
        return await self._run_chat(
            system_message=(
                "You are a DEFENSE LAWYER in a financial courtroom. "
                "Output only valid JSON matching the requested structure."
            ),
            user_message=prompt,
        )

    async def _run_chat(self, system_message: str, user_message: str) -> AgentOutput:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=self.temperature,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content or "{}"
        payload = extract_json_object(raw_content)
        arguments = [
            Argument(
                claim=item["claim"],
                evidence=item["evidence"],
                rule_used=item["rule_used"],
                strength=float(item["strength"]),
            )
            for item in payload.get("arguments", [])[:3]
        ]
        return AgentOutput(stance=payload["stance"], arguments=arguments)


def extract_json_object(text: str) -> dict[str, object]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group())
