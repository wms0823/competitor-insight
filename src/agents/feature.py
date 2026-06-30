from langchain_core.messages import SystemMessage
from src.state import ComparisonState
from src.tools.search import search_tool
from src.config import settings

FEATURE_PROMPT = """你是功能对比分析专家。请根据以下搜索结果，对比 {product_a} 和 {product_b} 的功能差异。

搜索结果：
{search_results}

输出要求：简洁，直接给表格和要点，无需冗余描述。

## 功能对比
| 功能 | {product_a} | {product_b} | 优势方 |
|------|------------|------------|--------|
（至少 5 项核心功能对比）

### 功能维度打分（1-10）
- {product_a}: X分
- {product_b}: Y分"""


def feature_agent(state: ComparisonState) -> dict:
    a, b = state["product_a"], state["product_b"]

    # 1. 一次搜索
    try:
        results = search_tool.invoke(f"{a} vs {b} 功能对比 核心功能 特色")
    except Exception:
        results = "搜索结果暂不可用"

    # 2. 一次 LLM 调用（限制搜索结果长度，加速生成）
    llm = settings.get_llm(temperature=0.1)
    prompt = FEATURE_PROMPT.format(product_a=a, product_b=b, search_results=results[:2000])
    resp = llm.invoke([SystemMessage(content=prompt)])

    return {"feature_result": resp.content}
