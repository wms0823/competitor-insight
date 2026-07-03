import json
from typing import Literal
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from src.state import ComparisonState
from src.config import settings

ROUTE = Literal["feature", "pricing", "sentiment", "scenario", "end"]

AGENT_DESCRIPTIONS = {
    "feature": "功能对比：对比两个产品的核心功能、技术能力、特色功能",
    "pricing": "价格对比：对比定价模式、性价比、免费额度、隐藏成本",
    "sentiment": "口碑对比：对比用户评价、社区活跃度、开发者生态、满意度",
    "scenario": "场景对比：对比适用场景、行业案例、最佳实践、局限性",
}

SUPERVISOR_PROMPT = """你是竞品对比系统的主管。你的任务是协调四个专业 Agent 完成对比分析。

四个 Agent 及其职责：
- feature: 功能对比
- pricing: 价格对比
- sentiment: 口碑对比
- scenario: 场景对比

当前已完成：{completed}
未完成：{pending}

决策规则：
1. 如果还有未完成的维度 → 选择一个最关键的维度，分配给对应 Agent
2. 如果四个维度全部完成 → 汇总所有结果，判断是否有冲突点，输出 "end"
3. 冲突点定义：两个维度的结论互相矛盾。例如「功能很强但口碑很差」→ 标记为冲突点，需要重点分析

输出 JSON：{{"next_agent": "feature|pricing|sentiment|scenario|end", "reason": "..."}}
"""


def supervisor_node(state: ComparisonState) -> dict:
    llm = ChatOpenAI(model=settings.llm_model, temperature=0)
    completed = state.get("completed_dims", [])
    pending = [
        d
        for d in ["feature", "pricing", "sentiment", "scenario"]
        if d not in completed
    ]

    if not pending:
        return _summarize(state, llm)

    prompt = SUPERVISOR_PROMPT.format(completed=completed, pending=pending)
    resp = llm.invoke([SystemMessage(content=prompt)])
    try:
        decision = json.loads(resp.content)
    except json.JSONDecodeError:
        decision = {"next_agent": pending[0]}

    return {"messages": [resp], "next_agent": decision["next_agent"]}


def _summarize(state: ComparisonState, llm):
    """四个维度全部完成 → 汇总 + 冲突检测"""
    summary_prompt = f"""汇总以下四个维度的对比结果，生成最终报告。

产品A: {state['product_a']} | 产品B: {state['product_b']}

功能对比: {state.get('feature_result', '')}
价格对比: {state.get('pricing_result', '')}
口碑对比: {state.get('sentiment_result', '')}
场景对比: {state.get('scenario_result', '')}

要求：
1. 生成结构化对比报告（总评 + 各维度打分 + 决策建议）
2. 找出冲突点：是否有维度结论互相矛盾的地方
3. 给出最终推荐及理由"""
    resp = llm.invoke([SystemMessage(content=summary_prompt)])
    return {
        "messages": [resp],
        "final_report": resp.content,
        "next_agent": "end",
    }


def supervisor_router(state: ComparisonState) -> ROUTE:
    na = state.get("next_agent", "")
    if state.get("error_count", 0) >= state.get("max_retries", 3):
        return "end"
    valid = {"feature", "pricing", "sentiment", "scenario", "end"}
    return na if na in valid else "end"
