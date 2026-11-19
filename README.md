# DefendOps

**LLM 驱动的蓝队告警研判 Agent。**

对标红队 `PentestCrew`，DefendOps 是防守侧的智能体：一条告警进来，Agent 自己决定需要哪些证据、调用工具取证、再推理出「真实攻击 / 误报 / 需人工复核」的结构化结论与处置建议。

> 设计原则：**能用大模型就用，尽量少写固定脚本。** 无模型直接报错，不提供离线规则降级。

## 当前能力

- **告警研判（Alert Triage）**——首个落地场景。输入一条告警 JSON，输出结构化研判结论。
- **ReAct 闭环**——观察告警 → LLM 规划 → 调用工具取证 → 再推理 → 收敛结论，最多 N 轮。
- **工具即端点**——工具按 JSON Schema 注册，LLM 运行时自主发现并决定是否调用；引擎不硬编码调用顺序。
- **证据可追溯**——每次工具调用、每条推理轨迹都记录进结论，便于审计与复盘。

## 架构

```
defendops/
├── cli.py              # 命令行入口（doctor / triage）
├── config.py           # 配置加载与校验（无 key 即报错）
├── llm.py              # OpenAI 兼容 LLM 客户端（探活 / 调用 / 失败抛错）
├── models.py           # Alert / Verdict / Evidence 数据模型
├── tools/              # 工具层
│   ├── base.py         # Tool + ToolRegistry（schema 注册与分发）
│   └── builtin.py      # 内置取证工具（IOC 提取 / 情报查询 / 内外网判断）
└── agent/              # ReAct 研判引擎
    ├── state.py        # Agent 状态与轨迹
    ├── prompts.py      # 系统提示词 + 结论 schema
    └── graph.py        # triage()：观察→规划→工具→推理→结论
```

研判一次完整流程（`triage` 的真实输出，来自示例告警）：

1. Agent 提取告警里的 IOC → 得到 `185.220.101.7` 与内网 `10.0.2.15`
2. 查本地情报 → 该 IP 命中 `tor-exit / ssh-bruteforce`
3. 判断内外网 → 攻击源公网、目标内网资产
4. 输出结论：`true_positive / high / confidence 0.93` + 6 条处置建议

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置模型

```bash
cp config/config.example.json config/config.json
# 编辑 config/config.json，填入 base_url / api_key / model
```

默认用 DeepSeek，可换成任意 OpenAI 兼容服务（通义、Kimi、智谱、混元、Ollama 等），只需改 `base_url`、`api_key`、`model`。

> `config/config.json` 已在 `.gitignore`，密钥不会入库。

```json
{
  "llm": {
    "provider": "deepseek",
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "sk-...",
    "model": "deepseek-chat",
    "temperature": 0.1,
    "timeout": 60,
    "max_retries": 2
  },
  "agent": { "max_rounds": 8, "language": "zh-CN" }
}
```

### 3. 探活 + 研判

```bash
python -m defendops doctor                          # 确认模型可用
python -m defendops triage data/samples/alert.json  # 研判示例告警
python -m defendops triage alert.json -o verdict.json
```

## 测试

测试用假 LLM 跑通整个 ReAct 闭环，不依赖网络或密钥：

```bash
python -m unittest discover -s tests -v
```

CI（GitHub Actions）会在每次 push / PR 自动跑编译检查与全量测试。

## 路线图

- [ ] 更多工具端点：资产库查询、日志检索、情报 API（MCP 端点化）
- [ ] 批量告警研判与聚合（告警降噪 / 关联分析）
- [ ] Web 工作台（实时轨迹 + 结论审阅）
- [ ] 结论落库与研判知识沉淀

## 命名

`DefendOps` = Defend + Ops，防守运营。与红队 `PentestCrew` 攻守对应。
