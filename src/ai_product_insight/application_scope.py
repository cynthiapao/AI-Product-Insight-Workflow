from __future__ import annotations

import re

from .models import ProductCandidate


# This is intentionally conservative. Ambiguous products continue to the LLM
# assessment; only candidates that clearly describe a technical building block
# are rejected before research spends network and model budget on them.
NON_APPLICATION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bterminal assistant\b",
        r"\bcommand[- ]line (?:tool|assistant|utility|interface)\b",
        r"\b(?:developer|agent|orchestration) framework\b",
        r"\b(?:python|javascript|typescript|rust|go) library\b",
        r"\b(?:api|sdk) (?:client|wrapper|toolkit)\b",
        r"\b(?:model|training|fine[- ]tuning) (?:framework|toolkit|library)\b",
        r"\b(?:inference|serving) engine\b",
        r"\b(?:vector )?database engine\b",
        r"\bmodel weights?\b",
        r"\bbenchmark(?:ing)? (?:suite|tool|dataset)\b",
        r"\btraining dataset\b",
        r"\bobservability (?:stack|framework|library)\b",
    )
)


def is_clear_non_application(candidate: ProductCandidate) -> bool:
    """Return True only for obvious technical artifacts in automatic discovery.

    A manually supplied product always reflects an explicit editorial choice and
    therefore bypasses this automatic guard.
    """

    if candidate.manual:
        return False
    text = f"{candidate.name}\n{candidate.summary}".strip()
    return any(pattern.search(text) for pattern in NON_APPLICATION_PATTERNS)
