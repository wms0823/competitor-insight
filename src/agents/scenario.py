from langchain_core.messages import SystemMessage
from src.state import ComparisonState
from src.tools.search import search_tool
from src.config import settings

SCENARIO_PROMPT = """你是场景对比分析专家。请根据以下搜索结果，对比 {product_a} 和 {product_b} 的适用场景。

搜索结果：
{search_results}

输出要求：简洁。

## 场景对比
| 维度 | {product_a} | {product_b} | 优势方 |
|------|------------|------------|--------|
（适用团队、行业、场景等）

### 场景维度打分（1-10）
- {product_a}: X分
- {product_b}: Y分"""


def scenario_agent(state: ComparisonState) -> dict:
    a, b = state["product_a"], state["product_b"]

    try:
        results = search_tool.invoke(f"{a} vs {b} 适用场景 行业案例 最佳实践")
    except Exception:
        results = "搜索结果暂不可用"

    llm = settings.get_llm(temperature=0.1)
    prompt = SCENARIO_PROMPT.format(product_a=a, product_b=b, search_results=results[:2000])
    resp = llm.invoke([SystemMessage(content=prompt)])

    return {"scenario_result": resp.content}
