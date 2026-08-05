# 运行与维护手册

## 每两周的人工动作

1. 打开自动创建的 Draft Pull Request。
2. 先看 `run-report.json` 是否存在来源失败或证据不足。
3. 核对文章里的事实是否能在来源页面找到。
4. 删除没有证据支撑的判断，补充自己的真实体验。
5. 检查标题是否克制、正文是否约 5 分钟、方法论是否有适用边界。
6. 将 `review_status` 改为 `approved` 后再合并。

## 失败排查

- `DEEPSEEK_API_KEY is required`：检查 GitHub Secret 名称是否完全一致。
- `No candidate met the selection threshold`：信息源当天质量偏低，可手动指定产品或临时调低 `min_score`。
- `Insufficient evidence`：候选页面无法访问或只有宣传文案；补充官网更新日志、测评或手动体验记录。
- 没有创建 Draft PR：先从 Artifact 下载草稿，再检查仓库是否允许 Actions 创建 PR。
- 某个 RSS 失效：在 `config/sources.json` 暂时设为 `enabled: false`，替换后运行离线测试。

## 月度维护

- 检查信息源是否仍可访问。
- 查看 DeepSeek 官方模型名与价格是否变化。
- 抽查最近文章中“事实—来源”映射。
- 根据实际内容质量调整评分阈值，而不是增加更多 Agent。

