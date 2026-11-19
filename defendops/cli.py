"""DefendOps 命令行入口。

用法：
    python -m defendops doctor                       # 探活模型
    python -m defendops triage data/samples/alert.json   # 研判单条告警
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .agent import triage
from .config import load_config
from .exceptions import ConfigError, ModelUnavailableError
from .llm import LLMClient
from .models import Alert
from .tools import builtin_tools


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    print(f"[*] Provider : {cfg.llm.provider}")
    print(f"[*] Model    : {cfg.llm.model}")
    print(f"[*] Base URL : {cfg.llm.base_url}")
    print("[*] 探活中...")
    llm = LLMClient(cfg)
    if llm.probe():
        print("[+] 模型可用")
        return 0
    print("[-] 模型不可用：请检查 base_url / api_key / model。DefendOps 不做离线降级。", file=sys.stderr)
    return 1


def cmd_triage(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    raw = json.loads(Path(args.alert).read_text(encoding="utf-8"))
    alert = Alert.from_dict(raw)
    llm = LLMClient(cfg)
    registry = builtin_tools()
    verdict = triage(alert, llm, registry, max_rounds=cfg.agent.max_rounds)
    out = verdict.to_dict()
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"[+] 研判结果已写入 {args.output}")
    else:
        print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="defendops", description="LLM 驱动的蓝队告警研判 Agent")
    parser.add_argument("--version", action="version", version=f"DefendOps {__version__}")
    parser.add_argument("--config", help="配置文件路径，默认 config/config.json")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="探活模型可用性").set_defaults(func=cmd_doctor)

    p_triage = sub.add_parser("triage", help="研判一条告警")
    p_triage.add_argument("alert", help="告警 JSON 文件路径")
    p_triage.add_argument("-o", "--output", help="研判结果输出文件（默认打印到 stdout）")
    p_triage.set_defaults(func=cmd_triage)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, ModelUnavailableError) as exc:
        print(f"[-] {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"[-] 文件不存在：{exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"[-] JSON 解析失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
