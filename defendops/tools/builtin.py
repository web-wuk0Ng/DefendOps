"""内置研判工具。确定性、无副作用，供 LLM 自主调用做取证。

注意：这些是「能力端点」，不是规则兜底——用不用、怎么用完全由 LLM 决定。
"""
from __future__ import annotations

import ipaddress
import re
from typing import Any

from .base import Tool, ToolRegistry

_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_DOMAIN = re.compile(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b")
_SHA256 = re.compile(r"\b[a-fA-F0-9]{64}\b")
_MD5 = re.compile(r"\b[a-fA-F0-9]{32}\b")

# 演示用的本地情报样本。真实部署应替换为威胁情报 API（MCP 端点）。
_LOCAL_INTEL: dict[str, dict[str, Any]] = {
    "185.220.101.7": {"verdict": "malicious", "tags": ["tor-exit", "ssh-bruteforce"], "source": "local-demo"},
    "45.155.205.233": {"verdict": "malicious", "tags": ["known-scanner"], "source": "local-demo"},
    "evil-example.xyz": {"verdict": "malicious", "tags": ["c2", "phishing"], "source": "local-demo"},
}


def extract_iocs(text: str) -> dict[str, Any]:
    """从文本中提取 IOC（IPv4、域名、MD5、SHA256），去重后分类返回。"""
    iocs = {
        "ipv4": sorted(set(_IPV4.findall(text))),
        "domains": sorted({d.lower() for d in _DOMAIN.findall(text)}),
        "md5": sorted(set(_MD5.findall(text))),
        "sha256": sorted(set(_SHA256.findall(text))),
    }
    return {"count": sum(len(v) for v in iocs.values()), "iocs": iocs}


def check_intel(indicator: str) -> dict[str, Any]:
    """在本地情报库查询单个 IOC（IP / 域名 / 哈希）。命中返回标签，未命中返回 unknown。"""
    key = indicator.strip().lower()
    hit = _LOCAL_INTEL.get(key)
    if hit:
        return {"indicator": key, "found": True, **hit}
    return {"indicator": key, "found": False, "verdict": "unknown", "source": "local-demo"}


def is_private_ip(ip: str) -> dict[str, Any]:
    """判断 IP 是否为私有 / 保留地址，用于区分内网资产与外部攻击源。"""
    try:
        addr = ipaddress.ip_address(ip.strip())
        return {"ip": ip, "private": addr.is_private, "global": addr.is_global, "version": addr.version}
    except ValueError as exc:
        return {"ip": ip, "error": f"非法 IP：{exc}"}


def builtin_tools() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(Tool(
        name="extract_iocs",
        description="从告警原始文本/字段中提取 IOC：IPv4、域名、MD5、SHA256。用于快速定位攻击指标。",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string", "description": "要分析的原始文本"}},
            "required": ["text"],
        },
        handler=extract_iocs,
    ))
    registry.register(Tool(
        name="check_intel",
        description="查询单个 IOC（IP/域名/哈希）在本地威胁情报库的记录，返回恶意判定与标签。",
        parameters={
            "type": "object",
            "properties": {"indicator": {"type": "string", "description": "待查询的 IOC"}},
            "required": ["indicator"],
        },
        handler=check_intel,
    ))
    registry.register(Tool(
        name="is_private_ip",
        description="判断 IP 是否为内网/保留地址，帮助区分受保护资产与外部攻击源。",
        parameters={
            "type": "object",
            "properties": {"ip": {"type": "string", "description": "待判断的 IPv4/IPv6 地址"}},
            "required": ["ip"],
        },
        handler=is_private_ip,
    ))
    return registry
