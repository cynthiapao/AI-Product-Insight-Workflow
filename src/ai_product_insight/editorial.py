from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Editorial resource not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid editorial JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Editorial resource must contain a JSON object: {path}")
    return value


@dataclass(frozen=True)
class GoldExample:
    input: dict[str, Any]
    output: dict[str, Any]


@dataclass(frozen=True)
class EditorialContext:
    """Reusable editorial rules and all approved input/output transformations."""

    profile: dict[str, Any]
    rubric: dict[str, Any]
    gold_examples: tuple[GoldExample, ...]

    @property
    def gold_input(self) -> dict[str, Any]:
        """Backward-compatible access to the first approved example input."""
        return self.gold_examples[0].input

    @property
    def gold_output(self) -> dict[str, Any]:
        """Backward-compatible access to the first approved example output."""
        return self.gold_examples[0].output

    @classmethod
    def load(cls, project_root: Path) -> "EditorialContext":
        gold_dir = project_root / "examples" / "gold"
        examples: list[GoldExample] = []
        input_paths = sorted(
            gold_dir.glob("*.input.json"),
            key=lambda path: (path.name != "ai-website.input.json", path.name),
        )
        for input_path in input_paths:
            output_path = input_path.with_name(
                input_path.name.removesuffix(".input.json") + ".output.json"
            )
            if not output_path.is_file():
                raise FileNotFoundError(
                    f"Gold example output not found for {input_path}: {output_path}"
                )
            examples.append(
                GoldExample(
                    input=_load_json_object(input_path),
                    output=_load_json_object(output_path),
                )
            )
        if not examples:
            raise FileNotFoundError(f"No gold examples found in: {gold_dir}")
        return cls(
            profile=_load_json_object(project_root / "config" / "editorial_profile.json"),
            rubric=_load_json_object(project_root / "config" / "editorial_rubric.json"),
            gold_examples=tuple(examples),
        )

    def _render(self, role: str, examples: list[dict[str, Any]]) -> str:
        context = {
            "role": role,
            "editorial_profile": self.profile,
            "editorial_rubric": self.rubric,
            "approved_examples": examples,
        }
        return (
            "\n\n[EDITORIAL_CONTEXT]\n"
            "以下内容是编辑规范与已通过人工审核的转换范例。学习其推理方式、结构密度、"
            "个人表达和证据边界；不要复制范例中的产品事实、结论或措辞到其他产品。\n"
            + json.dumps(context, ensure_ascii=False, indent=2)
        )

    def analyst_prompt_suffix(self) -> str:
        examples: list[dict[str, Any]] = []
        for example in self.gold_examples:
            selected_output = {
                key: example.output[key]
                for key in (
                    "title",
                    "opening",
                    "why_it_works",
                    "boundaries",
                    "personal_judgment",
                    "transferable_methods",
                )
                if key in example.output
            }
            examples.append({"input": example.input, "output": selected_output})
        return self._render("analyst", examples)

    def editor_prompt_suffix(self) -> str:
        examples = [
            {"input": example.input, "output": example.output}
            for example in self.gold_examples
        ]
        return self._render("editor", examples)
