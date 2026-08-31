"""Live, read-only evidence check. Does not call a model or create drafts.

Example: python scripts/check_research_sources.py --archive /path/run.zip
         python scripts/check_research_sources.py --name Demo --url https://demo.example --notes "Product purpose"
"""
from __future__ import annotations

import argparse
import json
import zipfile

from ai_product_insight.models import ProductCandidate
from ai_product_insight.research import collect_research_evidence, has_required_evidence_mix
from ai_product_insight.sources import HttpFetcher


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive")
    parser.add_argument("--name")
    parser.add_argument("--url")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    if args.archive:
        with zipfile.ZipFile(args.archive) as archive:
            names = sorted(n for n in archive.namelist() if n.endswith("/02-selected.json"))
            if not names:
                parser.error("No selected-candidate checkpoint in archive")
            candidates = [ProductCandidate.model_validate(item) for item in json.loads(archive.read(names[-1]))]
    elif args.name and args.url:
        candidates = [ProductCandidate(name=args.name, url=args.url, source="manual", summary=args.notes, manual=True)]
    else:
        parser.error("Provide --archive or --name and --url")
    for candidate in candidates:
        result = collect_research_evidence(candidate, HttpFetcher(timeout=15, retries=0))
        print(json.dumps({
            "name": candidate.name,
            "usable_source_mix": has_required_evidence_mix(result.items),
            "sources": [{"type": e.source_type, "url": str(e.url), "chars": len(e.excerpt)} for e in result.items],
            "diagnostics": result.errors,
        }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
