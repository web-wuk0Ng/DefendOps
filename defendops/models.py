"""核心数据模型：告警输入与研判结论输出。"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Alert:
    """一条待研判的安全告警。字段刻意保持通用，适配不同 SIEM 来源。"""

    id: str
    title: str
    source: str = ""
    severity: str = "medium"          # info/low/medium/high/critical
    timestamp: str = ""
    assets: list[str] = field(default_factory=list)   # 涉及的主机 / IP / 账号
    raw: dict[str, Any] = field(default_factory=dict) # 原始字段，原样带给模型

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Alert":
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            source=str(data.get("source", "")),
            severity=str(data.get("severity", "medium")),
            timestamp=str(data.get("timestamp", "")),
            assets=list(data.get("assets", [])),
            raw=dict(data.get("raw", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Evidence:
    """ReAct 过程中一次工具调用的证据。"""

    tool: str
    arguments: dict[str, Any]
    result: Any


@dataclass
class Verdict:
    """研判结论。由 LLM 按 schema 产出，再解析成此结构。"""

    disposition: str = "needs_review"   # true_positive / false_positive / needs_review
    severity: str = "medium"
    confidence: float = 0.0             # 0~1
    summary: str = ""
    rationale: str = ""
    recommended_actions: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)   # ReAct 思考 / 决策轨迹

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence"] = [
            {"tool": e.tool, "arguments": e.arguments, "result": e.result}
            for e in self.evidence
        ]
        return d
