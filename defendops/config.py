"""配置加载。无模型 / 无 key 时明确报错，不做离线降级。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import ConfigError

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG = _PROJECT_ROOT / "config" / "config.json"


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = 0.1
    timeout: int = 60
    max_retries: int = 2


@dataclass
class AgentConfig:
    max_rounds: int = 8
    language: str = "zh-CN"


@dataclass
class AppConfig:
    llm: LLMConfig
    agent: AgentConfig


def load_config(path: str | Path | None = None) -> AppConfig:
    """从 JSON 文件加载配置；文件不存在时抛 ConfigError。"""
    cfg_path = Path(path) if path else _DEFAULT_CONFIG
    if not cfg_path.exists():
        raise ConfigError(
            f"配置文件不存在：{cfg_path}。请复制 config/config.example.json 为 config/config.json 并填入模型信息。"
        )
    try:
        raw: dict[str, Any] = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"配置文件不是合法 JSON：{cfg_path}（{exc}）") from exc

    llm_raw = raw.get("llm", {})
    agent_raw = raw.get("agent", {})
    llm = LLMConfig(
        provider=llm_raw.get("provider", "deepseek"),
        base_url=llm_raw.get("base_url", ""),
        api_key=llm_raw.get("api_key", ""),
        model=llm_raw.get("model", ""),
        temperature=llm_raw.get("temperature", 0.1),
        timeout=llm_raw.get("timeout", 60),
        max_retries=llm_raw.get("max_retries", 2),
    )
    agent = AgentConfig(
        max_rounds=agent_raw.get("max_rounds", 8),
        language=agent_raw.get("language", "zh-CN"),
    )
    cfg = AppConfig(llm=llm, agent=agent)
    validate_config(cfg)
    return cfg


def validate_config(cfg: AppConfig) -> None:
    """模型是硬依赖：缺一即报错，绝不静默降级到规则引擎。"""
    missing = []
    if not cfg.llm.base_url:
        missing.append("llm.base_url")
    if not cfg.llm.api_key:
        missing.append("llm.api_key")
    if not cfg.llm.model:
        missing.append("llm.model")
    if missing:
        raise ConfigError(
            "DefendOps 是 LLM 驱动的 Agent，必须配置模型。"
            f"缺少：{', '.join(missing)}。请在 config/config.json 中补全。"
        )
