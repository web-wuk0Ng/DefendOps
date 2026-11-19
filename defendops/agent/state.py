"""Agent 内部状态（ReAct 轨迹）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import Alert, Evidence


@dataclass
class AgentState:
    alert: Alert
    messages: list[dict[str, Any]] = field(default_factory=list)  # 给 LLM 的对话
    evidences: list[Evidence] = field(default_factory=list)       # 工具取证
    trace: list[str] = field(default_factory=list)                # 人类可读轨迹
    rounds: int = 0
    verdict_raw: str = ""                                          # 模型最终 JSON 文本
