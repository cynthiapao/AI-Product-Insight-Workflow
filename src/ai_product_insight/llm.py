from __future__ import annotations

import json
import time
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class JsonLLM(Protocol):
    def generate_json(self, system: str, user: str) -> dict[str, Any]: ...


class LLMError(RuntimeError):
    pass


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 60,
        retries: int = 2,
    ) -> None:
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for live runs")
        self.api_key = api_key
        self.url = f"{base_url.rstrip('/')}/chat/completions"
        self.model = model
        self.timeout = timeout
        self.retries = retries

    def generate_json(self, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system + "\n只返回有效 JSON，不要使用 Markdown 代码块。"},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "temperature": 0.2,
            "stream": False,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                request = Request(
                    self.url,
                    data=body,
                    method="POST",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                with urlopen(request, timeout=self.timeout) as response:
                    result = json.loads(response.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
            except (HTTPError, URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.8 * (attempt + 1))
        raise LLMError(f"DeepSeek request failed: {last_error}")


class OfflineDemoLLM:
    """Deterministic local substitute used only by the offline demo and tests."""

    def generate_json(self, system: str, user: str) -> dict[str, Any]:
        data = json.loads(user)
        if "[SCOUT]" in system:
            assessments = []
            for index, candidate in enumerate(data["candidates"]):
                dims = {"relevance": 5 if index == 0 else 3, "novelty": 4, "product_depth": 4, "evidence": 4}
                total = round(dims["relevance"] * .35 + dims["novelty"] * .25 + dims["product_depth"] * .25 + dims["evidence"] * .15, 2)
                assessments.append({"candidate_id": candidate["candidate_id"], "score": {**dims, "total": total, "reason": "产品机制清晰，具备近期讨论度和可验证的公开信息。"}})
            return {"assessments": assessments, "selected_ids": [data["candidates"][0]["candidate_id"]]}
        if "[RESEARCH]" in system:
            return {
                "verified_facts": ["该产品把多步骤任务整合进一个可观察的工作流。", "公开页面展示了任务过程和阶段性结果。"],
                "open_questions": ["长期使用中的稳定性仍需真实体验验证。"],
                "quality": "usable",
            }
        if "[CLARIFIER]" in system:
            return {
                "questions": [
                    "哪个具体输出让你第一次觉得模型真正理解了你的设计意图？",
                    "执行顺利和需要多轮调整的分界分别是什么？",
                ]
            }
        if "[COMPARE_ANALYST]" in system:
            names = [item["name"] for item in data["comparison_subjects"]]
            joined = "、".join(names)
            return {
                "one_line": f"在这次真实项目里，{joined} 并不是可以互换的同一种工具，而是在不同阶段承担了不同角色。",
                "core_mechanism": "这次比较不按参数或单次回答排名，而是沿着同一个项目的推进过程观察模型：谁更适合把模糊意图变成方向，谁更适合持续执行，谁更适合精修内容，以及模型之间怎样交接上下文。",
                "why_it_works": "设计探索、代码执行、内容精修和中文表达需要的能力并不相同。把模型放回真实任务阶段，差异才会转化成可以使用的分工，而不是停留在抽象的能力印象上。",
                "limitations": ["这些判断来自一次个人网站项目，不能直接外推到所有任务。", "模型版本和提示方式变化后，体验也可能发生变化。"],
                "personal_judgment": "我更愿意把模型选择理解为工作流设计，而不是寻找一个全能冠军。真正影响效率的，是能否在正确阶段找到合适的协作者，并让前一阶段的意图和约束顺利交给下一阶段。",
                "patterns": [
                    {"name": "按项目阶段分配模型", "principle": "先识别任务处于探索、执行还是精修阶段，再把它交给在该类任务中表现更合适的模型。", "applies_when": "适用于需要多个模型共同完成的中长期创作和产品项目。"},
                    {"name": "建立统一交接上下文", "principle": "用同一份目标、约束、样例和已确认决策作为模型之间的交接材料，减少重复解释和风格漂移。", "applies_when": "适用于频繁切换模型或工具、且需要保持产物一致性的任务。"},
                ],
            }
        if "[ANALYST]" in system:
            name = data["candidate"]["name"]
            return {
                "one_line": f"{name} 把复杂的 AI 执行过程转化为用户可理解、可干预的任务流程。",
                "core_mechanism": "它没有把生成结果作为唯一界面，而是把任务拆成连续阶段，让用户看到系统正在做什么，并在关键节点保留控制权。",
                "why_it_works": "可观察的过程降低了用户面对黑盒系统时的不确定感，也让错误更早暴露，用户可以在最终结果生成前纠偏。",
                "limitations": ["流程透明不等于结果可靠，关键事实仍需核验。", "阶段过多可能给轻量任务增加额外负担。"],
                "personal_judgment": "我更看重它对人机协作节奏的处理，而不是单次回答能力。真正的产品优势来自可理解、可控制的执行过程。",
                "patterns": [{"name": "可观察的 AI 工作流", "principle": "把高耗时或多步骤的模型执行拆成用户能够理解的阶段，并在关键节点提供反馈与纠偏入口。", "applies_when": "适用于等待时间较长、错误成本较高或需要多工具协作的 AI 任务。"}],
            }
        if "[COMPARE_EDITOR]" in system:
            names = [item["name"] for item in data["comparison_subjects"]]
            joined = "、".join(names)
            return {
                "slug": "ai-models-in-one-website-project",
                "title": "同一个网站项目里，不同 AI 模型分别适合做什么？",
                "summary": f"把 {joined} 放进同一次建站过程后，我看到的不是简单的强弱排序，而是它们在探索、执行和精修阶段呈现出的不同角色。",
                "read_minutes": 5,
                "tags": ["AI 产品", "多模型协作", "个人建站"],
                "opening": "大模型并不是可以随意替换的同一种工具。至少在这次个人网站项目里，它们更像几位工作方式不同的协作者，分别在设计探索、持续执行、内容精修和中文表达中发挥作用。",
                "core_experience": f"我把 {joined} 放进了同一个网站项目，而不是用一道标准题测试它们。实际推进中，有的模型更容易接住模糊的设计意图，有的适合在方案确定后持续修改代码，有的更适合处理项目文案。真正明显的差异，不只出现在答案里，也出现在它们怎样追问、怎样延续上下文，以及我需要花多少精力把想法翻译给它们。",
                "why_it_works": "这种分工之所以有意义，是因为建站并不是一个单一任务。最初需要把模糊偏好变成可以讨论的方向，中间需要大量准确而连续的执行，后期还要校准设计细节和中文表达。不同阶段需要的能力不同，把模型放在具体任务里观察，比脱离场景比较参数更接近真实生产力。",
                "boundaries": "这不是一份普遍适用的模型排行榜。体验受到模型版本、上下文长度、提示方式和我对工具熟悉程度的影响，多模型切换还会产生重复交代背景、风格标准不一致和决策丢失等成本。因此，文章中的结论只能代表这次个人网站项目。",
                "personal_judgment": "我的判断是，未来个人使用 AI 的效率差距，未必只来自能否找到最强模型，更来自能否建立一套清楚的协作分工。模型的能力当然重要，但什么时候介入、接收什么材料、完成到什么程度再交给下一个工具，同样属于产品工作流的一部分。",
                "transferable_methods": [
                    {"name": "按阶段而不是按名气选模型", "principle": "先把项目拆成方向探索、方案执行和内容精修，再根据真实表现为每个阶段选择协作者。", "applies_when": "适用于设计、写作、编程混合发生的复杂个人项目。"},
                    {"name": "给模型准备同一份交接单", "principle": "持续维护目标、风格样例、已确认方案和不能改变的约束，让模型切换时共享同一基线。", "applies_when": "适用于需要跨多个模型连续迭代、又不能丢失风格一致性的项目。"},
                ],
            }
        if "[EDITOR]" in system:
            name = data["candidate"]["name"]
            return {
                "slug": "observable-ai-workflow",
                "title": f"我为什么更关注 {name} 的过程，而不只是答案",
                "summary": "一个值得关注的 AI 产品机制：让复杂执行过程可见、可理解，也给用户留下纠偏空间。",
                "read_minutes": 5,
                "tags": ["AI 产品", "交互设计", "工作流"],
                "opening": f"第一次看到 {name} 时，我真正感兴趣的不是它又能多回答一个问题，而是它如何把复杂任务的执行过程交还给用户。",
                "core_experience": "传统对话产品常把任务压缩成输入和答案，中间过程几乎不可见。这个产品选择展示任务阶段、当前动作和阶段性产物。用户不必盯着加载动画猜测系统是否卡住，也能在方向偏离时更早发现问题。",
                "why_it_works": "这种设计缓解了 AI 产品最常见的不确定性。过程可见会建立适度信任，阶段性结果又提供了判断线索。它并没有承诺模型不会犯错，而是让错误变得更容易被看见和修正。对用户来说，等待不再只是被动消耗，而是一个可以理解任务进度、判断方向是否正确的过程。",
                "boundaries": "透明流程也可能变成表演式进度。如果阶段信息与真实执行无关，反而会消耗信任；对于低风险、几秒即可完成的任务，复杂流程也没有必要。",
                "personal_judgment": "我认为这类产品的竞争点正在从模型回答能力转向任务组织能力。真正有价值的不是展示更多思考文本，而是让用户知道下一步发生什么、何时需要介入，以及结果依据来自哪里。如果这些过程信息能够对应真实动作，它会比单纯提高回答速度更能建立长期信任，也更适合进入高风险的业务流程。",
                "transferable_methods": [{"name": "可观察的 AI 工作流", "principle": "将长耗时、多步骤的 AI 任务拆成真实且可验证的阶段，并在关键节点提供纠偏入口。", "applies_when": "适用于企业分析、深度研究、数据处理等错误成本较高的任务。"}],
            }
        raise LLMError("Unknown offline demo prompt")
