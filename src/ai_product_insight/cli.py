from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from .agents import AgentCrew, EditorAgent, InsightAgent, ResearchAgent, ScoutAgent, SocialRepurposeAgent
from .config import WorkflowConfig
from .discovery import DiscoveryAgent
from .editorial import EditorialContext
from .llm import DeepSeekClient, JsonLLM, OfflineDemoLLM
from .models import ComparisonBrief, EvidenceItem, ProductCandidate
from .pipeline import InsightPipeline
from .publishing import (
    approve_and_archive,
    approve_markdown,
    find_git_executable,
    git_commit_and_push,
    parse_article_markdown,
    publish_to_site,
    render_preview,
)
from .sources import HttpFetcher


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI 产品洞察草稿工作流")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config" / "sources.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "output" / "drafts")
    parser.add_argument("--runs", type=Path, default=PROJECT_ROOT / "data" / "runs")
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("scheduled", help="从公开来源自动发现并生成一篇草稿")
    manual = sub.add_parser("manual", help="手动指定产品，同时保留自动研究与写作")
    manual.add_argument("--name", required=True)
    manual.add_argument("--url", required=True)
    manual.add_argument("--notes", default="")
    comparison = sub.add_parser("compare", help="研究多个指定产品并生成一篇对比草稿")
    comparison.add_argument("--name", required=True, help="对比文章的主题")
    comparison.add_argument(
        "--product",
        action="append",
        nargs=2,
        required=True,
        metavar=("PRODUCT_NAME", "OFFICIAL_URL"),
        help="产品名称和主要官方页面；可重复 2-6 次",
    )
    comparison.add_argument("--notes-file", required=True, type=Path, help="UTF-8 编码的个人体验记录")
    comparison.add_argument("--no-clarify", action="store_true", help="跳过一次性编辑追问")
    demo = sub.add_parser("offline-demo", help="使用本地固定样例验证整条链路")
    demo.add_argument("--fixture", type=Path, default=PROJECT_ROOT / "fixtures" / "demo_input.json")
    approve = sub.add_parser("approve", help="将人工确认的文章标记为 approved 并移入 reviewed")
    approve.add_argument("--article", required=True, type=Path, help="已经完成人工审核的 Markdown 草稿")
    publish = sub.add_parser("publish", help="预览并经人工确认后发布到静态 GitHub Pages 网站")
    publish.add_argument("--article", required=True, type=Path, help="待审核发布的 Markdown 草稿")
    publish.add_argument("--site", required=True, type=Path, help="本地网站 Git 仓库目录")
    publish.add_argument("--no-open", action="store_true", help="只生成预览，不自动打开浏览器")
    publish.add_argument("--no-push", action="store_true", help="确认后只更新本地网站，不提交和推送")
    social = sub.add_parser("render-social", help="校验人工截图并生成 X 和小红书配图")
    social.add_argument("--bundle", required=True, type=Path, help="文章对应的 social.json")
    social.add_argument("--assets", required=True, type=Path, help="人工截图所在目录")
    social.add_argument("--output", required=True, type=Path, help="生成图片的输出目录")
    social.add_argument("--font", type=Path, help="可选字体文件；默认自动查找微软雅黑或 Noto Sans CJK")
    return parser


def _load_fixture(path: Path) -> tuple[list[ProductCandidate], dict[str, list[EvidenceItem]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    candidates = [ProductCandidate.model_validate(item) for item in raw["candidates"]]
    evidence: dict[str, list[EvidenceItem]] = {}
    for candidate in candidates:
        evidence[candidate.candidate_id] = [EvidenceItem.model_validate(item) for item in raw["evidence"]]
    return candidates, evidence


def build_comparison_brief(args: argparse.Namespace) -> ComparisonBrief:
    notes_path = args.notes_file
    if not notes_path.is_file():
        raise FileNotFoundError(f"找不到体验记录文件：{notes_path}")
    notes = notes_path.read_text(encoding="utf-8").strip()
    products = [
        ProductCandidate(name=name, url=url, source="manual-comparison", manual=True)
        for name, url in args.product
    ]
    return ComparisonBrief(title=args.name, products=products, notes=notes)


def collect_clarification_answers(questions: list[str]) -> list[str]:
    print("\nDeepSeek 还需要补充以下信息（仅此一轮，可直接回车跳过某题）：\n")
    answers: list[str] = []
    for index, question in enumerate(questions, 1):
        print(f"{index}. {question}")
        answers.append(input("> ").strip())
        print()
    return answers


def build_agent_crew(
    config: WorkflowConfig,
    fetcher: HttpFetcher,
    editorial_context: EditorialContext,
    fast_llm: JsonLLM,
    quality_llm: JsonLLM | None = None,
) -> AgentCrew:
    """Route high-volume research to Flash and editorial judgment to Pro."""
    quality_llm = quality_llm or fast_llm
    return AgentCrew(
        scout=ScoutAgent(fast_llm, config),
        researcher=ResearchAgent(fast_llm, fetcher, config),
        analyst=InsightAgent(quality_llm, editorial_context),
        editor=EditorAgent(quality_llm, editorial_context),
        social=SocialRepurposeAgent(quality_llm, editorial_context),
    )


def run_publish_command(args: argparse.Namespace) -> int:
    try:
        article = parse_article_markdown(args.article)
        preview_path = render_preview(article, args.site, PROJECT_ROOT / "output" / "previews")
    except (OSError, ValueError) as exc:
        print(f"错误：无法生成文章预览：{exc}", file=sys.stderr)
        return 2

    print(f"预览已生成：{preview_path}")
    if not args.no_open:
        webbrowser.open(preview_path.resolve().as_uri())

    if not args.no_push and find_git_executable() is None:
        print(
            "错误：当前系统没有找到 Git，尚不能自动提交和推送。安装 Git/GitHub Desktop 后重试，"
            "或使用 --no-push 只更新本地网站。",
            file=sys.stderr,
        )
        return 2

    print("\n请检查文章事实、来源、表达和页面样式。")
    confirmation = input("确认标记为 approved、更新网站并发布？请输入 PUBLISH：").strip()
    if confirmation != "PUBLISH":
        print("已取消；网站目录和文章审核状态均未修改。")
        return 0

    try:
        approve_markdown(args.article)
        approved = parse_article_markdown(args.article)
        changed = publish_to_site(approved, args.site)
        print("已更新本地网站：")
        for path in changed:
            print(f"- {path}")
        if not args.no_push:
            result = git_commit_and_push(
                args.site,
                changed,
                f"publish insight: {approved.title}",
            )
            print(f"GitHub 推送完成：{result}")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"错误：发布未完整完成：{exc}", file=sys.stderr)
        return 1
    return 0


def run_approve_command(args: argparse.Namespace) -> int:
    try:
        outputs = approve_and_archive(args.article, PROJECT_ROOT / "output" / "reviewed")
    except (OSError, ValueError) as exc:
        print(f"错误：文章审核状态未更新：{exc}", file=sys.stderr)
        return 2
    print("文章已人工审核通过：")
    for path in outputs:
        print(f"- {path}")
    return 0


def run_render_social_command(args: argparse.Namespace) -> int:
    from .social_render import MissingAssetsError, render_social_assets

    try:
        outputs = render_social_assets(args.bundle, args.assets, args.output, args.font)
    except (OSError, ValueError, RuntimeError, MissingAssetsError) as exc:
        print(f"错误：社交配图未生成：{exc}", file=sys.stderr)
        return 3
    print("社交配图已生成：")
    for path in outputs:
        print(f"- {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    if args.mode == "approve":
        return run_approve_command(args)
    if args.mode == "publish":
        return run_publish_command(args)
    if args.mode == "render-social":
        return run_render_social_command(args)
    config = WorkflowConfig.load(args.config)
    editorial_context = EditorialContext.load(PROJECT_ROOT)
    fetcher = HttpFetcher(timeout=config.request_timeout_seconds)
    if args.mode == "offline-demo":
        fast_llm = quality_llm = OfflineDemoLLM()
    else:
        if not config.api_key:
            print("错误：实时运行需要环境变量 DEEPSEEK_API_KEY。可先运行 offline-demo。", file=sys.stderr)
            return 2
        fast_llm = DeepSeekClient(
            api_key=config.api_key,
            base_url=config.deepseek_base_url,
            model=config.deepseek_fast_model,
            timeout=max(60, config.request_timeout_seconds),
        )
        quality_llm = DeepSeekClient(
            api_key=config.api_key,
            base_url=config.deepseek_base_url,
            model=config.deepseek_quality_model,
            timeout=max(60, config.request_timeout_seconds),
        )

    discovery = DiscoveryAgent(config, fetcher)
    crew = build_agent_crew(
        config=config,
        fetcher=fetcher,
        editorial_context=editorial_context,
        fast_llm=fast_llm,
        quality_llm=quality_llm,
    )
    pipeline = InsightPipeline(
        discovery,
        crew,
        args.output,
        args.runs,
        social_output_dir=PROJECT_ROOT / "output" / "social",
        assets_dir=PROJECT_ROOT / "inputs" / "assets",
    )

    manual = None
    fixture_candidates = None
    fixture_evidence = None
    if args.mode == "manual":
        manual = ProductCandidate(name=args.name, url=args.url, source="manual", summary=args.notes, manual=True)
    elif args.mode == "offline-demo":
        fixture_candidates, fixture_evidence = _load_fixture(args.fixture)

    if args.mode == "compare":
        try:
            comparison_brief = build_comparison_brief(args)
        except (OSError, UnicodeError, ValueError) as exc:
            print(f"错误：无法读取对比输入：{exc}", file=sys.stderr)
            return 2
        clarification_callback = None
        if not args.no_clarify:
            if sys.stdin.isatty():
                clarification_callback = collect_clarification_answers
            else:
                print("提示：当前不是交互终端，已跳过一次性编辑追问。", file=sys.stderr)
        report = pipeline.run_comparison(comparison_brief, clarification_callback=clarification_callback)
    else:
        report = pipeline.run(
            mode=args.mode,
            manual=manual,
            fixture_candidates=fixture_candidates,
            fixture_evidence=fixture_evidence,
        )
    print(report.model_dump_json(indent=2))
    return 0 if report.outputs and report.status in {"completed", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
