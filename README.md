# AI 产品洞察自动化工作流

这是一个面向个人作品集网站的内容工作流 MVP。它每周从公开信息源发现候选产品，也允许手动指定产品；经过顺序式多 Agent 分析后，输出约 5 分钟的中文文章草稿。所有内容默认是 `draft`，必须人工审核后才能发布。

## 工作流

```text
公开信息源 / 手动指定
        ↓
Discovery Agent：采集、归一化、去重
        ↓
Scout Agent：相关性、新颖性、产品深度、证据评分
        ↓
Research Agent：整理事实、来源和待确认问题
        ↓
Insight Agent：核心机制、有效原因、边界、方法论
        ↓
Editor Agent：生成 5 分钟中文结构化草稿
        ↓
Markdown + JSON + 网站卡片 HTML
        ↓
Draft Pull Request → 人工审核 → 合并发布
```

## 为什么没有直接照搬 PDF 中的代码

方案保留了 PDF 的关键设计：顺序式多 Agent、结构化 Schema、模型路由边界和人工审核。MVP 没有把 CrewAI 设为硬依赖，而是用很薄的 Python 编排层实现相同角色和顺序，原因是：

- GitHub Actions 安装更快、依赖更少；
- 每个阶段都能离线测试和单独重跑；
- DeepSeek 接口、信息源和未来视觉模型都可以独立替换；
- 对于 4 个固定顺序步骤，引入大型 Agent 框架暂时不会增加实际能力。

后续若需要并行研究、长任务恢复或更复杂的人机节点，可把 `AgentCrew` 替换为 CrewAI Flow，现有 Pydantic 数据契约无需变化。

## 本地快速验证

要求 Python 3.11+。

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
python -m ai_product_insight offline-demo
```

离线演示不会访问网络或调用 DeepSeek。成功后会生成：

- `output/drafts/*.md`：尚未完成人工复核的自动文章草稿；
- `output/reviewed/*.md`：已经人工复核的文章；文件仍以 frontmatter 中的 `review_status` 决定能否正式发布；
- `output/drafts/*.json`：后续自动接入网站的数据；
- `output/drafts/*.card.html`：可复制进当前首页的洞察卡片；
- `data/runs/<run-id>/`：每个 Agent 的中间结果与运行报告。

## 使用 DeepSeek

程序只从环境变量读取 Key，不读取也不提交 `.env`。

```powershell
$env:DEEPSEEK_API_KEY="你的 Key"
python -m ai_product_insight scheduled
```

手动指定产品：

```powershell
python -m ai_product_insight manual `
  --name "产品名称" `
  --url "https://product.example.com" `
  --notes "你自己的体验或观察"
```

手动生成多产品对比文章：

```powershell
python -m ai_product_insight compare `
  --name "用四个 AI 模型制作个人网站：它们分别适合做什么？" `
  --product "Gemini" "Gemini 官方页面 URL" `
  --product "Codex & ChatGPT" "OpenAI 官方页面 URL" `
  --product "Claude" "Claude 官方页面 URL" `
  --product "DeepSeek" "DeepSeek 官方页面 URL" `
  --notes-file "inputs\ai-model-comparison-notes.md"
```

`compare` 接受 2-6 组 `--product "名称" "主要官方 URL"`。程序会分别研究每个产品，再结合 `--notes-file` 中的个人体验生成一篇对比草稿。体验记录用于第一人称观察，不会被当作产品事实；对比模式仍然保留人工审核。

本地交互终端中，研究完成后 DeepSeek 会进行一次编辑追问，最多 3 个问题。回答会保存到本次运行的 `03-clarification.json`，并进入后续分析和写作。若需要完全自动运行，可添加 `--no-clarify`。

编辑规范位于 `config/`，人工确认的输入/输出范例位于 `examples/gold/`。每组范例使用相同文件名前缀的 `.input.json` 和 `.output.json`；工作流会自动加载目录中的全部成对范例，供 Insight 与 Editor 学习结构、证据边界和语言密度，但禁止复制范例中的产品事实和结论。

预览并发布审核后的文章到现有静态网站：

```powershell
python -m ai_product_insight publish `
  --article "output\reviewed\article-slug.md" `
  --site "D:\桌面\简历-鲍康昕\项目内容"
```

命令先在 `output/previews/` 生成页面并打开浏览器，不修改网站。检查内容和样式后，在终端输入 `PUBLISH`，程序才会把文章标记为 `approved`、生成 `insights/<slug>.html`、更新首页卡片，并只提交这些相关文件后推送当前 Git 分支。调试时可使用 `--no-open` 或 `--no-push`。

默认模型和信息源位于 `config/sources.json`。当前采用分阶段模型路由：Discovery/Scout/Research 使用 `deepseek-v4-flash`，Insight/Editor 使用 `deepseek-v4-pro`。前者负责高频筛选与资料整理，后者负责观点提炼、结构判断和最终成文。

## 接入 GitHub

1. 建议将本工作流保存为独立私有仓库；审核后的文章由 `publish` 命令写入现有个人网站仓库。
2. 在仓库 `Settings → Secrets and variables → Actions` 新建 `DEEPSEEK_API_KEY`。
3. 在 `Settings → Actions → General → Workflow permissions` 开启读写权限，并允许 GitHub Actions 创建 Pull Request。
4. 在 Actions 页面手动运行一次 `Generate AI product insight draft`。
5. 检查生成的 Draft Pull Request；核验事实、来源和表达后再合并。

GitHub Actions 当前配置为每周一北京时间 09:20 运行。每次成功运行会创建独立草稿分支和 Draft Pull Request，文章仍需人工修改与核验后才能进入发布流程。

## 与现有网站连接

当前项目与网站代码解耦。第一阶段建议先验证 2-3 篇草稿的质量；验证通过后，再增加一个小型同步脚本：把审核后的 JSON 渲染成独立文章 HTML，并更新现有 `index.html` 的 `AI 产品洞察` 卡片列表。

## 安全边界

- 禁止把 `DEEPSEEK_API_KEY` 写入仓库、HTML 或浏览器端 JavaScript。
- 自动化只创建草稿，不直接发布。
- 所有文章必须保留来源，区分事实、推断和个人判断。
- 公开信息抓取遵守站点条款、robots 规则和合理请求频率。

## 当前验证状态

- [x] 单元测试通过
- [x] 离线端到端演示通过
- [x] 生成文件人工检查通过
- [x] GitHub Actions 关键结构与密钥引用检查完成
- [ ] 使用真实 DeepSeek Key 试运行
