"""ReAct 研判引擎：观察告警 → LLM 规划 → 调用工具取证 → 再推理 → 结构化结论。

无模型 / 模型失败直接抛错，不降级到规则引擎。
"""
from __future__ import annotations

import json
import re
from typing import Any

from ..exceptions import ModelUnavailableError
from ..llm import LLMClient
from ..models import Alert, Evidence, Verdict
from ..tools import ToolRegistry
from .prompts import system_prompt
from .state import AgentState


def _extract_json(text: str) -> dict[str, Any]:
    """从模型文本里稳健地抠出第一个 JSON 对象。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("模型未返回 JSON 结论")
    return json.loads(text[start:end + 1])


def triage(alert: Alert, llm: LLMClient, registry: ToolRegistry, max_rounds: int = 8) -> Verdict:
    """对单条告警执行 ReAct 研判。"""
    state = AgentState(alert=alert)
    state.messages.append({"role": "system", "content": system_prompt(tool_names=registry.names())})
    state.messages.append({
        "role": "user",
        "content": "请研判以下告警：\n" + json.dumps(alert.to_dict(), ensure_ascii=False, indent=2),
    })
    state.trace.append(f"接收告警 {alert.id}：{alert.title}")

    for _ in range(max_rounds):
        state.rounds += 1
        response = llm.chat(state.messages, tools=registry.schemas())
        msg = response.choices[0].message

        # 模型决定调用工具 → 执行并把结果回灌为 observation
        if msg.tool_calls:
            state.messages.append(msg)
            for call in msg.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                result = registry.call(call.function.name, args)
                state.evidences.append(Evidence(tool=call.function.name, arguments=args, result=result))
                state.trace.append(f"[工具] {call.function.name}({args}) → {json.dumps(result, ensure_ascii=False)[:200]}")
                state.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            state.messages.append({
                "role": "user",
                "content": "基于以上工具结果继续研判。若证据充分，请直接输出最终 JSON 结论。",
            })
            continue

        # 无工具调用 → 视为最终结论
        state.verdict_raw = msg.content or ""
        state.trace.append("模型给出最终结论")
        return _to_verdict(state)

    # 超过轮次上限仍未下结论：强制再问一次，要求立即收敛
    raise ModelUnavailableError(
        f"研判在 {max_rounds} 轮内未收敛出结论。这是模型未能完成任务，不提供规则兜底。"
    )


def _to_verdict(state: AgentState) -> Verdict:
    data = _extract_json(state.verdict_raw)
    return Verdict(
        disposition=str(data.get("disposition", "needs_review")),
        severity=str(data.get("severity", "medium")),
        confidence=float(data.get("confidence", 0.0)) if isinstance(data.get("confidence"), (int, float)) else 0.0,
        summary=str(data.get("summary", "")),
        rationale=str(data.get("rationale", "")),
        recommended_actions=list(data.get("recommended_actions", [])),
        evidence=list(state.evidences),
        trace=list(state.trace),
    )
