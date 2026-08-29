# Research Evidence Reliability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让每周自动选题在不降低证据标准的前提下，自动补充官方与独立来源，并在首选产品不可写时继续研究后续候选。

**Architecture:** 新增一个独立的证据采集模块，负责主页面、同域官方关联页、Hacker News 和新闻 RSS；`ResearchAgent` 只负责把采集结果交给模型判断。定时模式增加证据组合校验，Scout 保留更多达到阈值的回退候选，Pipeline 沿用“首篇成功后停止”的行为。

**Tech Stack:** Python 3.12、标准库 `urllib`/`html.parser`/`xml.etree`、Pydantic、unittest、GitHub Actions。

---

### Task 1: 固化失败场景与证据组合规则

**Files:**
- Create: `tests/test_research_evidence.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_scout_response.py`

**Step 1:** 编写失败测试，覆盖同域官方链接发现、独立来源收集、私有地址拒绝、定时模式缺少独立来源时跳过，以及超过 3 个候选后仍能回退。

**Step 2:** 运行对应测试，确认新行为尚未实现。

### Task 2: 实现安全的多源证据采集

**Files:**
- Create: `src/ai_product_insight/research.py`
- Modify: `src/ai_product_insight/sources.py`
- Modify: `src/ai_product_insight/agents.py`
- Modify: `src/ai_product_insight/prompts.py`

**Step 1:** 实现页面正文与同域研究链接提取、Hacker News 搜索和新闻 RSS 回退。

**Step 2:** 为公开 URL、响应大小、去重和相关性增加边界检查。

**Step 3:** 让 `ResearchAgent` 在没有 fixture 时使用采集器，并在定时模式检查官方与独立来源是否齐全。

**Step 4:** 运行研究层测试，确认通过。

### Task 3: 扩大候选回退并改进诊断

**Files:**
- Modify: `src/ai_product_insight/config.py`
- Modify: `config/sources.json`
- Modify: `src/ai_product_insight/agents.py`
- Modify: `src/ai_product_insight/pipeline.py`

**Step 1:** 新增 `research_candidate_limit`，保留模型首选顺序并追加达到阈值的候选。

**Step 2:** 定时 Pipeline 把证据缺口写入运行报告，成功生成第一篇后停止。

**Step 3:** 运行 Pipeline 与 Scout 测试。

### Task 4: 文档与完整验证

**Files:**
- Modify: `docs/operations.md`
- Modify: `docs/development-log.md`
- Create: `docs/adr/0001-collect-mixed-research-evidence.md`

**Step 1:** 记录新研究逻辑、失败排查方法、请求成本和边界。

**Step 2:** 运行完整测试套件。

**Step 3:** 使用固定 HTML/JSON fixture 做一次不访问真实网络的 scheduled 端到端验证，确认有草稿时返回成功、全部不足时返回失败。


