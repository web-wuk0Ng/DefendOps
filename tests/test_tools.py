"""工具层测试（unittest，零第三方测试依赖）。"""
import unittest

from defendops.tools.builtin import builtin_tools


class TestTools(unittest.TestCase):
    def setUp(self):
        self.registry = builtin_tools()

    def test_registry_schemas(self):
        schemas = self.registry.schemas()
        self.assertEqual({"extract_iocs", "check_intel", "is_private_ip"}, set(self.registry.names()))
        self.assertTrue(all(s["type"] == "function" for s in schemas))

    def test_extract_iocs(self):
        result = self.registry.call("extract_iocs", {"text": "src 185.220.101.7 hit evil-example.xyz"})
        self.assertIn("185.220.101.7", result["iocs"]["ipv4"])
        self.assertIn("evil-example.xyz", result["iocs"]["domains"])

    def test_check_intel_hit_and_miss(self):
        hit = self.registry.call("check_intel", {"indicator": "185.220.101.7"})
        self.assertTrue(hit["found"] and hit["verdict"] == "malicious")
        miss = self.registry.call("check_intel", {"indicator": "1.2.3.4"})
        self.assertFalse(miss["found"])

    def test_private_ip(self):
        self.assertTrue(self.registry.call("is_private_ip", {"ip": "10.0.2.15"})["private"])
        self.assertTrue(self.registry.call("is_private_ip", {"ip": "8.8.8.8"})["global"])
        self.assertIn("error", self.registry.call("is_private_ip", {"ip": "not-an-ip"}))

    def test_unknown_tool_returns_error(self):
        self.assertIn("error", self.registry.call("nope", {}))


if __name__ == "__main__":
    unittest.main()
