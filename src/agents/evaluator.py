from langchain_core.messages import SystemMessage
from src.state import ComparisonState
from src.config import settings

EVALUATOR_PROMPT = """你是技术选型顾问。综合以下四维竞品分析，输出精炼评审报告。

## {product_a} vs {product_b}（{category}）

数据:
- 功能: {feature_result}
- 价格: {pricing_result}
- 口碑: {sentiment_result}
- 场景: {scenario_result}

输出要求（每节2-4句，总字数≤1200）：

**总评** — 一句结论。

---

**交叉验证** — 各维度可靠性，标出薄弱维度。

---

**冲突点** — 列出矛盾结论及其原因。

---

**综合评分** — 用表格（权重: 功能30% 价格25% 口碑25% 场景20%）。

---

**分场景推荐** — 用表格（个人/小团队、中型企业、大型企业）。

---

**技术决策建议** — 3-5条，每条含适用条件与风险。

每个板块之间必须用 `---` 分割线隔开。
末尾附加：
<!--CONFLICTS-->
冲突要点
<!--END_CONFLICTS-->
"""


def evaluator_agent(state: ComparisonState) -> dict:
    a = state["product_a"]
    b = state["product_b"]
    cat = state.get("category", "通用")

    def _trim(text: str, max_chars: int = 900) -> str:
        if not text:
            return "（暂无结果）"
        text = text.strip()
        return text if len(text) <= max_chars else text[:max_chars] + "\n...(已截断)"

    feature = _trim(state.get("feature_result", ""))
    pricing = _trim(state.get("pricing_result", ""))
    sentiment = _trim(state.get("sentiment_result", ""))
    scenario = _trim(state.get("scenario_result", ""))

    llm = settings.get_llm(temperature=0.1)
    prompt = EVALUATOR_PROMPT.format(
        product_a=a, product_b=b, category=cat,
        feature_result=feature, pricing_result=pricing,
        sentiment_result=sentiment, scenario_result=scenario,
    )
    resp = llm.invoke([SystemMessage(content=prompt)])
    report = resp.content.replace("\r\n", "\n")  # 统一换行符

    # 后处理：确保各板块之间有分割线（在 ### 标题前插入 ---）
    import re
    # 匹配以 ### 开头的板块标题行
    report = re.sub(
        r'\n(###\s+(?:交叉验证|冲突点|综合评分|分场景推荐|分场景建议|技术决策建议))',
        r'\n\n---\n\n\1',
        report
    )
    # 去除开头可能产生的多余空行和分割线
    report = report.lstrip("\n")
    if report.startswith("---"):
        report = report[3:].lstrip("\n")

    # 解析冲突摘要
    conflicts = ""
    if "<!--CONFLICTS-->" in report and "<!--END_CONFLICTS-->" in report:
        start = report.index("<!--CONFLICTS-->") + len("<!--CONFLICTS-->")
        end = report.index("<!--END_CONFLICTS-->")
        conflicts = report[start:end].strip()
        prefix = report[: start - len("<!--CONFLICTS-->")].rstrip()
        while prefix.endswith("---"):
            prefix = prefix[:-3].rstrip("\n").rstrip()
        report = (
            prefix
            + "\n\n---\n\n### 冲突摘要\n\n" + conflicts + "\n"
            + report[end + len("<!--END_CONFLICTS-->"):].strip()
        )

    return {"final_report": report, "conflict_points": conflicts if conflicts else "无冲突"}