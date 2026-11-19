"""用假 LLM 跑通 ReAct 闭环，无需联网。"""
import json
import unittest
from types import SimpleNamespace

from defendops.agent.graph import triage, _extract_json
from defendops.config import AppConfig, LLMConfig, AgentConfig
from defendops.models import Alert
from defendops.tools import builtin_tools


class FakeLLM:
    """按序返回：先调一次工具，再给结论。"""

    def __init__(self, cfg):
        self.calls = 0

    def chat(self, messages, tools=None, response_format=None):
        self.calls += 1
        if self.calls == 1:
            call = SimpleNamespace(
                id="call_1",
                function=SimpleNamespace(name="check_intel",
                                         arguments='{"indicator": "185.220.101.7"}'),
            )
            return SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(tool_calls=[call], content=None))])
        verdict = {
            "disposition": "true_positive", "severity": "high", "confidence": 0.92,
            "summary": "确认 SSH 暴力破解，源 IP 为已知恶意 Tor 出口",
            "rationale": "185.220.101.7 命中本地情报，5 分钟内 87 次 root 登录失败",
            "recommended_actions": ["封禁源 IP", "禁用 root 远程登录", "检查 web-prod-01 登录日志"],
        }
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(tool_calls=None, content=json.dumps(verdict, ensure_ascii=False)))])


class TestAgent(unittest.TestCase):
    def test_react_loop_with_tool(self):
        cfg = AppConfig(llm=LLMConfig(), agent=AgentConfig())
        alert = Alert.from_dict({"id": "T-1", "title": "SSH brute force",
                                 "raw": {"src_ip": "185.220.101.7"}})
        verdict = triage(alert, FakeLLM(cfg), builtin_tools(), max_rounds=5)
        self.assertEqual(verdict.disposition, "true_positive")
        self.assertEqual(verdict.severity, "high")
        self.assertEqual(verdict.confidence, 0.92)
        self.assertEqual(len(verdict.evidence), 1)
        self.assertEqual(verdict.evidence[0].tool, "check_intel")
        self.assertEqual(verdict.evidence[0].result["verdict"], "malicious")
        self.assertIn("封禁源 IP", verdict.recommended_actions)
        self.assertTrue(any("工具" in t for t in verdict.trace))

    def test_extract_json_handles_code_fence(self):
        raw = '```json\n{"disposition": "false_positive", "confidence": 0.3}\n```'
        self.assertEqual(_extract_json(raw)["disposition"], "false_positive")


if __name__ == "__main__":
    unittest.main()
