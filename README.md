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
Social Repurpose Agent：改写 X / 小红书文案并提出截图清单
        ↓
文章文件 + 社交草稿 + 截图上传目录
        ↓
Draft Pull Request → 人工上传截图 → 自动生成配图 → 人工审核
```

## 方案选型：为什么采用轻量的顺序工作流

这套系统现阶段要解决的，不是让多个 Agent 自由讨论，而是稳定地产出一篇值得人工继续打磨的产品洞察草稿。内容生产本身存在明确依赖：先发现值得研究的产品，再核验证据、形成判断，最后按统一结构成稿。因此，MVP 选择让四个角色依次交接，而没有一开始就引入复杂的自治编排。

- 每个 Agent 只负责一种判断，并通过 Pydantic Schema 交付结构化结果，方便定位问题和追溯依据；
- Scout、Research 优先使用速度快、成本低的模型，Insight、Editor 和 Social Repurpose 使用能力更强的模型，把预算集中在真正影响内容质量的环节；
- 公开事实与个人判断分开处理，证据不足时继续尝试下一候选或停止生成，不为了更新频率牺牲可信度；
- 自动化最终只创建 Draft Pull Request，发布权仍留给人，工作流提高效率但不替代编辑判断。

轻量 Python 编排也让信息源、模型和各个 Agent 可以独立替换。未来如果出现并行研究、长任务恢复或更复杂的人机协作需求，再引入 CrewAI Flow 等框架；现有的数据契约和审核机制可以继续沿用。

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
- `output/social/<slug>/social.json`：X、小红书、轮播结构与截图要求的结构化数据；
- `output/social/<slug>/x-post.md`：不超过 280 字符的英文 X 草稿；
- `output/social/<slug>/xiaohongshu.md`：中文小红书正文与轮播提纲；
- `inputs/assets/<slug>/README.md`：人工截图清单与固定文件名；
- `data/runs/<run-id>/`：每个 Agent 的中间结果与运行报告。

## 人工截图节点与社交配图

每篇文章生成后，工作流会在同一个 Draft PR 中创建 `inputs/assets/<slug>/`，其中的 README 会说明要截取哪个页面、哪个区域，以及图片用于 X 还是小红书。请在 GitHub 上切换到该 PR 的 `insight-draft/...` 分支，进入对应目录并通过 `Add file → Upload files` 上传截图。文件名必须与清单一致，上传前需要自行隐藏账号、密钥和私人消息。

截图提交会触发 `.github/workflows/render-social-assets.yml`。它先检查必需截图，再生成 `output/social/<slug>/rendered/x-card.png` 和 `xhs-01.png` 等轮播图片，最后把图片提交回原草稿分支并在 Draft PR 留言。缺少截图时只报告具体文件名，不会生成不完整图片，也不会自动发布。

本地也可以执行同样的渲染：

```powershell
python -m ai_product_insight render-social `
  --bundle "output\social\article-slug\social.json" `
  --assets "inputs\assets\article-slug" `
  --output "output\social\article-slug\rendered"
```

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

默认模型和信息源位于 `config/sources.json`。当前采用分阶段模型路由：Discovery/Scout/Research 使用 `deepseek-v4-flash`，Insight/Editor/Social Repurpose 使用 `deepseek-v4-pro`。前者负责高频筛选与资料整理，后者负责观点提炼、结构判断、最终成文和平台改写。

## 接入 GitHub

1. 建议将本工作流保存为独立私有仓库；审核后的文章由 `publish` 命令写入现有个人网站仓库。
2. 在仓库 `Settings → Secrets and variables → Actions` 新建 `DEEPSEEK_API_KEY`。
3. 在 `Settings → Actions → General → Workflow permissions` 开启读写权限，并允许 GitHub Actions 创建 Pull Request。
4. 在 Actions 页面手动运行一次 `Generate AI product insight draft`。
5. 检查生成的 Draft Pull Request，并按 `inputs/assets/<slug>/README.md` 上传真实截图。
6. 等待 `Render social assets after screenshot upload` 更新同一个 PR，检查 X 与小红书配图。
7. 核验事实、来源、表达、截图隐私和视觉效果后再合并。

GitHub Actions 当前配置为每周一北京时间 09:20 运行。Scout 会按优先级保留最多 3 个候选；若首选证据不足，流程会继续研究下一候选，并在生成第一篇草稿后停止。只有实际产生 Markdown 草稿时才会创建独立草稿分支和 Draft Pull Request；文章仍需人工修改与核验后才能进入发布流程。

## 与现有网站连接

当前项目与网站代码解耦。第一阶段建议先验证 2-3 篇草稿的质量；验证通过后，再增加一个小型同步脚本：把审核后的 JSON 渲染成独立文章 HTML，并更新现有 `index.html` 的 `AI 产品洞察` 卡片列表。

## 安全边界

- 禁止把 `DEEPSEEK_API_KEY` 写入仓库、HTML 或浏览器端 JavaScript。
- 自动化只创建草稿，不直接发布。
- 截图由人选择并上传；程序不会自动登录产品或抓取受限页面。
- 上传前必须检查截图中的账号、密钥、私人对话和其他敏感信息。
- 所有文章必须保留来源，区分事实、推断和个人判断。
- 公开信息抓取遵守站点条款、robots 规则和合理请求频率。

## 当前验证状态

- [x] 单元测试通过
- [x] 离线端到端演示通过
- [x] 生成文件人工检查通过
- [x] GitHub Actions 关键结构与密钥引用检查完成
- [ ] 使用真实 DeepSeek Key 试运行
