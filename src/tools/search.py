"""Tavily 搜索工具 — 供 ReAct Agent 调用的互联网搜索能力。"""

import logging
import os

from langchain_community.tools import TavilySearchResults
from langchain_core.tools import tool

from src.config import settings

logger = logging.getLogger(__name__)

MAX_RESULTS = 3


def _ensure_env_key():
    """确保 TAVILY_API_KEY 已写入环境变量（langchain_community 从 os.environ 读取）。"""
    if not os.getenv("TAVILY_API_KEY") and settings.tavily_api_key:
        os.environ["TAVILY_API_KEY"] = settings.tavily_api_key


@tool
def search_tool(query: str) -> str:
    """搜索互联网获取竞品对比相关信息。输入中文或英文关键词查询，返回带来源链接的搜索结果摘要。"""
    _ensure_env_key()

    logger.info("Tavily 搜索: %s", query[:80])

    try:
        raw = TavilySearchResults(max_results=MAX_RESULTS).invoke(query)
    except Exception as exc:
        logger.error("Tavily 搜索失败: %s", exc)
        return f"搜索失败（{type(exc).__name__}）: {str(exc)[:200]}。请尝试更换搜索关键词。"

    if not raw:
        return "未找到相关搜索结果，请尝试更换关键词或调整搜索角度。"

    # 格式化为 LLM 友好的结构化文本
    blocks = []
    for i, r in enumerate(raw, 1):
        title = r.get("title", "无标题")
        content = r.get("content", "无内容")
        url = r.get("url", "无链接")
        blocks.append(f"【结果 {i}】{title}\n{content}\n🔗 {url}")

    logger.info("Tavily 搜索完成，返回 %d 条结果", len(raw))
    return "\n\n".join(blocks)
