from typing import Annotated, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


def _merge_metrics(left: dict, right: dict) -> dict:
    """合并并行 Agent 的指标字典（LangGraph reducer）。"""
    merged = {**left}
    merged.update(right)
    return merged


def _merge_lists(left: list, right: list) -> list:
    """合并并行节点返回的列表（LangGraph reducer）。"""
    return (left or []) + (right or [])


class ComparisonState(TypedDict):
    # === 消息历史 ===
    messages: Annotated[List[BaseMessage], add_messages]

    # === 用户输入 ===
    product_a: str          # 产品A名称
    product_b: str          # 产品B名称
    category: str           # 所属品类

    # === 链路追踪 ===
    trace_id: str           # 请求级追踪 ID
    agent_metrics: Annotated[Dict[str, dict], _merge_metrics]  # 各 Agent 耗时/调用统计（支持并行合并）

    # === 各维度产出 ===
    feature_result: Optional[str]    # 功能对比结果
    pricing_result: Optional[str]    # 价格对比结果
    sentiment_result: Optional[str]  # 口碑对比结果
    scenario_result: Optional[str]   # 场景对比结果

    # === 汇总 ===
    final_report: Optional[str]      # 最终对比报告
    conflict_points: Optional[str]   # 冲突点（各维度结论矛盾处）

    # === 性能模式 ===
    mode: str                       # "fast" | "standard" | "deep"

    # === 实时进度 ===
    progress: Annotated[List[str], _merge_lists]  # 各 Agent 的实时进度消息（支持并行合并）

    # === 控制 ===
    next_agent: Optional[str]        # supervisor 的路由决策（预留）
    completed_dims: List[str]        # 已完成的维度
    error_count: int
    max_retries: int
