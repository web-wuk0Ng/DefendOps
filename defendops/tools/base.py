"""工具抽象：工具即端点，LLM 运行时按 schema 发现并决定调用，引擎不硬编码流程。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]          # JSON Schema：入参
    handler: Callable[..., Any]         # 实际执行函数

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict[str, Any]]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"未知工具：{name}"}
        try:
            return tool.handler(**arguments)
        except Exception as exc:  # noqa: BLE001 - 工具错误回灌给 LLM 自行处理
            return {"error": f"工具 {name} 执行失败：{type(exc).__name__}: {exc}"}

    def names(self) -> list[str]:
        return list(self._tools)
