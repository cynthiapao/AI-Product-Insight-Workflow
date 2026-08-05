import json
import tempfile
import unittest
from pathlib import Path

from ai_product_insight.publishing import (
    approve_markdown,
    parse_article_markdown,
    publish_to_site,
    render_preview,
)


ARTICLE = '''---
title: "AI 让我做出了网站，但离想要的样子还有多远？"
slug: "ai-built-my-website"
summary: "AI 降低了建站门槛，但把模糊审美翻译成精确设计语言，仍然需要人的判断和持续投入。"
read_minutes: 5
tags: "AI 建站 / 产品洞察"
review_status: "draft"
generated_at: "2026-07-20T00:00:00+00:00"
---

# AI 让我做出了网站，但离想要的样子还有多远？

## 一句话看懂

AI 让我跨过了从零到一，但没有自动完成从“能用”到“符合个人审美”的最后一段路。

## 核心体验

我提供了一张并非网站截图的设计参考，模型仍然生成了一版让我满意的网页初稿。

| 比较维度 | Lovable | Codex |
| --- | --- | --- |
| 如何开始 | 视觉选择题 | 已有代码与明确修改 |
| 更适合 | 设计冷启动 | 持续开发 |

## 为什么有效

视觉参考降低了意图翻译成本，也给模型提供了比抽象形容词更稳定的设计锚点。

## 问题与边界

当设计进入细节调整，模糊语言很难精确控制间距、线条和层级。

## 我的判断

真正的门槛正在从会不会写代码，转向能不能把感觉表达成可执行的设计语言。

## 可迁移的方法

### 1. 先提供视觉锚点

用参考图帮助模型理解方向。

**适用场景：** 视觉设计任务。

## 产品启示

AI 产品需要帮助用户表达需求，而不是等待用户先掌握专业语言。

## 信息来源

- [个人建站记录](https://example.com/notes)（manual）
'''


SITE_INDEX = '''<!doctype html><html><body><section id="insights"><div class="insight-list">
<article class="insight-item"><h3>已有手工卡片</h3></article>
</div></section></body></html>'''


class PublishingTests(unittest.TestCase):
    def test_preview_does_not_mutate_site_and_publish_updates_generated_block(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            article_path = root / "article.md"
            site = root / "site"
            preview = root / "preview"
            site.mkdir()
            article_path.write_text(ARTICLE, encoding="utf-8")
            (site / "index.html").write_text(SITE_INDEX, encoding="utf-8")
            (site / "style.css").write_text(":root { --accent: #0066ff; }", encoding="utf-8")

            article = parse_article_markdown(article_path)
            preview_path = render_preview(article, site, preview)

            self.assertTrue(preview_path.is_file())
            preview_html = preview_path.read_text(encoding="utf-8")
            self.assertIn(article.summary, preview_html)
            self.assertIn('<table class="insight-compare-table">', preview_html)
            self.assertIn('<th scope="row">如何开始</th>', preview_html)
            self.assertIn("Product Insight", preview_html)
            self.assertIn("AI 产品需要帮助用户表达需求", preview_html)
            self.assertNotIn("| 比较维度 |", preview_html)
            self.assertFalse((site / "insights").exists())

            approve_markdown(article_path)
            approved = parse_article_markdown(article_path)
            changed = publish_to_site(approved, site)

            self.assertEqual(approved.review_status, "approved")
            self.assertTrue((site / "insights" / "ai-built-my-website.html").is_file())
            self.assertTrue((site / "insights" / "insight.css").is_file())
            manifest = json.loads((site / "insights" / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest[0]["slug"], "ai-built-my-website")
            homepage = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn("AUTO-GENERATED-INSIGHTS:START", homepage)
            self.assertIn('href="insights/ai-built-my-website.html"', homepage)
            self.assertIn(article.summary, homepage)
            self.assertIn("已有手工卡片", homepage)
            self.assertEqual(len(changed), 4)

    def test_publish_rejects_unapproved_article(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            article_path = root / "article.md"
            site = root / "site"
            site.mkdir()
            article_path.write_text(ARTICLE, encoding="utf-8")
            (site / "index.html").write_text(SITE_INDEX, encoding="utf-8")
            article = parse_article_markdown(article_path)

            with self.assertRaisesRegex(ValueError, "approved"):
                publish_to_site(article, site)


if __name__ == "__main__":
    unittest.main()
