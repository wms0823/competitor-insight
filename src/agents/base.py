"""ReAct Agent 工厂 — 支持 fast/standard/deep 三种性能模式 + 实时进度推送。"""

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

# ── 模式配置 ──
MODE_CONFIG = {
    "fast": {
        "max_iterations": 1,
        "tools": [search_tool],
        "label": "快速",
        "desc": "1轮搜索，~20秒",
    },
    "standard": {
        "max_iterations": 2,
        "tools": [search_tool],
        "label": "标准",
        "desc": "2轮搜索，~30秒",
    },
    "deep": {
        "max_iterations": 3,
        "tools": [search_tool, scrape_tool],
        "label": "深度",
        "desc": "3轮搜索+网页抓取，~50秒",
    },
}

DIM_LABELS = {
    "feature": "功能对比",
    "pricing": "价格对比",
    "sentiment": "口碑对比",
    "scenario": "场景对比",
}


def create_dimension_agent(name: str, system_prompt: str):
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
        mode = state.get("mode", "standard")
        cfg = MODE_CONFIG.get(mode, MODE_CONFIG["standard"])
        max_iter = cfg["max_iterations"]
        tools: List[BaseTool] = cfg["tools"]
        tool_by_name = {t.name: t for t in tools}
        dim_label = DIM_LABELS.get(name, name)

        # ── 进度 ──
        progress = list(state.get("progress", []))
        progress.append(f"🔍 {dim_label}：开始分析...")
        logger.info("[%s] 模式=%s 最大迭代=%d", name, mode, max_iter)

        # ── 指标 ──
        metrics = AgentMetrics()
        metrics.start()

        # ── 初始化 LLM（绑定工具） ──
        llm = settings.get_llm(temperature=0.1)
        llm_with_tools = llm.bind_tools(tools) if tools else llm

        # ── 搜索策略提示 ──
        search_hint = ""
        if mode == "fast":
            search_hint = "搜索 1 次获取关键信息后立即输出对比结果。追求速度，不必穷尽。"
        elif mode == "deep":
            search_hint = (
                "搜索 2-3 次获取全面信息，必要时抓取重要页面详情。追求深度和准确度。"
            )
        else:
            search_hint = "搜索 1-2 次获取关键信息，信息充分后立即输出。追求效率。"

        # ── 构建初始消息 ──
        system_msg = SystemMessage(
            content=system_prompt.format(product_a=a, product_b=b, category=cat)
        )
        user_msg = HumanMessage(content=f"请对比 {a} 和 {b}。{search_hint}")

        messages = [system_msg, user_msg]

        # ── ReAct 循环 ──
        for iteration in range(1, max_iter + 1):
            logger.info("[%s] ReAct 第 %d/%d 轮", name, iteration, max_iter)

            # 最后一轮前提醒收尾
            if iteration == max_iter and max_iter > 1:
                messages.append(
                    HumanMessage(
                        content="（请综合所有已获取信息，按格式输出对比结果，不要再搜索。）"
                    )
                )
            elif iteration >= 2:
                messages.append(
                    HumanMessage(
                        content="（信息应该足够了，请尽快输出对比结果。）"
                    )
                )

            response = llm_with_tools.invoke(messages)
            metrics.record_llm_call()
            messages.append(response)

            # 没有工具调用 → Agent 认为任务完成
            if not response.tool_calls:
                metrics.stop()
                logger.info(
                    "[%s] 任务完成 — %d轮 | %dms | %d次LLM | %d次工具",
                    name,
                    iteration,
                    metrics.elapsed_ms,
                    metrics.llm_calls,
                    metrics.tool_calls,
                )
                existing = state.get("agent_metrics", {})
                existing[name] = metrics.to_dict()
                progress.append(f"✅ {dim_label}：完成（{iteration}轮，{metrics.elapsed_ms}ms）")
                return {
                    f"{name}_result": response.content,
                    "agent_metrics": existing,
                    "progress": progress,
                }

            # ── 执行工具调用 ──
            for tc in response.tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                tool_id = tc.get("id", "")
                query_preview = str(tool_args.get("query", tool_args.get("url", "")))[:60]

                metrics.record_tool_call(tool_name)
                logger.info("[%s] 调用工具: %s(%s)", name, tool_name, tool_args)
                progress.append(f"📡 {dim_label}：{tool_name} → {query_preview}...")

                tool = tool_by_name.get(tool_name)
                if tool is None:
                    result = f"错误: 未知工具 '{tool_name}'"
                else:
                    try:
                        result = tool.invoke(tool_args)
                    except Exception as exc:
                        result = (
                            f"工具调用失败 ({type(exc).__name__}): {str(exc)[:300]}"
                        )
                        logger.warning("[%s] 工具 %s 失败: %s", name, tool_name, exc)

                messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_id)
                )

        # ── 超过最大迭代次数，强制结束 ──
        logger.warning("[%s] 达到最大迭代次数 %d，强制输出", name, max_iter)
        messages.append(
            HumanMessage(
                content="已达到最大搜索轮次。请基于已获取的所有信息，直接按格式输出对比结果，不要再调用工具。"
            )
        )
        final = llm.invoke(messages)
        metrics.record_llm_call()
        metrics.stop()

        existing = state.get("agent_metrics", {})
        existing[name] = metrics.to_dict()
        progress.append(f"✅ {dim_label}：完成（已达上限，{metrics.elapsed_ms}ms）")
        return {
            f"{name}_result": final.content,
            "agent_metrics": existing,
            "progress": progress,
        }

    agent_node.__name__ = f"{name}_agent"
    return agent_node
