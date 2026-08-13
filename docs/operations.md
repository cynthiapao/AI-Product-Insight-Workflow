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
10. 将 `review_status` 改为 `approved` 后再合并；合并本身不等于发布到网站或社交平台。

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
- `No candidate met the selection threshold`：信息源当天质量偏低，可手动指定产品或临时调低 `min_score`。
- `Insufficient evidence`：候选页面无法访问或只有宣传文案；自动发现模式会继续尝试后续候选，手动模式则需要补充官网更新日志、测评或体验记录。
- 没有创建 Draft PR：若所有候选都证据不足，工作流会明确失败但仍上传运行 Artifact；否则检查仓库是否允许 Actions 创建 PR。
- `缺少必需截图`：打开 `inputs/assets/<slug>/README.md`，核对文件名、扩展名和上传分支，补齐后再次提交。
- `找不到可用字体`：GitHub 工作流应安装 `fonts-noto-cjk`；本地可给 `render-social` 增加 `--font` 指向微软雅黑或其他中文字体。
- 截图已上传但没有触发：确认文件提交在 `insight-draft/...` 草稿分支，而不是 `main`；也可用 Actions 页面手动重跑并输入 slug。
- 某个 RSS 失效：在 `config/sources.json` 暂时设为 `enabled: false`，替换后运行离线测试。

## 月度维护

- 检查信息源是否仍可访问。
- 查看 DeepSeek 官方模型名与价格是否变化。
- 抽查最近文章中“事实—来源”映射。
- 根据实际内容质量调整评分阈值，而不是增加更多 Agent。
