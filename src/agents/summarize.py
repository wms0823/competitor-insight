from src.state import ComparisonState


def summarize_node(state: ComparisonState) -> dict:
    """直接拼接四个维度的结果，不再单独调 LLM 汇总。"""
    a, b = state["product_a"], state["product_b"]
    cat = state.get("category", "通用")

    feature = state.get("feature_result", "") or ""
    pricing = state.get("pricing_result", "") or ""
    sentiment = state.get("sentiment_result", "") or ""
    scenario = state.get("scenario_result", "") or ""

    report = f"""# {a} vs {b} 竞品对比分析报告
> 品类：{cat} | 由 AI 多智能体自动生成

---

{feature}

---

{pricing}

---

{sentiment}

---

{scenario}

---

## 综合建议
以上四个维度由 AI 智能体基于公开信息独立分析，请结合实际需求选择。
"""

    return {"final_report": report}
