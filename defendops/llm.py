"""LLM 客户端：OpenAI 兼容协议，支持 DeepSeek/通义/Kimi/智谱/混元/Ollama 等。

设计原则：模型不可用就是不可用，探活失败或调用失败一律抛错，不写规则兜底。
"""
from __future__ import annotations

from typing import Any

from openai import OpenAI

from .config import AppConfig
from .exceptions import ModelUnavailableError


class LLMClient:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        llm = cfg.llm
        self._client = OpenAI(
            base_url=llm.base_url,
            api_key=llm.api_key,
            timeout=llm.timeout,
            max_retries=llm.max_retries,
        )

    def probe(self) -> bool:
        """探活：向模型发一个最小请求确认可用。"""
        try:
            self._client.chat.completions.create(
                model=self.cfg.llm.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception as exc:  # noqa: BLE001 - 探活需要吞掉所有异常转成布尔
            return False

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> Any:
        """发起一次 chat 调用。失败抛 ModelUnavailableError，绝不返回假结果。"""
        kwargs: dict[str, Any] = {
            "model": self.cfg.llm.model,
            "messages": messages,
            "temperature": self.cfg.llm.temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if response_format:
            kwargs["response_format"] = response_format
        try:
            return self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(f"模型调用失败：{type(exc).__name__}: {exc}") from exc
