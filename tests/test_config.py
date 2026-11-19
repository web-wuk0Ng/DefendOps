"""配置层测试：无 key 必须报错，绝不降级。"""
import json
import tempfile
import unittest
from pathlib import Path

from defendops.config import load_config, validate_config, LLMConfig, AgentConfig, AppConfig
from defendops.exceptions import ConfigError


class TestConfig(unittest.TestCase):
    def test_load_real_config(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_file = Path(td) / "config.json"
            cfg_file.write_text(json.dumps({
                "llm": {"provider": "deepseek", "base_url": "https://api.deepseek.com/v1",
                        "api_key": "sk-test", "model": "deepseek-chat"},
                "agent": {"max_rounds": 5},
            }), encoding="utf-8")
            cfg = load_config(cfg_file)
            self.assertEqual(cfg.llm.model, "deepseek-chat")
            self.assertEqual(cfg.agent.max_rounds, 5)

    def test_missing_file_raises(self):
        with self.assertRaises(ConfigError):
            load_config("/nonexistent/path/config.json")

    def test_no_key_raises_no_fallback(self):
        cfg = AppConfig(
            llm=LLMConfig(base_url="https://api.deepseek.com/v1", api_key="", model="deepseek-chat"),
            agent=AgentConfig(),
        )
        with self.assertRaises(ConfigError) as ctx:
            validate_config(cfg)
        self.assertIn("api_key", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
