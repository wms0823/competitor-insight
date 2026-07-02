"""ReAct (Reasoning + Acting) Agent 工厂函数。

将原本"搜索 → 截断 → 单次 LLM 调用"的流水线升级为真正的 Agent 循环：
LLM 自主决定何时搜索、搜索什么、是否需要抓取详情页，
多轮迭代直到信息充分后再输出结构化对比结果。
"""

import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from src.config import settings
from src.observability import AgentMetrics
from src.state import ComparisonState
from src.tools.scraper import scrape_tool
from src.tools.search import search_tool

logger = logging.getLogger(__name__)

# ── ReAct 配置 ──
MAX_REACT_ITERATIONS = 6  # 最大迭代次数（Agent 通常在 3-4 轮内完成）

# 所有维度 Agent 共用的工具集
DIMENSION_TOOLS: List[BaseTool] = [search_tool, scrape_tool]

# 工具名 → 工具实例的快速映射
TOOL_BY_NAME = {t.name: t for t in DIMENSION_TOOLS}


def create_dimension_agent(
    name: str,
    system_prompt: str,
):
    """创建基于 ReAct 循环的维度对比 Agent。

    Args:
        name: 维度名称（feature / pricing / sentiment / scenario）。
        system_prompt: 系统提示词模板，支持 {product_a} {product_b} {category} 占位符。

    Returns:
        一个符合 LangGraph 节点签名的可调用对象: (state) -> dict。
    """

    def agent_node(state: ComparisonState) -> dict:
        a = state["product_a"]
        b = state["product_b"]
        cat = state.get("category", "通用")

        # ── 指标采集 ──
        metrics = AgentMetrics()
        metrics.start()

        # ── 初始化 LLM（绑定工具） ──
        llm = settings.get_llm(temperature=0.1)
        llm_with_tools = llm.bind_tools(DIMENSION_TOOLS)

        # ── 构建初始消息 ──
        system_msg = SystemMessage(content=system_prompt.format(
            product_a=a, product_b=b, category=cat,
        ))
        user_msg = HumanMessage(content=(
            f"请对比 {a} 和 {b}。"
            f"用 search_tool 搜索 2-3 次获取关键信息，"
            f"必要时用 scrape_tool 抓取重要页面。"
            f"信息基本充分后立即输出对比结果，追求效率而非穷尽。"
        ))

        messages = [system_msg, user_msg]

        # ── ReAct 循环 ──
        for iteration in range(1, MAX_REACT_ITERATIONS + 1):
            logger.info("[%s] ReAct 第 %d/%d 轮", name, iteration, MAX_REACT_ITERATIONS)

            # 第 3 轮后提醒收尾
            if iteration == 3:
                messages.append(HumanMessage(content=(
                    "（已搜索 3 轮，信息应该足够了。"
                    "请现在综合所有信息，按格式输出对比结果。"
                    "除非有关键数据完全缺失，否则不要再搜索。）"
                )))

            response = llm_with_tools.invoke(messages)
            metrics.record_llm_call()
            messages.append(response)

            # 没有工具调用 → Agent 认为任务完成
            if not response.tool_calls:
                metrics.stop()
                logger.info(
                    "[%s] 任务完成 — %d 轮 | %d ms | %d LLM 调用 | %d 工具调用",
                    name, iteration,
                    metrics.elapsed_ms, metrics.llm_calls, metrics.tool_calls,
                )
                # 写入 state
                existing = state.get("agent_metrics", {})
                existing[name] = metrics.to_dict()
                return {
                    f"{name}_result": response.content,
                    "agent_metrics": existing,
                }

            # ── 执行工具调用 ──
            for tc in response.tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                tool_id = tc.get("id", "")

                metrics.record_tool_call(tool_name)
                logger.info("[%s] 调用工具: %s(%s)", name, tool_name, tool_args)

                tool = TOOL_BY_NAME.get(tool_name)
                if tool is None:
                    result = f"错误: 未知工具 '{tool_name}'"
                else:
                    try:
                        result = tool.invoke(tool_args)
                    except Exception as exc:
                        result = (
                            f"工具调用失败 ({type(exc).__name__}): "
                            f"{str(exc)[:300]}"
                        )
                        logger.warning(
                            "[%s] 工具 %s 调用失败: %s", name, tool_name, exc,
                        )

                messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id,
                ))

        # ── 超过最大迭代次数，强制结束 ──
        logger.warning(
            "[%s] 达到最大迭代次数 %d，强制输出结果",
            name, MAX_REACT_ITERATIONS,
        )
        messages.append(HumanMessage(content=(
            "你已达到最大搜索轮次。请基于已获取的所有信息，"
            "直接按要求的格式输出对比结果（不要再调用工具）。"
        )))
        final = llm.invoke(messages)
        metrics.record_llm_call()
        metrics.stop()

        existing = state.get("agent_metrics", {})
        existing[name] = metrics.to_dict()
        return {
            f"{name}_result": final.content,
            "agent_metrics": existing,
        }

    agent_node.__name__ = f"{name}_agent"
    return agent_node
