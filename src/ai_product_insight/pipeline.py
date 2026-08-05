from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from .agents import AgentCrew
from .discovery import DiscoveryAgent
from .models import (
    ClarificationItem,
    ClarificationRound,
    ComparisonBrief,
    EvidenceItem,
    EvidenceQuality,
    ProductCandidate,
    ResearchPack,
    RunReport,
)
from .render import write_outputs


class InsightPipeline:
    def __init__(self, discovery: DiscoveryAgent, crew: AgentCrew, output_dir: Path, runs_dir: Path) -> None:
        self.discovery = discovery
        self.crew = crew
        self.output_dir = output_dir
        self.runs_dir = runs_dir

    def run(
        self,
        mode: str,
        manual: ProductCandidate | None = None,
        fixture_candidates: list[ProductCandidate] | None = None,
        fixture_evidence: dict[str, list[EvidenceItem]] | None = None,
    ) -> RunReport:
        run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
        report = RunReport(run_id=run_id, mode=mode, status="completed")
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_dir = self.runs_dir / run_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        try:
            if fixture_candidates is not None:
                candidates, discovery_errors = fixture_candidates, []
            else:
                candidates, discovery_errors = self.discovery.discover(manual=manual)
            report.errors.extend(discovery_errors)
            report.candidate_count = len(candidates)
            self._write_json(checkpoint_dir / "01-candidates.json", candidates)

            selected = self.crew.scout.select(candidates)
            report.selected_count = len(selected)
            self._write_json(checkpoint_dir / "02-selected.json", selected)
            if not selected:
                report.status = "partial"
                report.errors.append("No candidate met the selection threshold")

            for candidate in selected:
                seed = (fixture_evidence or {}).get(candidate.candidate_id)
                research = self.crew.researcher.research(candidate, seed_evidence=seed)
                self._write_json(checkpoint_dir / f"03-research-{candidate.candidate_id}.json", research)
                if research.quality == EvidenceQuality.insufficient:
                    report.status = "partial"
                    report.errors.append(f"Insufficient evidence for {candidate.name}")
                    continue
                insight = self.crew.analyst.analyze(research)
                self._write_json(checkpoint_dir / f"04-insight-{candidate.candidate_id}.json", insight)
                article = self.crew.editor.draft(research, insight)
                paths = write_outputs(article, self.output_dir)
                report.outputs.extend(str(path) for path in paths)
                if mode == "scheduled":
                    break

        except Exception as exc:  # The report is the operational failure boundary.
            report.status = "failed"
            report.errors.append(f"{type(exc).__name__}: {exc}")
        finally:
            report.finished_at = datetime.now(timezone.utc)
            (checkpoint_dir / "run-report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return report

    def run_comparison(
        self,
        brief: ComparisonBrief,
        fixture_evidence: dict[str, list[EvidenceItem]] | None = None,
        clarification_callback: Callable[[list[str]], list[str]] | None = None,
    ) -> RunReport:
        run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
        report = RunReport(
            run_id=run_id,
            mode="compare",
            status="completed",
            candidate_count=len(brief.products),
        )
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_dir = self.runs_dir / run_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(checkpoint_dir / "01-comparison-brief.json", brief)

        research_results: list[ResearchPack] = []
        usable: list[ResearchPack] = []
        try:
            for candidate in brief.products:
                try:
                    seed = (fixture_evidence or {}).get(candidate.candidate_id)
                    research = self.crew.researcher.research(
                        candidate,
                        seed_evidence=seed,
                        min_evidence_items=1,
                    )
                    research_results.append(research)
                    self._write_json(checkpoint_dir / f"02-research-{candidate.candidate_id}.json", research)
                    if research.quality == EvidenceQuality.insufficient:
                        report.status = "partial"
                        report.errors.append(f"Insufficient public evidence for {candidate.name}; personal notes retained")
                        continue
                    usable.append(research)
                except Exception as exc:
                    report.status = "partial"
                    report.errors.append(f"Research failed for {candidate.name}: {type(exc).__name__}: {exc}")

            report.selected_count = len(usable)
            if len(usable) < 2:
                report.status = "partial"
                report.errors.append("Comparison requires usable evidence for at least two products")
            else:
                clarification = ClarificationRound()
                if clarification_callback is not None:
                    plan = self.crew.analyst.clarifying_questions(brief, research_results)
                    answers = clarification_callback(plan.questions)
                    items = [
                        ClarificationItem(question=question, answer=answer.strip()[:2000])
                        for question, answer in zip(plan.questions, answers)
                        if answer.strip()
                    ]
                    clarification = ClarificationRound(items=items)
                    self._write_json(checkpoint_dir / "03-clarification.json", clarification)
                insight = self.crew.analyst.compare(brief, research_results, clarification)
                self._write_json(checkpoint_dir / "04-comparison-insight.json", insight)
                article = self.crew.editor.draft_comparison(brief, research_results, insight, clarification)
                report.outputs.extend(str(path) for path in write_outputs(article, self.output_dir))
                if len(usable) < len(brief.products):
                    report.status = "partial"
        except Exception as exc:
            report.status = "failed"
            report.errors.append(f"{type(exc).__name__}: {exc}")
        finally:
            report.finished_at = datetime.now(timezone.utc)
            (checkpoint_dir / "run-report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return report

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        if isinstance(value, list):
            data = [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in value]
        elif hasattr(value, "model_dump"):
            data = value.model_dump(mode="json")
        else:
            data = value
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
