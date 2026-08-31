# 运行与维护手册

## 每周的人工动作

1. 打开自动创建的 Draft Pull Request。
2. 先看 `run-report.json` 是否存在来源失败或证据不足。
3. 核对文章里的事实是否能在来源页面找到。
4. 删除没有证据支撑的判断，补充自己的真实体验。
5. 检查标题是否克制、正文是否约 5 分钟、方法论是否有适用边界。
6. 查看 `inputs/assets/<slug>/README.md`，按固定文件名准备真实截图并隐藏敏感信息。
7. 在 Draft PR 的 `insight-draft/...` 分支中进入对应截图目录，选择 `Add file → Upload files` 并提交。
8. 等待 `Render social assets after screenshot upload` 完成，检查 `output/social/<slug>/rendered/` 中的 X 横图和小红书轮播图。
9. 检查 X 英文正文不超过 280 字符，并用 2–4 个短段落形成阅读节奏；小红书正文约 300–500 字，保留真实经历、摩擦和判断过程；轮播图不能只有口号，配图与文章判断一致。
10. 人工确认正文后运行 `approve --article ...`：系统把 `review_status` 改为 `approved`，并将 Markdown/JSON 从 `output/drafts/` 移到 `output/reviewed/`。普通 PR 合并只表示仓库变更通过；只有完成这一步的文章 PR 合并，才表示内容审核通过。网站与社交平台发布仍是独立步骤。

## 修复分支验证（不创建文章 PR）

- 在 Actions → `Generate AI product insight draft` → `Run workflow` 选择修复分支，勾选 `validation_only`。产品参数留空测试自动发现；填写产品参数则测试指定产品。
- 该模式仍调用 DeepSeek 并生成文章 / 社交草稿，但只上传 Artifact，不推送草稿分支、不创建文章 PR、不发布网站。用于避免验证用的文章 PR 混入尚未合并的代码修复。
- 正式生成文章时选择 `main`，不要勾选 `validation_only`。
- 只想检查采集、不调用模型：运行 `python scripts/check_research_sources.py --archive <失败运行的zip>`。结果中的 `usable_source_mix` 仅表示来源组合满足要求，最终能否写作还需 Research 模型评估。
- 代码 PR 会自动运行 `Test insight workflow`，无需 DeepSeek Secret。

## 截图上传规则

- 必须使用 README 清单中的文件名，否则工作流会按“缺少截图”处理。
- 优先截取能证明文章判断的界面状态，不使用与正文无关的装饰图。
- 本人网站与操作过程标记为 `personal`；讨论对象产品的真实界面标记为 `product`。
- 上传前检查头像、邮箱、账号、API Key、私人对话、客户信息和浏览器书签。
- 截图提交后会自动续跑；不需要重新运行文章生成工作流。
- 小红书截图页也要用简短说明指出“这张图证明什么”；观点页通常应有 60–180 字，不能为了适配模板把内容压缩成一句口号。
- 如果只想重跑配图，可在 Actions 中选择 `Render social assets after screenshot upload`，选中当前草稿分支并输入文章 slug。

## 失败排查

- `DEEPSEEK_API_KEY is required`：检查 GitHub Secret 名称是否完全一致。
- `No candidate met the selection threshold`：信息源当天质量偏低，可手动指定更适合的产品；先检查候选和评分，不为保证产出而降低门槛。
- `Insufficient evidence`：查看错误后缀判断具体缺口。`missing official or release evidence` 表示官网、文档或更新页没有成功抓取；`missing independent community or report evidence` 表示暂未找到 Hacker News 讨论或独立报道。自动发现模式最多继续研究 `research_candidate_limit` 个达到评分阈值的候选，手动模式则需要补充官网更新日志、测评或体验记录。
- 没有创建 Draft PR：若所有候选都证据不足，工作流会明确失败但仍上传运行 Artifact；否则检查仓库是否允许 Actions 创建 PR。
- `official URL unresolved`：发现入口无法解析出可核对的官网；Product Hunt 的 403 不应通过不断重试或把其摘要标成官方证据解决。
- `identity mismatch`：同名结果的用途不一致，或指向另一个产品；这是主动排除错误来源。不要手工改成可用来凑足数量。
- `no substantive non-author comments`：帖子只有作者介绍、短反馈或数量指标，不能算独立材料。新闻标题也不等于报道正文。
- `Process completed with exit code 1`：查看其前面的 `run-report.json` / errors。这只是没有产出的退出码，不是具体原因。更细的采集问题保存在 `03-research-*.json` 的 `collection_diagnostics` 中。
- `缺少必需截图`：打开 `inputs/assets/<slug>/README.md`，核对文件名、扩展名和上传分支，补齐后再次提交。
- `找不到可用字体`：GitHub 工作流应安装 `fonts-noto-cjk`；本地可给 `render-social` 增加 `--font` 指向微软雅黑或其他中文字体。
- 截图已上传但没有触发：确认文件提交在 `insight-draft/...` 草稿分支，而不是 `main`；也可用 Actions 页面手动重跑并输入 slug。
- 某个 RSS 失效：在 `config/sources.json` 暂时设为 `enabled: false`，替换后运行离线测试。

## 月度维护

- 检查信息源是否仍可访问。
- 查看 DeepSeek 官方模型名与价格是否变化。
- 抽查最近文章中“事实—来源”映射。
- 抽查 Hacker News/新闻搜索是否匹配到同名但无关的产品；自动相关性过滤不能替代人工核对。
- 根据实际内容质量调整评分阈值，而不是增加更多 Agent。

## 自动研究的证据结构

- 定时模式不会因为凑满两条链接就继续写作；至少需要一条官方/发布材料和一条社区/报道材料。
- 官方材料包括产品主页面，以及主页面中可发现的同域文档、功能说明、更新日志或发布说明。
- 独立材料优先使用指向同一产品的 Hacker News 讨论中的非作者实质评论；没有匹配时再查询 Google News RSS 并尝试抓取实际报道。RSS 标题和摘要本身不算独立报道。
- Product Hunt RSS 外链优先解析官网；跳转失败再核实 HN 外链。官网不明或名称 / 用途不符时保留证据缺口，不猜域名。GitHub 项目优先读取 README，避免导航文字挤占证据。
- Scout 仍给出最多 3 个首选产品，但研究阶段会保留达到评分阈值的后续候选，并按顺序尝试至 `research_candidate_limit`。生成第一篇可用草稿后即停止。
- 网页摘录只作为不可信证据输入，不能改变 Agent 指令；抓取器拒绝本地/私有地址，并限制单个响应体大小。
- 增加候选回退和外部材料后，定时任务可能比原来多运行几分钟，这是证据完整性带来的预期成本。
- 当前仍是有限的规则式身份核验；无法覆盖所有同名品牌、新闻跳转和官网 / 仓库别名。DNS 检查也不等同于连接层 IP 固定；生产部署应保留网络隔离。人工审核仍需核对事实与引用。
